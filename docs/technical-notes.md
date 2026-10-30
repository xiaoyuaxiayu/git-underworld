# 开发与分析说明

[返回 README](../README.md)

## 源码结构

| 路径 | 用途 |
| --- | --- |
| `frontend/` | 当前前端源码，原生 HTML/CSS/JavaScript |
| `backend/git_reader.py` | Git 只读扫描器 |
| `backend/app.py` | FastAPI 接口与静态资源服务 |
| `run.py` / `start.bat` | 本地启动入口，固定监听 `127.0.0.1:8765` |
| `scripts/create_demo_repo.py` / `scripts/demo_fixture.py` | 在新目录生成可分析的示例历史 |
| `tests/test_history.py` | 后端、API 与只读行为测试 |
| `tests/browser_check.py` | 可选的浏览器交互验证 |
| `dist/index.html` | 早期原型存档，服务不加载 |
| `scripts/migrate_frontend.py` | 一次性迁移脚本；日常修改 frontend，不要重跑以免覆盖页面 |
| `.openai/hosting.json` | 早期站点原型遗留标识，本地服务不使用 |

`start.bat` 优先使用 `.venv\Scripts\python.exe`，不存在时使用 PATH 中的 Python。它不自动安装依赖，也不自动打开浏览器。

## 分析规则

- 只分析已提交的**文件删除**。每轮固定开始时的 HEAD，沿 first-parent 选取最近 200 个提交，API 接受 1–1000 的上限。
- 按选定区间从旧到新处理；每个提交与第一父提交比较。合并提交不会重复遍历支线内部提交。完整历史中的根提交以空树作为起点。
- `git diff-tree -M` 用于识别重命名。R 状态不生成死亡记录，并传递已知创建起点。识别基于相似度；重命名同时大幅改写可能呈现为删除与新增，不能保证还原作者意图。
- 文件路径使用 NUL 分隔解析，避免空格或换行破坏字段边界。中文 UTF-8 路径正常显示；非 UTF-8 名称按替换字符展示，不能保证原样显示。
- 超度人为删除提交的作者；删除时间与存续时间计算使用**提交者时间**。时间差不是代码实际运行时长，也不是可靠的人类工作耗时。
- 可见创建提交提供存续起点；如果起点位于扫描区间外、浅边界之前或时间倒序，时长为未知。浅边界缺少可用父提交时跳过其变更，不将边界快照视为创建。
- 删除后同路径再出现，标记旧删除记录为疑似还魂；记录重现提交与时间。同路径不证明相同内容，之后再次删除则单独入册并重新计算该轮时长。
- 单条 Git 命令超时 5 秒，总扫描预算 45 秒，预算覆盖 Git 调用。中途失败返回已完成部分和提示；部分结果可能尚未处理到 HEAD，前端显示实际区间。
- 普通 Git 历史不能可靠证明强推。应用没有真实强推检测或实际恢复功能。

## 只读与页面安全

扫描器通过参数数组调用 Git，`shell=False`。仅使用 `rev-parse`、`for-each-ref`、`rev-list`、`show -s`、`diff-tree`，禁用可选锁、外部 diff 和 textconv，不执行 checkout/reset/clean/rebase/push，不修改 Git 配置。新建示例仓库与测试仓库的脚本会写入它们自己的目录，这与只读分析接口分开。

仓库路径、文件名、作者和提交信息通过 DOM `textContent` 展示，不作为 HTML 执行。接口拒绝跨 Origin 浏览器请求，设置 CSP，不开放跨域许可。应用运行入口仅监听回环地址；运行分析不上传代码、不调用外部 AI 服务，判词由前端模板生成。

## 运行测试

在项目根目录打开 PowerShell，使用 README 中创建的虚拟环境：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试会在系统临时目录创建独立 Git 仓库，覆盖创建、删除、重建、再次删除、重命名与重命名后删除、中文与空格路径、第一父链合并、截断、浅克隆、非 Git 目录、空仓库、跨站拒绝、超时和部分结果。比较分析前后所有仓库文件（含 `.git`）字节验证只读。不会在用户指定的仓库中做破坏性测试。

可选 JavaScript 语法检查（仅此检查需要 Node.js）：

```powershell
node --check frontend/app.js
```

可选浏览器检查需要 Playwright 和 Chromium：

```powershell
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe -m playwright install chromium
```

先用 `scripts/create_demo_repo.py` 创建默认的 `demo-repository`（已存在则跳过），并在另一个窗口启动服务，再运行：

```powershell
.\.venv\Scripts\python.exe tests/browser_check.py
```

截图写入 `.test-output/`，该目录不提交到 Git。浏览器测试依赖不属于普通运行依赖。历史验证结果与未覆盖场景见 [TEST_RESULTS.md](../TEST_RESULTS.md)。
