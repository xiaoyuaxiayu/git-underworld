import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import app
from backend.git_reader import analyze, GitReader, ScanError

def git(path, *args, timestamp=None):
    env = os.environ.copy()
    env.update(GIT_AUTHOR_NAME='测试超度人', GIT_AUTHOR_EMAIL='test@local',
               GIT_COMMITTER_NAME='测试超度人', GIT_COMMITTER_EMAIL='test@local',
               GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
    if timestamp:
        env.update(GIT_AUTHOR_DATE=timestamp, GIT_COMMITTER_DATE=timestamp)
    return subprocess.check_output(['git','-C',str(path),*args], env=env, stderr=subprocess.PIPE)

def fixture(path):
    path.mkdir(parents=True)
    git(path,'init','-b','main')
    name='中文 空格.txt'
    for n, action in enumerate(['create','delete','recreate','delete','rename-source','rename']):
        if action in ('create','recreate'):
            (path/name).write_text('hello '+action, encoding='utf-8')
        elif action=='delete':
            (path/name).unlink()
        elif action=='rename-source':
            (path/'旧 文件.txt').write_text('rename unchanged\n', encoding='utf-8')
        else:
            (path/'旧 文件.txt').rename(path/'新 文件.txt')
        git(path,'add','--all')
        git(path,'commit','-m',action+' <img src=x onerror=alert(1)>',timestamp=f'2026-01-01T{n:02}:00:00+00:00')
    return path

class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='git-underworld-')
        self.root=Path(self.temp.name)
        self.repo=fixture(self.root/'中文 空格 仓库')

    def tearDown(self):
        # Git object files can be read-only on Windows.
        import shutil, stat
        def writable(func, path, exc):
            os.chmod(path, stat.S_IWRITE); func(path)
        shutil.rmtree(self.root, onexc=writable)
        self.temp.cleanup()

    def test_lifecycles_rename_and_readonly(self):
        before={p.relative_to(self.repo):p.read_bytes() for p in self.repo.rglob('*') if p.is_file()}
        result=analyze(str(self.repo))
        self.assertEqual(result['scope']['scanned'],6)
        recent,old=result['records']
        self.assertEqual(recent['path'],'中文 空格.txt')
        self.assertEqual(old['author'],'测试超度人')
        self.assertEqual([recent['lifetime_seconds'],old['lifetime_seconds']],[3600,3600])
        self.assertFalse(recent['resurrected']); self.assertTrue(old['resurrected'])
        self.assertIn('<img',recent['message'])
        after={p.relative_to(self.repo):p.read_bytes() for p in self.repo.rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    def test_truncated(self):
        result=analyze(str(self.repo),3)
        self.assertTrue(result['scope']['truncated'])
        self.assertEqual(len(result['records']),1)
        self.assertIsNone(result['records'][0]['lifetime_seconds'])

    def test_shallow(self):
        target=self.root/'浅 克隆'
        git(self.root,'clone','--depth','3',self.repo.as_uri(),str(target))
        result=analyze(str(target))
        self.assertTrue(result['scope']['shallow'])
        self.assertEqual(result['records'],[])  # Boundary deletion has no available parent.
        self.assertTrue(result['warnings'])

    def test_invalid_empty_api(self):
        with TestClient(app) as client:
            self.assertEqual(client.get('/').status_code,200)
            self.assertEqual(client.get('/static/app.js').status_code,200)
            self.assertEqual(client.post('/api/analyze',json={'path':str(self.root)}).status_code,400)
            self.assertEqual(client.post('/api/analyze',json={'path':str(self.repo),'limit':0}).status_code,422)
            response=client.post('/api/analyze',json={'path':str(self.repo)})
            self.assertEqual(len(response.json()['records']),2)
            self.assertEqual(client.post('/api/analyze',json={'path':str(self.repo)},headers={'origin':'https://evil.invalid'}).status_code,403)
        empty=self.root/'empty'; empty.mkdir(); git(empty,'init')
        self.assertIsNone(analyze(str(empty))['scope']['head'])

    def test_timeout_and_argv(self):
        reader=GitReader(str(self.repo))
        with patch('backend.git_reader.subprocess.run',side_effect=subprocess.TimeoutExpired('git',1)) as run:
            with self.assertRaisesRegex(ScanError,'超时'):
                reader.git('rev-parse','HEAD')
            self.assertIsInstance(run.call_args.args[0],list)
            self.assertFalse(run.call_args.kwargs['shell'])
        with self.assertRaisesRegex(ScanError,'时限'):
            analyze(str(self.repo),scan_timeout=0)

    def test_first_parent(self):
        git(self.repo,'switch','-c','side')
        (self.repo/'side.txt').write_text('temporary')
        git(self.repo,'add','.'); git(self.repo,'commit','-m','side create')
        (self.repo/'side.txt').unlink()
        git(self.repo,'add','.'); git(self.repo,'commit','-m','side delete')
        git(self.repo,'switch','main')
        git(self.repo,'merge','--no-ff','side','-m','merge side')
        result=analyze(str(self.repo))
        self.assertEqual(result['scope']['scanned'],7)
        self.assertEqual(len(result['records']),2)

    def test_rename_lifetime(self):
        (self.repo/'新 文件.txt').unlink()
        git(self.repo,'add','--all')
        git(self.repo,'commit','-m','delete renamed',timestamp='2026-01-01T06:00:00+00:00')
        recent=analyze(str(self.repo))['records'][0]
        self.assertEqual(recent['path'],'新 文件.txt')
        self.assertEqual(recent['lifetime_seconds'],7200)

    def test_partial_timeout(self):
        original=GitReader.git
        calls=0
        def stop_later(reader,*args):
            nonlocal calls
            if args[0]=='diff-tree':
                calls+=1
                if calls==3:
                    raise ScanError('Git 命令超时')
            return original(reader,*args)
        with patch.object(GitReader,'git',stop_later):
            result=analyze(str(self.repo))
        self.assertFalse(result['scope']['complete'])
        self.assertEqual(result['scope']['scanned'],2)
        self.assertEqual(len(result['records']),1)
        self.assertIn('返回已完成部分',result['warnings'][0])

    def test_shallow_unknown_birth(self):
        target=self.root/'浅 clone 四层'
        git(self.root,'clone','--depth','4',self.repo.as_uri(),str(target))
        result=analyze(str(target))
        self.assertEqual(len(result['records']),1)
        self.assertIsNone(result['records'][0]['lifetime_seconds'])

if __name__=='__main__':
    unittest.main()
