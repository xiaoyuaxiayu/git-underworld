import os
import subprocess

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
