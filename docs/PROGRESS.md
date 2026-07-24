# 项目进度

最后更新：2026-07-24

## 当前状态

- 当前阶段：第 4 步——日报与邮件
- 当前小步：4.3——生成 HTML 并发送邮件
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

### 1.2 处理分页、限流和重试（2026-07-20）

- 按 GitHub `Link` 响应头顺序读取下一页。
- 默认每页 25、最多采集 50，并限制单页 1–100、总量 1–1000。
- 返回 `RepositorySearchResult`，包含仓库、页数和最后响应的限流信息。
- 解析 `X-RateLimit-Limit`、`Remaining`、`Reset` 和 `Resource`。
- 403/429 遵守 `Retry-After` 或 `X-RateLimit-Reset`。
- 5xx 与网络临时错误采用最多 2 次的指数退避，其他 4xx 快速失败。
- 睡眠与时钟可以在测试中注入，11 个测试均不真实等待或访问网络。
- 真实未认证验证读取 2 页、采集 50 个仓库并展示 Top 10。

验证：

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m github_trend_agent
.\.venv\Scripts\python.exe scripts\check.py
```

### 1.3 完成认证采集与阶段验收（2026-07-21）

目标：以最小权限安全配置 GitHub Token，验证认证请求，并完成数据采集阶段复盘。

- 已引入并锁定 `python-dotenv 1.2.2`，本地 `.env` 可自动加载。
- 操作系统环境变量优先于 `.env`，便于部署环境安全覆盖。
- 已建立 Token 扫描门禁，扫描所有可被 Git 跟踪的文件且不输出密钥值。
- 已创建细粒度 Token，真实值只保存在被 Git 忽略的本地 `.env` 中。
- 认证模式真实请求成功：读取 2 页、采集 50 个仓库并展示 Top 10。
- 格式、静态检查、密钥扫描和 12 个单元测试全部通过。

原始仓库数据契约：

- `name`、`stars`、`forks`、`url`、`owner`、`updated_at` 和 `pushed_at` 为必填字段。
- `description`、`language` 允许缺失，交由下一阶段的清洗规则处理。
- `topics` 在程序中统一为不可变元组，即使 API 没有主题也使用空元组。
- 采集层只负责忠实解析和基础类型验证，不在网络客户端中混入评分逻辑。

## 第 1 步复盘

已经具备：

- GitHub Search API 的认证只读采集，以及清晰的数据模型。
- 多页采集、数量上限、限流信息和有限重试。
- 本地密钥隔离、环境变量覆盖和提交前敏感信息扫描。
- 真实 API 验收与不访问网络的单元测试。

尚未具备：

- 可解释的热度评分与 Top 10 排名。

## 第 2 步进行中

### 2.1 建立数据清洗规则与可验证输出（2026-07-22）

目标：把采集层返回的原始仓库转换为可评分的数据，并让每条清洗规则都可测试、可统计、可解释。

- 按仓库 URL 去重，保留第一次出现的数据。
- 将缺失描述转换为明确的占位文本，避免后续报告出现空白。
- 将缺失语言统一标记为 `Unknown`，保留“未知”这一事实。
- 拒绝名称或 URL 无效、Stars/Forks 为负数的异常记录。
- 输出输入数、保留数、去重数和无效数，便于观察 ETL 数据质量。
- 使用独立的 `CleanRepository`，让清洗后的描述和语言在类型上保证非空。
- 清洗逻辑位于独立模块，不与 API 请求或 CLI 展示逻辑混合。
- 新增 4 个清洗测试；全项目 16 个测试、格式检查、静态检查和密钥扫描全部通过。
- 真实认证运行采集 50 条，清洗后保留 50 条、重复 0 条、无效 0 条。

验证：

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m unittest tests.test_cleaner -v
.\.venv\Scripts\python.exe scripts\check.py
.\.venv\Scripts\python.exe -m github_trend_agent
```

### 2.2 设计第一版可解释热度评分（2026-07-22）

目标：在还没有历史快照时，使用当前可获得的数据构建明确标注为“热度”而非“增长趋势”的第一版评分。

- 将该指标明确命名为“当前热度”，不声称它代表 Star 增长趋势。
- 总分为 Star 相对热度 55%、Fork 相对热度 20%、代码推送活跃度 25%。
- Stars 和 Forks 使用 `log1p` 对数压缩，再按本批候选集最大值归一化到 0–100。
- 活跃度使用 30 天半衰期：刚推送约 100 分，30 天前约 50 分，60 天前约 25 分。
- 输出总分和三个分项，并按总分降序、仓库名稳定排序。
- 当前时间可注入测试，避免测试结果随日期漂移；无时区时间会被拒绝。
- 真实验收发现 `updated_at` 对热门仓库几乎都接近当前时间，不能代表代码活跃度。
- 根据 GitHub 官方字段语义，保留 `updated_at`，新增并改用最后代码推送时间 `pushed_at`。
- 新增 6 个评分测试；全项目共 22 个测试，质量门禁全部通过。
- 真实认证运行后，评分成功改变单纯按 Stars 排列的顺序，且可由分项解释。

验证：

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m unittest tests.test_scorer -v
.\.venv\Scripts\python.exe scripts\check.py
.\.venv\Scripts\python.exe -m github_trend_agent
```

## 第 2 步复盘

已经具备：

- 原始数据和清洗后数据的独立类型契约。
- 缺失值处理、去重、无效数据过滤和清洗统计。
- 可解释、可测试、有明确名称和局限性的当前热度评分。
- 真实数据驱动的字段修正和排名验收。

仍需后续补充：

- 当前分数是同一批候选项目之间的相对比较，不能直接比较不同查询或不同日期的绝对分值。
- 真正的增长趋势必须等历史快照建立后，计算固定时间窗口内的 Stars 增量与增长率。

## 第 3 步进行中

### 3.1 定义结构化分析契约与供应商边界（2026-07-23）

目标：先定义 LLM 必须返回哪些字段、发生错误时如何处理，再接入 DeepSeek 或 OpenAI，避免业务代码绑定某一家 API。

- 定义 `ProjectAnalysis`：项目简介、值得关注原因、技术价值、学习建议、适合人群、1–5 推荐分和证据限制。
- 使用“值得关注原因”而不是未经证实的“走红原因”，避免把当前元数据误写成历史趋势证据。
- 定义最小 `LLMProvider` 接口，DeepSeek、OpenAI 和测试替身都只需实现同一个 `generate_json` 方法。
- Prompt 只发送名称、描述、语言、Stars、Forks、Topics、最后推送时间和可解释热度分项，不发送 Token 或本地配置。
- 系统提示明确将仓库文本视为不可信数据，降低描述或 Topics 中 Prompt Injection 的影响。
- 严格校验 JSON 对象、精确字段、非空文本、列表长度、推荐分范围和最大响应长度。
- 无效响应的异常不回显模型原文，避免意外内容进入日志。
- 批量分析隔离预期的单项目失败，保留错误结果并继续后续项目。
- 新增 6 个合同测试；全项目共 28 个测试，质量门禁全部通过。
- 本小步不调用真实 LLM，不产生模型费用，也不改变现有 CLI 行为。

验证：

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m unittest tests.test_llm_analysis -v
.\.venv\Scripts\python.exe scripts\check.py
```

### 3.2 接入首个 LLM 供应商（2026-07-23）

目标：选择 DeepSeek 或 OpenAI，实现第一个 `LLMProvider` 适配器，并只分析少量真实 Top 项目完成成本受控的闭环。

当前检查点：

- 选择 DeepSeek 作为首个供应商，使用官方 OpenAI 兼容 Chat Completions API。
- 新增 `DeepSeekProvider`，通过标准库 HTTPS POST 调用，不引入供应商 SDK。
- 默认模型为 `deepseek-v4-flash`，关闭思考模式，要求 JSON，最大输出 1200 tokens。
- 默认 `LLM_PROVIDER=none`，只有显式启用并配置 Key 时才产生真实调用。
- `LLM_ANALYSIS_LIMIT` 默认 1、最大 10；首次只分析当前热度第一名。
- Key 从环境配置读取且不参与对象表示；HTTP 错误不回显服务端正文。
- 付费请求暂不自动重试，避免在超时边界重复计费；重试与 token 预算留到 3.3。
- 为请求体、认证头、余额不足、异常响应和配置增加 5 个测试；全项目 33 个测试通过。
- 任何发送到聊天、截图、日志或提交中的真实 Key 都视为泄露，必须吊销并重新创建。
- 首次真实运行成功分析 1 个项目，证明 GitHub→清洗→评分→DeepSeek→JSON 校验→终端展示闭环可用。
- 首次输出错误地将 `2026-07-22` 判断为未来时间，暴露模型不知道程序当前日期的问题。
- Prompt 已新增带时区的 `analysis_time`，并要求日期比较只能以该字段为准；终端分析标签改为中文。
- 第二次真实运行正确识别最后推送时间为分析日前一天，未再出现“未来日期”误判。
- 第二次输出使用中文标签，项目简介、关注原因、技术价值、学习建议、适合人群、推荐指数和证据限制均通过合同校验。

- 项目所有者已确认吊销曾暴露的旧 Key；新 Key 仅保存在被 Git 忽略的本地 `.env`。
- 两次单项目真实调用均成功，证明账户余额、认证、模型名称和 API 地址可用。
- 密钥扫描通过，Key 未出现在代码、文档、测试或 Git 清单中。

验证：

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\check.py
.\.venv\Scripts\python.exe -m github_trend_agent
```

## 第 3 步复盘

已经具备：

- 供应商无关的 LLM 边界、结构化 Prompt 与严格 JSON 合同。
- DeepSeek 真实调用、最小调用数量限制、安全错误和单项目失败隔离。
- 日期证据边界和不可信仓库文本防护。

本阶段决策：当前默认只分析 1 个项目，暂不增加 Token 统计和 LangChain，优先完成用户可见的日报闭环。

## 第 4 步进行中

### 4.1 生成 Markdown 日报

目标：把已有的采集、清洗、评分和 AI 分析结果组装成一份可以直接打开阅读的每日技术报告。

已完成：

- 新增不可变 `DailyReport` 数据模型，显式组合日期、评分项目和可选 AI 结果。
- 新增纯渲染函数，生成日期、项目数、Top 项目、链接、热度分项和 AI 分析。
- CLI 在现有采集、清洗、评分和可选 DeepSeek 分析后，打印 Markdown 日报预览。
- AI 未开启、未选中该项目或分析失败时，仍保留项目基础数据。
- 不在日报中显示供应商内部错误，并转义不可信的 HTML/Markdown 文本。
- 新增 5 个日报测试，覆盖无 AI、AI 成功、AI 失败、恶意文本和空报告。
- 不引入新依赖，不访问网络，不写入日报文件。
- 全项目共 38 个测试，格式、静态检查、密钥扫描和测试全部通过。

验证：

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m unittest tests.test_reporter -v
.\.venv\Scripts\python.exe scripts\check.py
```

### 4.2 保存按日期命名的历史日报

目标：将已验证的 Markdown 内容安全保存到本地报告目录，让每天的成果可以保留和回看。

已完成：

- 默认将日报保存到 `reports/YYYY-MM-DD.md`，使用 UTF-8 和统一换行符。
- `reports` 目录不存在时自动创建，成功后向用户显示绝对路径。
- 使用独占创建模式，同日文件存在时拒绝覆盖并返回非零退出码。
- 保存错误不回显文件内容，空 Markdown 在写入前被拒绝。
- 生成的日报默认被 Git 忽略，仅跟踪 `reports/README.md` 记录目录规则。
- 新增 4 个保存测试，覆盖自动建目录、UTF-8、禁止覆盖、目录冲突和空内容。
- 全项目共 42 个测试，格式、静态检查、密钥扫描和测试全部通过。
- 真实运行已生成 `reports/2026-07-24.md`（2,875 字节），终端保存路径、UTF-8 中文和 VS Code Markdown 预览均验收通过。
- 已确认 `.env` 和生成的日报均被 Git 忽略，不会随源码误提交。

验证：

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m unittest tests.test_reporter -v
.\.venv\Scripts\python.exe scripts\check.py
```

## 唯一的下一步

### 4.3 生成 HTML 并发送邮件

目标：将日报转换成邮箱中易读的 HTML，并通过安全的 SMTP 配置发送给指定收件人。

计划：

- 先建立不依赖邮箱的 Markdown/HTML 报告转换与预览。
- 再封装 SMTP 发送器，邮箱、授权码和收件人只通过本地环境配置。
- 使用测试替身验证邮件主题、HTML 正文和失败处理，不先发真实邮件。

## 待办阶段

- 第 5 步：引入数据库，保存仓库快照和日报历史。
- 第 6 步：基于历史快照计算 Star 增量和真实趋势。
- 第 7 步：加入 APScheduler 每日定时运行。
- 第 8 步：提供 FastAPI 查询接口。
- 第 9 步：实现趋势 Dashboard 前端。
- 第 10 步：完成 Docker 部署、运行日志和生产配置。
- 后续增强：把搜索、分析、趋势和报告封装为 Agent 工具。

## 决策与提醒

- 长期记忆采用仓库内 Markdown，而不是项目专属 Skill：内容随代码版本演进，新会话可直接读取，也便于审查历史。
- 当前每次只分析 1 个项目，已足以控制 MVP 调用量；暂不实现 Token 统计与成本预算，避免提前复杂化。
- 暂不引入 FastAPI、Pandas、LangChain、MySQL、Redis 等依赖，避免在需求尚未落地时增加复杂度。
- GitHub API 无法直接提供可靠的历史 Star 增长速度；该指标必须基于后续保存的快照计算。
