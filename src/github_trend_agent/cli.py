"""Command-line entry point for GitHub Trend Agent."""

import sys

from github_trend_agent.config import ConfigurationError, Settings


def build_startup_message(settings: Settings) -> str:
    """Return the message shown when the application starts."""
    auth_mode = "authenticated" if settings.github_auth_enabled else "unauthenticated"
    return f"GitHub Trend Agent is ready ({auth_mode} mode)."


def main() -> int:
    """Run the command-line application and return its process exit code."""
    try:
        settings = Settings.from_env()
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    print(build_startup_message(settings))
    return 0
