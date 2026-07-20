# 项目进度

最后更新：2026-07-20

## 当前状态

- 当前阶段：第 1 步——GitHub 数据采集
- 当前小步：1.2——处理分页、限流和重试
- 项目状态：进行中

## 已完成

### 0.1 建立仓库与长期项目记忆（2026-07-16）

- 初始化本地 Git 仓库。
- 建立项目宪章，固定目标、范围、阶段与完成标准。
- 建立 `AGENTS.md`，让新 Codex 会话能够按相同方式继续指导。
- 建立进度文件，确保每次只推进一个可验证的小步。
- 建立基础 README 和 Python `.gitignore`。

验证：

```powershell
git status --short --branch
git rev-parse --show-toplevel
```

### 0.2 确认 Python 工具链与环境方案（2026-07-16）

- 确认可用解释器为 Python 3.12.10，Git 为 2.54.0.windows.1。
- 发现 Windows `py` 启动器未识别已安装解释器，因此项目命令统一使用 `python`。
- 使用标准库 `venv` 创建 `.venv`，验证结果为 `isolated = True`。
- 虚拟环境初始占用 12,009,099 字节，未下载业务依赖。
- 使用 `pyproject.toml` 声明 Python 版本与直接依赖；首次引入外部依赖时生成并提交锁文件。

验证：

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import sys; print(sys.prefix != sys.base_prefix)"
```

### 0.3 创建最小 Python 工程骨架（2026-07-17）

- 采用 `src/github_trend_agent` 包布局，隔离仓库文件与可导入源码。
- 建立 `python -m github_trend_agent` 模块入口。
- 将用户可见输出与进程入口分离，入口返回标准退出码。
- 使用标准库 `unittest` 建立首个测试，不增加第三方依赖。

验证：

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m github_trend_agent
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### 0.4 建立类型安全的配置管理（2026-07-18）

- 添加可提交的 `.env.example`，不包含真实密钥。
- 使用不可变、带类型的 `Settings` 集中解析环境变量。
- 支持 API 地址、请求超时、Top N 和 GitHub Token 配置。
- Token 不参与配置对象的字符串表示，降低日志泄露风险。
- 配置错误返回明确消息和非零退出码，不输出密钥值。
- 测试通过显式字典注入配置，不依赖用户电脑的真实环境。

验证：

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m github_trend_agent
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### 0.5 添加最小质量门禁并完成初始化复盘

目标：建立最小代码质量检查，完成第 0 步验收，并创建项目第一次 Git 提交。

当前检查点：

- 已锁定 Ruff 0.15.22，并使用无缓存模式运行。
- 已建立统一命令 `python scripts/check.py`。
- 格式检查、静态检查和 5 个单元测试全部通过。
- 密钥扫描未发现真实 GitHub Token，`.venv` 与字节码缓存均被忽略。
- 使用 GitHub noreply 邮箱配置当前仓库的提交身份，保护个人邮箱。
- 创建语义清晰的第一次本地 Git 提交。

完成标准：

- 代码格式、静态检查和测试有统一命令。
- 初始化阶段所有验证通过。
- 检查提交内容不包含密钥或本地环境。
- 创建语义清晰的第一次 Git commit。

## 第 0 步复盘

已经具备：

- 独立 Git 仓库和持续更新的项目文档。
- Python 3.12 隔离环境与 `src` 工程布局。
- 可运行的模块入口和带类型的安全配置对象。
- 密钥隔离规则、5 个单元测试和一条统一质量门禁命令。

尚未具备：

- GitHub API 请求和真实仓库数据。
- 数据清洗、评分、LLM、日报、邮件、数据库与 Web 功能。

## 第 1 步已完成

### 1.1 建立 GitHub API 最小采集闭环（2026-07-20）

- 使用 GitHub REST API `2026-03-10` 版本和推荐 JSON 请求头。
- 封装 `GitHubClient`，CLI 不直接承担网络请求和 JSON 解析。
- 建立不可变 `Repository` 数据模型，显式表示可缺失描述与语言。
- 查询 `language:python stars:>1000`，真实返回并展示 10 个公开仓库。
- 对成功响应、GitHub 403 错误和无效响应建立测试。
- 使用 Python 标准库完成首个闭环，不增加运行依赖。

验证：

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m github_trend_agent
.\.venv\Scripts\python.exe scripts\check.py
```

## 唯一的下一步

### 1.2 处理分页、限流和重试

目标：让采集器在请求量增大或 GitHub 暂时拒绝请求时仍可预测地运行。

完成标准：

- 支持多页采集并设置明确总量上限。
- 读取并保存响应中的限流信息。
- 对可重试错误采用有上限的退避策略。
- 对不可重试错误快速失败，避免浪费 API 配额。
- 时间与等待逻辑可在测试中替换，不进行真实休眠。

## 待办阶段

- 1.3 完成采集阶段的数据模型与验收。

## 决策与提醒

- 长期记忆采用仓库内 Markdown，而不是项目专属 Skill：内容随代码版本演进，新会话可直接读取，也便于审查历史。
- 暂不引入 FastAPI、Pandas、LangChain、MySQL、Redis 等依赖，避免在需求尚未落地时增加复杂度。
- GitHub API 无法直接提供可靠的历史 Star 增长速度；该指标必须基于后续保存的快照计算。
