"""Render daily trend data without collecting, analyzing, or saving it."""

import html
from datetime import date
from pathlib import Path

from github_trend_agent.models import AnalysisOutcome, DailyReport, ProjectAnalysis

DEFAULT_REPORT_DIRECTORY = Path("reports")


class ReportSaveError(RuntimeError):
    """Raised when a rendered report cannot be saved safely."""


class ReportAlreadyExistsError(ReportSaveError):
    """Raised when saving would overwrite an existing daily report."""


def report_file_path(
    report_date: date,
    output_directory: Path = DEFAULT_REPORT_DIRECTORY,
) -> Path:
    """Return the deterministic path for one daily Markdown report."""
    return output_directory / f"{report_date.isoformat()}.md"


def save_markdown_report(
    report: DailyReport,
    markdown: str,
    output_directory: Path = DEFAULT_REPORT_DIRECTORY,
) -> Path:
    """Save UTF-8 Markdown without replacing an existing daily report."""
    if not markdown.strip():
        raise ValueError("markdown cannot be empty.")

    path = report_file_path(report.report_date, output_directory)
    try:
        output_directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ReportSaveError(f"Daily report could not be saved: {path}") from exc
    try:
        with path.open("x", encoding="utf-8", newline="\n") as report_file:
            report_file.write(markdown)
    except FileExistsError as exc:
        raise ReportAlreadyExistsError(f"Daily report already exists: {path}") from exc
    except OSError as exc:
        raise ReportSaveError(f"Daily report could not be saved: {path}") from exc
    return path.resolve()


def render_markdown_report(report: DailyReport) -> str:
    """Render one self-contained Markdown report from domain data."""
    lines = [
        "# GitHub 技术趋势日报",
        "",
        f"日期：{report.report_date.isoformat()}",
        "",
        f"项目数量：{len(report.repositories)}",
        "",
        "## 今日热门项目",
        "",
    ]
    if not report.repositories:
        lines.append("本次没有可展示的项目。")
        return "\n".join(lines) + "\n"

    outcomes_by_url = _index_outcomes(report.analysis_outcomes)
    for position, scored in enumerate(report.repositories, start=1):
        repository = scored.repository
        lines.extend(
            [
                f"### {position}. {_inline(repository.name)}",
                "",
                f"- 项目地址：{_inline(repository.url)}",
                f"- 开发语言：{_inline(repository.language)}",
                f"- Stars：{repository.stars:,}",
                f"- Forks：{repository.forks:,}",
                f"- 当前热度：{scored.total_score:.1f}",
                (
                    "- 热度分项："
                    f"Stars {scored.star_score:.1f} / "
                    f"Forks {scored.fork_score:.1f} / "
                    f"活跃度 {scored.freshness_score:.1f}"
                ),
                "",
            ]
        )
        outcome = outcomes_by_url.get(repository.url.casefold())
        lines.extend(_render_analysis(outcome))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _index_outcomes(
    outcomes: tuple[AnalysisOutcome, ...],
) -> dict[str, AnalysisOutcome]:
    indexed: dict[str, AnalysisOutcome] = {}
    for outcome in outcomes:
        key = outcome.scored_repository.repository.url.casefold()
        if key in indexed:
            raise ValueError("A report cannot contain duplicate analysis outcomes.")
        indexed[key] = outcome
    return indexed


def _render_analysis(outcome: AnalysisOutcome | None) -> list[str]:
    if outcome is None:
        return ["> 本项目本次未进行 AI 分析。"]
    if outcome.analysis is None:
        return ["> AI 分析未完成，基础项目数据仍然保留。"]

    analysis = outcome.analysis
    return [
        "#### AI 分析",
        "",
        f"- 项目简介：{_inline(analysis.summary)}",
        f"- 值得关注：{_inline(analysis.why_worth_attention)}",
        f"- 技术价值：{_inline(analysis.technical_value)}",
        f"- 学习建议：{_inline(analysis.learning_advice)}",
        f"- 适合人群：{_join(analysis.suitable_for)}",
        f"- 推荐指数：{_stars(analysis)}",
        f"- 证据限制：{_join(analysis.evidence_limitations)}",
    ]


def _inline(value: str) -> str:
    """Keep untrusted text on one escaped Markdown line."""
    normalized = " ".join(value.split())
    escaped = html.escape(normalized, quote=False)
    for character in ("\\", "`", "*", "_", "[", "]"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped


def _join(values: tuple[str, ...]) -> str:
    return "；".join(_inline(value) for value in values)


def _stars(analysis: ProjectAnalysis) -> str:
    return "★" * analysis.recommendation_score + "☆" * (
        5 - analysis.recommendation_score
    )
