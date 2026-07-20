"""Allow the application to run with ``python -m github_trend_agent``."""

from github_trend_agent.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
