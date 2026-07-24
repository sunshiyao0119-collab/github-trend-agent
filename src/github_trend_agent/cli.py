"""Command-line entry point for GitHub Trend Agent."""

import sys
from datetime import datetime

from github_trend_agent.cleaner import clean_repositories
from github_trend_agent.config import ConfigurationError, Settings
from github_trend_agent.github_client import GitHubClient, GitHubClientError
from github_trend_agent.llm.analysis import RepositoryAnalyzer, analyze_batch
from github_trend_agent.llm.deepseek import DeepSeekProvider
from github_trend_agent.models import AnalysisOutcome, DailyReport, ScoredRepository
from github_trend_agent.reporter import (
    ReportSaveError,
    render_html_report,
    render_markdown_report,
    save_html_report,
    save_markdown_report,
)
from github_trend_agent.scorer import score_current_heat


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
    scored_repositories = score_current_heat(cleaning_result.repositories)
    print(f"Showing top {settings.top_n} by current heat:")
    if result.rate_limit.remaining is not None:
        print(f"GitHub search requests remaining: {result.rate_limit.remaining}")
    for position, repository in enumerate(
        scored_repositories[: settings.top_n],
        start=1,
    ):
        print(_format_repository(position, repository))

    analysis_outcomes: tuple[AnalysisOutcome, ...] = ()
    if settings.llm_analysis_enabled:
        analysis_outcomes = _analyze_with_deepseek(settings, scored_repositories)

    daily_report = DailyReport(
        report_date=datetime.now().astimezone().date(),
        repositories=scored_repositories[: settings.top_n],
        analysis_outcomes=analysis_outcomes,
    )
    markdown = render_markdown_report(daily_report)
    html_report = render_html_report(daily_report)
    print("\n--- Markdown 日报预览 ---\n")
    print(markdown, end="")
    try:
        report_path = save_markdown_report(daily_report, markdown)
        html_path = save_html_report(daily_report, html_report)
    except ReportSaveError as exc:
        print(f"Report save error: {exc}", file=sys.stderr)
        return 1
    print(f"\n日报已保存：{report_path}")
    print(f"HTML 日报已保存：{html_path}")
    return 0


def _format_repository(position: int, scored: ScoredRepository) -> str:
    repository = scored.repository
    return (
        f"{position}. {repository.name} | "
        f"{repository.language} | heat={scored.total_score:.1f}\n"
        f"   components: stars={scored.star_score:.1f}, "
        f"forks={scored.fork_score:.1f}, "
        f"freshness={scored.freshness_score:.1f}\n"
        f"   counts: stars={repository.stars:,}, forks={repository.forks:,}\n"
        f"   {repository.url}"
    )


def _analyze_with_deepseek(
    settings: Settings,
    scored_repositories: tuple[ScoredRepository, ...],
) -> tuple[AnalysisOutcome, ...]:
    provider = DeepSeekProvider(
        api_key=settings.require_deepseek_api_key(),
        base_url=settings.deepseek_api_url,
        model=settings.deepseek_model,
        timeout_seconds=settings.llm_request_timeout_seconds,
    )
    selected = scored_repositories[: settings.llm_analysis_limit]
    outcomes = analyze_batch(selected, RepositoryAnalyzer(provider))
    print(f"DeepSeek 分析：请求项目数={len(selected)}")
    return outcomes
