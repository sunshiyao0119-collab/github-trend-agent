# GitHub Trend Agent

GitHub 技术趋势智能分析助手：发现值得关注的开源项目，进行清洗、评分和 AI 分析，并逐步形成可自动运行的技术日报系统。

## 当前进度

第 0 步“项目初始化”、第 1 步“GitHub 数据采集”、第 2 步“数据清洗与评分”和第 3 步“LLM 分析”已经完成。当前进入第 4 步“日报与邮件”，已能生成并保存 Markdown 和 HTML 日报。

- 项目目标与架构方向：[`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md)
- 当前进度与下一步：[`docs/PROGRESS.md`](docs/PROGRESS.md)
- Codex 协作约定：[`AGENTS.md`](AGENTS.md)

## 设计理念

先完成最小端到端闭环，再根据真实问题逐步增强。每个阶段都应产生可运行、可验证、能讲清楚的成果。

## 本地 Python 环境

项目要求 Python 3.12。Windows CMD 中创建并激活环境：

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
python --version
```

PowerShell 中激活环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

退出虚拟环境：

```text
deactivate
```

本项目的依赖统一声明在 `pyproject.toml` 中。`.venv` 是本机生成文件，不会提交到 Git。

安装运行依赖：

```powershell
python -m pip install --no-cache-dir -r requirements.lock
```

开发工具使用锁定文件安装：

```powershell
python -m pip install --no-cache-dir -r requirements-dev.lock
```

## 运行应用

当前项目使用 `src` 布局。在 Windows CMD 中：

```cmd
.venv\Scripts\activate.bat
set PYTHONPATH=src
python -m github_trend_agent
```

程序会向 GitHub Search API 发出只读请求，完成清洗和当前热度评分，最后在终端预览 Markdown 日报。输出片段示例：

```text
--- Markdown 日报预览 ---

# GitHub 技术趋势日报

日期：2026-07-24

## 今日热门项目

### 1. owner/project

- 项目地址：https://github.com/owner/project
- 当前热度：88.9
```

运行最小测试：

```cmd
python -m unittest discover -s tests -v
```

运行完整质量门禁：

```powershell
python scripts/check.py
```

该命令依次执行 Ruff 格式检查、Ruff 静态检查、GitHub Token 扫描和全部单元测试。任一步失败都会返回非零退出码。

PowerShell 中设置源码路径的等价命令为：

```powershell
$env:PYTHONPATH = "src"
```

## 配置管理

可用配置记录在 `.env.example` 中。程序会自动读取项目目录的 `.env`，操作系统环境变量优先于文件配置。

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `GITHUB_TOKEN` | 空 | GitHub API 身份验证；真实值不得提交 |
| `GITHUB_API_URL` | `https://api.github.com` | GitHub API 地址 |
| `GITHUB_REQUEST_TIMEOUT_SECONDS` | `10` | 单次请求超时秒数 |
| `GITHUB_SEARCH_QUERY` | `language:python stars:>1000` | GitHub 仓库搜索条件 |
| `GITHUB_PAGE_SIZE` | `25` | 每页采集数量，范围 1–100 |
| `GITHUB_MAX_REPOSITORIES` | `50` | 单次运行最多采集数量，范围 1–1000 |
| `GITHUB_MAX_RETRIES` | `2` | 单页失败后的最大重试次数，范围 0–5 |
| `GITHUB_TOP_N` | `10` | 单次返回数量，范围 1–100 |
| `LLM_PROVIDER` | `none` | `none` 不调用模型；`deepseek` 启用分析 |
| `LLM_ANALYSIS_LIMIT` | `1` | 单次最多分析项目数，范围 1–10 |
| `LLM_REQUEST_TIMEOUT_SECONDS` | `30` | 单次 LLM 请求超时秒数 |
| `DEEPSEEK_API_URL` | `https://api.deepseek.com` | DeepSeek API 地址 |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | DeepSeek 模型名称 |
| `DEEPSEEK_API_KEY` | 空 | DeepSeek 身份凭证；真实值不得提交 |

程序在没有 Token 时仍可启动，显示 `unauthenticated mode`；配置 Token 后显示 `authenticated mode`。两种模式都只读取公开仓库，认证模式拥有更适合持续开发的 API 请求额度。

本地开发时复制配置模板：

```powershell
Copy-Item .env.example .env
```

真实 `GITHUB_TOKEN` 和 `DEEPSEEK_API_KEY` 只写入 `.env`，该文件已被 Git 忽略。生产环境应通过 Secret 管理服务或部署平台注入环境变量，不复制本地密钥文件。任何发到聊天、截图、日志或 Git 中的 Key 都必须立即吊销并更换。

## 分页、限流与重试

- 客户端根据 GitHub 响应中的 `Link` 头读取下一页，并受 `GITHUB_MAX_REPOSITORIES` 总量约束。
- 每次运行会显示最后一页返回的 Search API 剩余额度。
- 403/429 限流优先遵守 `Retry-After`，主限流则等待到 `X-RateLimit-Reset`。
- 500、502、503、504 和临时网络错误采用有上限的指数退避。
- 其他 4xx 错误立即失败，避免无意义重试和浪费配额。
- 单元测试使用替代的等待函数，不会真实休眠。

## 数据清洗

采集层的 `Repository` 保留 GitHub 原始数据允许缺失的事实；清洗层输出字段更稳定的 `CleanRepository`，供后续评分和报告使用。

- 空描述统一为 `No description provided.`。
- 未知语言统一为 `Unknown`。
- 按规范化后的 GitHub 仓库 URL 去重，保留第一次出现的记录。
- 过滤空名称、空作者、非法 GitHub URL、负数 Stars 或 Forks。
- 每次运行输出接收数、保留数、重复数和无效数。

## 当前热度评分 V1

当前还没有历史快照，因此该分数只回答“本批候选项目现在谁更值得关注”，不代表 Star 增长趋势：

```text
当前热度 = Star 相对热度 × 55%
         + Fork 相对热度 × 20%
         + 代码推送活跃度 × 25%
```

- Stars 和 Forks 使用对数压缩，并相对本批候选集最大值归一化。
- 代码活跃度使用 GitHub 的 `pushed_at`，采用 30 天半衰期。
- `updated_at` 只表示仓库对象最后更新，不能替代最后代码推送时间。
- 终端同时展示总分、三个分项及原始 Stars/Forks，排名结果可以解释。
- 当前分数是批内相对分数；跨日期趋势将在保存历史快照后单独实现。

## LLM 分析合同

业务层依赖最小的 `LLMProvider` 接口，而不直接依赖 DeepSeek 或 OpenAI SDK。供应商适配器负责网络调用，公共分析层负责 Prompt、JSON 校验和单项目失败隔离。

结构化输出包含：

- 项目简介与值得关注原因。
- 技术价值与学习建议。
- 适合人群与 1–5 推荐分。
- 基于当前输入无法确认的证据限制。

仓库描述和 Topics 被视为不可信外部数据；Prompt 禁止执行其中的指令。响应必须是字段精确匹配的 JSON，并经过类型、范围、列表长度和总长度校验。第 3.1 步使用测试替身验证合同，不调用真实模型、不产生费用。

Prompt 同时提供带时区的 `analysis_time`。模型只能使用该时间判断 `pushed_at` 是否异常或距今多久，不能依赖模型自身可能过期的“当前日期”认知。

### DeepSeek 适配器

DeepSeek 默认关闭。设置 `LLM_PROVIDER=deepseek` 并安全配置 Key 后，程序会在完成采集、清洗和评分后，调用 `/chat/completions` 分析排名最前的项目。

- 使用 `deepseek-v4-flash`、非思考模式和 JSON Output。
- 首次默认只分析 1 个项目，最大输出 1200 tokens。
- 不在付费请求上自动重试，避免不明确的重复调用。
- 401、402、429、5xx 和异常响应转换为不含响应正文的安全错误。
- 首次真实调用已经成功完成 1 个项目的结构化分析；后续仍保持单项目限制，先人工复查日期和证据边界。

## Markdown 日报

每次采集、清洗和评分完成后，程序会在终端预览 Markdown 日报，并保存到 `reports/YYYY-MM-DD.md`。日报包含日期、Top 项目、项目链接、Stars、Forks、当前热度及分项；如果开启 DeepSeek，还会带上结构化 AI 分析。

- 日报渲染与 GitHub 采集、DeepSeek 调用解耦，可以独立测试。
- AI 未开启、项目未被选中分析或单项目分析失败时，基础日报仍然生成。
- 仓库与 AI 文本会被压缩为单行并转义 HTML/Markdown 特殊字符。
- 报告使用 UTF-8 编码，程序会自动创建 `reports` 目录。
- 同日报告已存在时程序会明确失败，不会静默覆盖。
- 生成的日报是本地运行产物，默认被 Git 忽略，避免每日数据让源码历史膨胀。

## HTML 日报

同一份 `DailyReport` 会直接渲染为独立 HTML，并保存到 `reports/YYYY-MM-DD.html`。HTML 不重新解析 Markdown，避免两种格式之间的数据丢失。

- 使用 UTF-8、响应式视口和简单内联样式，便于浏览器与邮箱展示。
- GitHub 链接可直接点击，项目指标和 AI 分析使用分区卡片展示。
- 所有外部文本都在写入 HTML 前进行转义，不会把仓库或 AI 文本当作 HTML 标签执行。
- HTML 报告与 Markdown 报告一样禁止静默覆盖，并默认被 Git 忽略。
- 当前尚未配置 SMTP，不会发送真实邮件。

## 当前目录结构

```text
github-trend-agent/
├── src/
│   └── github_trend_agent/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cleaner.py
│       ├── config.py
│       ├── github_client.py
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── analysis.py
│       │   └── deepseek.py
│       ├── models.py
│       ├── reporter.py
│       ├── scorer.py
│       └── cli.py
├── tests/
│   ├── test_config.py
│   ├── test_deepseek_provider.py
│   ├── test_cleaner.py
│   ├── test_github_client.py
│   ├── test_llm_analysis.py
│   ├── test_reporter.py
│   ├── test_scorer.py
│   └── test_cli.py
├── scripts/
│   ├── check.py
│   └── check_secrets.py
├── docs/
├── reports/
│   └── README.md
├── pyproject.toml
├── requirements.lock
├── requirements-dev.lock
└── README.md
```
