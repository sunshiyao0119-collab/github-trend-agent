# GitHub Trend Agent

GitHub 技术趋势智能分析助手：发现值得关注的开源项目，进行清洗、评分和 AI 分析，并逐步形成可自动运行的技术日报系统。

## 当前进度

第 0 步“项目初始化”已经完成，项目进入第 1 步“GitHub 数据采集”。当前还没有业务运行依赖。

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

预期输出：

```text
GitHub Trend Agent is ready (unauthenticated mode).
```

运行最小测试：

```cmd
python -m unittest discover -s tests -v
```

运行完整质量门禁：

```powershell
python scripts/check.py
```

该命令依次执行 Ruff 格式检查、Ruff 静态检查和全部单元测试。任一步失败都会返回非零退出码。

PowerShell 中设置源码路径的等价命令为：

```powershell
$env:PYTHONPATH = "src"
```

## 配置管理

可用配置记录在 `.env.example` 中。当前程序从操作系统环境变量读取配置，不会自动读取 `.env` 文件。

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `GITHUB_TOKEN` | 空 | GitHub API 身份验证；真实值不得提交 |
| `GITHUB_API_URL` | `https://api.github.com` | GitHub API 地址 |
| `GITHUB_REQUEST_TIMEOUT_SECONDS` | `10` | 单次请求超时秒数 |
| `GITHUB_TOP_N` | `10` | 最终保留的项目数量 |

程序在没有 Token 时仍可启动，显示 `unauthenticated mode`。数据采集阶段需要更高 API 限额时，再配置真实 Token。

## 当前目录结构

```text
github-trend-agent/
├── src/
│   └── github_trend_agent/
│       ├── __init__.py
│       ├── __main__.py
│       ├── config.py
│       └── cli.py
├── tests/
│   ├── test_config.py
│   └── test_cli.py
├── scripts/
│   └── check.py
├── docs/
├── pyproject.toml
├── requirements-dev.lock
└── README.md
```
