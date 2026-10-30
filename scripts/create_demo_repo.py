"""Create only a NEW demo repository. Never alter an existing destination."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.demo_fixture import fixture

if __name__=='__main__':
    path=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'demo-repository'
    if path.exists():
        raise SystemExit('目标已存在，拒绝覆盖。请指定一个新的目录。')
    fixture(path)
    print(str(path))
