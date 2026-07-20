"""Command-line entry point for GitHub Trend Agent."""

import sys

from github_trend_agent.config import ConfigurationError, Settings
from github_trend_agent.github_client import GitHubClient, GitHubClientError
from github_trend_agent.models import Repository


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

    client = GitHubClient(settings)
    try:
        repositories = client.search_repositories(
            settings.github_search_query,
            settings.top_n,
        )
    except GitHubClientError as exc:
        print(f"GitHub collection error: {exc}", file=sys.stderr)
        return 1

    print(f"Found {len(repositories)} repositories:")
    for position, repository in enumerate(repositories, start=1):
        print(_format_repository(position, repository))
    return 0


def _format_repository(position: int, repository: Repository) -> str:
    language = repository.language or "Unknown"
    return (
        f"{position}. {repository.name} | "
        f"{language} | stars={repository.stars:,}\n"
        f"   {repository.url}"
    )
