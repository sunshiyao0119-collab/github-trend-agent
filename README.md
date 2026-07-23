# GitHub Trend Agent

GitHub 技术趋势智能分析助手：发现值得关注的开源项目，进行清洗、评分和 AI 分析，并逐步形成可自动运行的技术日报系统。

## 当前进度

第 0 步“项目初始化”、第 1 步“GitHub 数据采集”和第 2 步“数据清洗与评分”已经完成，项目进入第 3 步“LLM 分析”。当前程序可认证采集并清洗 50 个公开仓库，计算可解释的当前热度并展示 Top 10。

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

程序会向 GitHub Search API 发出只读请求，并显示按 Star 排序的公开仓库。输出示例：

```text
GitHub Trend Agent is ready (unauthenticated mode).
Collected 50 repositories across 2 page(s); showing top 10:
GitHub search requests remaining: 8
1. public-apis/public-apis | Python | stars=451,458
   https://github.com/public-apis/public-apis
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

程序在没有 Token 时仍可启动，显示 `unauthenticated mode`；配置 Token 后显示 `authenticated mode`。两种模式都只读取公开仓库，认证模式拥有更适合持续开发的 API 请求额度。

本地开发时复制配置模板：

```powershell
Copy-Item .env.example .env
```

真实 `GITHUB_TOKEN` 只写入 `.env`，该文件已被 Git 忽略。生产环境应通过 Secret 管理服务或部署平台注入环境变量，不复制本地密钥文件。

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
│       ├── models.py
│       ├── scorer.py
│       └── cli.py
├── tests/
│   ├── test_config.py
│   ├── test_cleaner.py
│   ├── test_github_client.py
│   ├── test_scorer.py
│   └── test_cli.py
├── scripts/
│   ├── check.py
│   └── check_secrets.py
├── docs/
├── pyproject.toml
├── requirements.lock
├── requirements-dev.lock
└── README.md
```
