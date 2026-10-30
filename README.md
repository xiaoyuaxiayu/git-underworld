# Git 地府 · git-underworld

保留墨绿与旧纸生死簿界面的本地 Git 文件删除分析工具。Python + FastAPI 后端，原生 HTML/CSS/JavaScript 前端，无前端构建步骤。

## Windows 启动

需要 Python 3.11+ 和 Git for Windows，均加入 PATH。在 PowerShell 中运行：

```powershell
cd 'E:\赛博地府\git-underworld'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\start.bat
```

浏览器打开 http://127.0.0.1:8765 。`start.bat` 优先使用 `.venv`，否则使用 PATH 中的 Python。已有依赖可直接运行 `python run.py`。关闭启动窗口或 Ctrl+C 停止服务。请使用仓库所属 Windows 用户启动；Git 所有权检查失败时本工具提示错误，不修改信任配置。

运行入口固定监听 `127.0.0.1:8765`；不上传代码、不调用付费 API、不发布。安装依赖需要访问包源，正常分析与判词生成无需联网。

## 体验

1. 打开页面即为**演示模式**：虚构记录、模拟还魂和强推剧情均明确标记。
2. 创建一个可真实分析的示例仓库：

   ```powershell
   .\.venv\Scripts\python.exe scripts/create_demo_repo.py
   ```

   在页面输入 `E:\赛博地府\git-underworld\demo-repository`，点击“翻阅生死簿”。预计显示两条 `中文 空格.txt` 删除记录，存续时间各一小时，较早一条标记“疑似还魂”；重命名不计死亡。生成器只接受不存在的目标目录，拒绝覆盖。也可传入一个新的绝对目录：`python scripts/create_demo_repo.py "E:\临时目录\演示 仓库"`。
3. 输入自己的本地 Git 仓库绝对路径（不带外层引号），点击“翻阅生死簿”。支持中文、空格路径，也可读取仓库子目录、worktree 或 bare 仓库。界面显示实际 HEAD 哈希、第一父链、数量上限、完成情况和浅克隆提示。
4. 点击记录或“判决书”，展示可截图的**代码往生判决书**。也可打印/保存 PDF。判词来自本地模板。

## 分析口径与限制

- 分析**文件级删除**，不解析函数。忽略工作区未提交变化。固定本轮开始时的 HEAD，默认扫描最近 200 个 first-parent 提交，可调 1–1000。
- 每个提交与第一父提交比较；合并提交只计对第一父快照的变化，不重复遍历支线提交。
- 使用 `git diff-tree -M` 识别重命名；识别出的 R 不算死亡，并传递已知存续起点。Git 的重命名识别基于相似度，重命名同时大幅改写可能表现为删除与新增，不能保证还原作者意图。
- 存续时间按本轮可见创建提交至删除提交的**提交者时间**计算；超度人为删除提交的作者。时间不是代码实际运行时长。起点超出扫描范围、浅边界、时间倒序时显示未知。浅边界没有可用父提交时跳过其变更。
- 同路径删除后在后续已扫描提交重新出现，标为“疑似还魂”，不代表内容一致。再次删除生成独立记录，重新计算这一轮存续时间。“未见重现”只针对本轮已扫描范围，不是当前文件存在性保证。
- 单条 Git 命令超时 5 秒，总扫描预算 45 秒；预算覆盖 Git 调用。扫描中途失败会返回已完成部分及警告，页面显示实际检查区间。从所选区间较早端开始处理，部分结果可能尚未到达 HEAD。
- 普通 Git 历史不能可靠证明发生过强推。强推警报仅存在于演示模式。真实模式没有还魂写操作。
- 非 UTF-8 文件名按替换字符展示；中文 UTF-8 Git 路径可正常显示。超大单提交的输出量未做压力测试。

## 只读与页面安全

后端仅调用 `rev-parse`、`for-each-ref`、`rev-list`、`show -s`、`diff-tree`，通过参数数组调用且 `shell=False`；禁用可选锁、外部 diff 和 textconv，不执行 checkout/reset/clean/rebase/push，不改 Git 配置。目标仓库不接受应用写入。测试/演示生成器只在新建的测试目录内写入与提交。

仓库路径、文件名、作者和提交信息通过 DOM `textContent` 展示，不作为 HTML 执行。接口拒绝跨 Origin 浏览器请求，设置 CSP；不开放跨域许可。本地路径不会被当作命令拼接。

## 源码

- `frontend/index.html` / `frontend/app.js`：实际运行的前端源码。
- `backend/git_reader.py`：只读扫描器。
- `backend/app.py`：API 与静态页面服务。
- `run.py` / `start.bat`：本地启动入口。
- `dist/index.html`：最初演示快照，仅存档，服务不加载它。
- `scripts/migrate_frontend.py`：本轮一次性迁移脚本，日常开发直接修改 frontend，不必重跑。
- `.openai/hosting.json`：先前原型遗留的站点标识，本地运行不使用，本轮未发布。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check frontend/app.js
```

自动测试在系统临时目录创建独立 Git 仓库，验证创建、删除、同路径重建、再次删除、重命名、中文与空格路径、first-parent 合并、截断、浅克隆、非 Git 目录、空仓库、API、跨站拒绝及模拟命令超时；比较分析前后全部仓库文件字节以验证只读。

可选浏览器验证：安装 `playwright` 与其 Chromium，先创建演示仓库并启动服务，再运行 `python tests/browser_check.py`。截图写入 `.test-output/`。浏览器依赖不属于运行必需依赖。
