"""Command-line entry point for GitHub Trend Agent."""

import sys

from github_trend_agent.cleaner import clean_repositories
from github_trend_agent.config import ConfigurationError, Settings
from github_trend_agent.github_client import GitHubClient, GitHubClientError
from github_trend_agent.models import CleanRepository


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
        result = client.search_repositories(
            settings.github_search_query,
            max_repositories=settings.github_max_repositories,
            page_size=settings.github_page_size,
        )
    except GitHubClientError as exc:
        print(f"GitHub collection error: {exc}", file=sys.stderr)
        return 1

    cleaning_result = clean_repositories(result.repositories)
    print(
        f"Collected {cleaning_result.total_received} repositories "
        f"across {result.pages_fetched} page(s)."
    )
    print(
        f"Cleaning: kept={len(cleaning_result.repositories)}, "
        f"duplicates={cleaning_result.duplicates_removed}, "
        f"invalid={cleaning_result.invalid_removed}."
    )
    print(f"Showing top {settings.top_n}:")
    if result.rate_limit.remaining is not None:
        print(f"GitHub search requests remaining: {result.rate_limit.remaining}")
    for position, repository in enumerate(
        cleaning_result.repositories[: settings.top_n],
        start=1,
    ):
        print(_format_repository(position, repository))
    return 0


def _format_repository(position: int, repository: CleanRepository) -> str:
    return (
        f"{position}. {repository.name} | "
        f"{repository.language} | stars={repository.stars:,}\n"
        f"   {repository.url}"
    )
