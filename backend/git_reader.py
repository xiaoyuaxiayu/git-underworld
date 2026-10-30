import os
import subprocess
import time
from pathlib import Path

class ScanError(Exception):
    pass

class GitReader:
    def __init__(self, path, command_timeout=5, scan_timeout=45):
        self.path = Path(path).expanduser().resolve()
        if not self.path.is_dir():
            raise ScanError('目录不存在，请输入本地 Git 仓库目录。')
        self.command_timeout = command_timeout
        self.deadline = time.monotonic() + scan_timeout

    def git(self, *args):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ScanError('扫描总时限已到，请降低扫描提交数。')
        env = {k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')}
        env.update(GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0', GIT_NO_REPLACE_OBJECTS='1')
        try:
            result = subprocess.run(['git', '--no-pager', '-C', str(self.path), *args], capture_output=True,
                                    shell=False, env=env, timeout=min(remaining, self.command_timeout))
        except FileNotFoundError as exc:
            raise ScanError('未找到 Git，请安装 Git for Windows 并加入 PATH。') from exc
        except subprocess.TimeoutExpired as exc:
            raise ScanError('Git 命令超时，请降低扫描范围或检查存储速度。') from exc
        if result.returncode:
            error = result.stderr.decode('utf-8', 'replace')
            if 'dubious ownership' in error:
                raise ScanError('Git 拒绝读取不同用户拥有的仓库。请使用仓库所属的 Windows 用户启动本服务；本工具不会修改 Git 信任配置。')
            if 'not a git repository' in error:
                raise ScanError('该目录不是 Git 仓库，请检查路径。')
            raise ScanError('Git 无法读取仓库：' + error[:1000])
        return result.stdout

def decode(value):
    return value.decode('utf-8', 'replace')

def changes(raw):
    parts = raw.split(b'\0'); i = 0
    while i < len(parts) and parts[i]:
        status = decode(parts[i])[0]; old = parts[i+1]; i += 2
        new = None
        if status in 'RC':
            new = parts[i]; i += 1
        yield status, old, new

def analyze(path, limit=200, **options):
    reader = GitReader(path, **options)
    reader.git('rev-parse', '--git-dir')
    shallow = reader.git('rev-parse', '--is-shallow-repository').strip() == b'true'
    try:
        head = decode(reader.git('rev-parse', '--verify', 'HEAD^{commit}')).strip()
    except ScanError as exc:
        if '超时' in str(exc) or '时限' in str(exc):
            raise
        refs = reader.git('for-each-ref', '--format=%(objectname)', 'refs/heads/')
        if refs.strip():
            raise
        return dict(records=[], warnings=['仓库尚无提交（HEAD 未诞生）。'], scope=dict(head=None,
                    strategy='HEAD first-parent', scanned=0, selected=0, limit=limit, truncated=False,
                    shallow=shallow, oldest=None, complete=True))
    chain = decode(reader.git('rev-list', '--first-parent', f'--max-count={limit+1}', head)).splitlines()
    truncated = len(chain) > limit
    commits = chain[:limit]
    warnings = []
    if shallow:
        warnings.append('浅克隆：更早历史不可见，浅边界不视为文件诞生。')
    if truncated:
        warnings.append(f'扫描已截断：仅检查 HEAD 起最近 {limit} 个第一父提交，较早起点可能未知。')
    births, deaths, records = {}, {}, []
    scanned = 0; oldest = None; newest = None
    for commit in reversed(commits):
        try:
            meta = reader.git('show', '-s', '--no-show-signature', '--format=%an%x00%ct%x00%cI%x00%B', commit).split(b'\0', 3)
            author, epoch, date, message = decode(meta[0]), int(meta[1]), decode(meta[2]), decode(meta[3]).rstrip('\n')
            parents = decode(reader.git('rev-list', '--parents', '-n', '1', commit)).split()[1:]
            if not parents and shallow:
                scanned += 1; oldest = oldest or commit; newest = commit
                continue
            args = ['diff-tree', '--no-commit-id', '--name-status', '-r', '-z', '-M', '--no-ext-diff', '--no-textconv']
            raw = reader.git(*args, parents[0], commit, '--') if parents else reader.git(*args, '--root', commit, '--')
        except ScanError as exc:
            warnings.append(str(exc) + ' 返回已完成部分；未检查的提交不能据此判断还魂。')
            break
        entries = list(changes(raw))
        for status, old, new in entries:
            if status == 'D':
                born = births.pop(old, None)
                duration = epoch-born if born is not None and epoch >= born else None
                record = dict(path=decode(old), author=author, deleted_at=date, message=message,
                              hash=commit, short_hash=commit[:9], lifetime_seconds=duration,
                              lifetime_note='按可见创建至删除提交的提交者时间计算' if duration is not None else '无可靠起点或提交时间倒序',
                              resurrected=False, reappeared_at=None, reappeared_hash=None)
                records.append(record); deaths.setdefault(old, []).append(record)
        for status, old, new in entries:
            if status == 'R':
                births[new] = births.pop(old, None)
            elif status == 'A':
                births[old] = epoch
            elif status == 'C':
                births[new] = epoch
            appeared = new if status in 'RC' else old if status == 'A' else None
            if appeared is not None:
                for dead in deaths.pop(appeared, []):
                    dead.update(resurrected=True, reappeared_at=date, reappeared_hash=commit)
        scanned += 1; oldest = oldest or commit; newest = commit
    return dict(records=list(reversed(records)), warnings=warnings, scope=dict(head=head,
                strategy='HEAD first-parent', scanned=scanned, selected=len(commits), limit=limit,
                truncated=truncated, shallow=shallow, oldest=oldest, newest=newest, complete=scanned==len(commits)))
