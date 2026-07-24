"""Render daily trend data without collecting, analyzing, or saving it."""

import html
from datetime import date
from pathlib import Path

from github_trend_agent.models import (
    AnalysisOutcome,
    DailyReport,
    ProjectAnalysis,
    ScoredRepository,
)

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


def save_html_report(
    report: DailyReport,
    html_content: str,
    output_directory: Path = DEFAULT_REPORT_DIRECTORY,
) -> Path:
    """Save a UTF-8 HTML report without replacing an existing file."""
    return _save_report_text(
        content=html_content,
        path=output_directory / f"{report.report_date.isoformat()}.html",
        output_directory=output_directory,
    )


def _save_report_text(
    *,
    content: str,
    path: Path,
    output_directory: Path,
) -> Path:
    if not content.strip():
        raise ValueError("report content cannot be empty.")
    try:
        output_directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ReportSaveError(f"Daily report could not be saved: {path}") from exc
    try:
        with path.open("x", encoding="utf-8", newline="\n") as report_file:
            report_file.write(content)
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


def render_html_report(report: DailyReport) -> str:
    """Render one standalone HTML report suitable for an email body."""
    outcomes_by_url = _index_outcomes(report.analysis_outcomes)
    project_sections = [
        _render_html_project(position, scored, outcomes_by_url)
        for position, scored in enumerate(report.repositories, start=1)
    ]
    if not project_sections:
        project_sections.append(
            '<p style="color:#64748b;margin:24px 0;">本次没有可展示的项目。</p>'
        )

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width,initial-scale=1">',
            "<title>GitHub 技术趋势日报</title>",
            "</head>",
            '<body style="margin:0;background:#f1f5f9;color:#0f172a;">',
            (
                '<main style="max-width:760px;margin:0 auto;padding:24px;'
                "font-family:Arial,'Microsoft YaHei',sans-serif;\">"
            ),
            (
                '<header style="background:#0f172a;color:#ffffff;padding:24px;'
                'border-radius:12px;">'
            ),
            '<h1 style="font-size:28px;margin:0 0 12px;">GitHub 技术趋势日报</h1>',
            (
                '<p style="margin:0;color:#cbd5e1;">'
                f"日期：{report.report_date.isoformat()} · "
                f"项目数量：{len(report.repositories)}</p>"
            ),
            "</header>",
            *project_sections,
            (
                '<footer style="color:#64748b;font-size:12px;margin-top:24px;">'
                "本报告由 GitHub Trend Agent 自动生成。</footer>"
            ),
            "</main>",
            "</body>",
            "</html>",
            "",
        ]
    )


def _render_html_project(
    position: int,
    scored: ScoredRepository,
    outcomes_by_url: dict[str, AnalysisOutcome],
) -> str:
    repository = scored.repository
    outcome = outcomes_by_url.get(repository.url.casefold())
    return "\n".join(
        [
            (
                '<section style="background:#ffffff;border-radius:12px;'
                'padding:20px;margin-top:18px;border:1px solid #e2e8f0;">'
            ),
            (
                '<h2 style="font-size:20px;margin:0 0 12px;">'
                f"{position}. {_html_text(repository.name)}</h2>"
            ),
            (
                '<p style="margin:0 0 14px;"><a style="color:#2563eb;" '
                f'href="{_html_attribute(repository.url)}">'
                "打开 GitHub 项目</a></p>"
            ),
            '<table role="presentation" style="width:100%;border-collapse:collapse;">',
            _html_metric_row("开发语言", _html_text(repository.language)),
            _html_metric_row("Stars", f"{repository.stars:,}"),
            _html_metric_row("Forks", f"{repository.forks:,}"),
            _html_metric_row("当前热度", f"{scored.total_score:.1f}"),
            _html_metric_row(
                "热度分项",
                (
                    f"Stars {scored.star_score:.1f} / "
                    f"Forks {scored.fork_score:.1f} / "
                    f"活跃度 {scored.freshness_score:.1f}"
                ),
            ),
            "</table>",
            _render_html_analysis(outcome),
            "</section>",
        ]
    )


def _html_metric_row(label: str, value: str) -> str:
    return (
        '<tr><td style="padding:6px 12px 6px 0;color:#64748b;'
        f'width:110px;">{label}</td><td style="padding:6px 0;">{value}</td></tr>'
    )


def _render_html_analysis(outcome: AnalysisOutcome | None) -> str:
    if outcome is None:
        return _html_notice("本项目本次未进行 AI 分析。")
    if outcome.analysis is None:
        return _html_notice("AI 分析未完成，基础项目数据仍然保留。")

    analysis = outcome.analysis
    items = (
        ("项目简介", analysis.summary),
        ("值得关注", analysis.why_worth_attention),
        ("技术价值", analysis.technical_value),
        ("学习建议", analysis.learning_advice),
        ("适合人群", "；".join(analysis.suitable_for)),
        ("推荐指数", _stars(analysis)),
        ("证据限制", "；".join(analysis.evidence_limitations)),
    )
    rendered_items = "".join(
        (
            '<li style="margin:8px 0;"><strong>'
            f"{label}：</strong>{_html_text(value)}</li>"
        )
        for label, value in items
    )
    return (
        '<div style="background:#f8fafc;border-left:4px solid #2563eb;'
        'padding:14px;margin-top:16px;">'
        '<h3 style="font-size:16px;margin:0 0 8px;">AI 分析</h3>'
        f'<ul style="padding-left:20px;margin:0;">{rendered_items}</ul></div>'
    )


def _html_notice(message: str) -> str:
    return (
        '<p style="background:#f8fafc;color:#64748b;padding:12px;'
        f'margin:16px 0 0;">{_html_text(message)}</p>'
    )


def _html_text(value: str) -> str:
    return html.escape(" ".join(value.split()), quote=False)


def _html_attribute(value: str) -> str:
    return html.escape(" ".join(value.split()), quote=True)


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
