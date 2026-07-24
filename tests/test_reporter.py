"""Tests for the provider-neutral Markdown daily report renderer."""

import unittest
from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from github_trend_agent.models import (
    AnalysisOutcome,
    CleanRepository,
    DailyReport,
    ProjectAnalysis,
    ScoredRepository,
)
from github_trend_agent.reporter import (
    ReportAlreadyExistsError,
    ReportSaveError,
    render_html_report,
    render_markdown_report,
    save_html_report,
    save_markdown_report,
)


def _scored_repository() -> ScoredRepository:
    repository = CleanRepository(
        name="owner/project",
        description="A useful project",
        language="Python",
        stars=1_234,
        forks=56,
        url="https://github.com/owner/project",
        topics=("python",),
        owner="owner",
        updated_at=datetime(2026, 7, 24, tzinfo=UTC),
        pushed_at=datetime(2026, 7, 23, tzinfo=UTC),
    )
    return ScoredRepository(
        repository=repository,
        total_score=88.88,
        star_score=80.0,
        fork_score=70.0,
        freshness_score=99.0,
    )


class RenderMarkdownReportTest(unittest.TestCase):
    def test_renders_repository_data_without_ai(self) -> None:
        report = DailyReport(
            report_date=date(2026, 7, 24),
            repositories=(_scored_repository(),),
        )

        markdown = render_markdown_report(report)

        self.assertIn("# GitHub 技术趋势日报", markdown)
        self.assertIn("日期：2026-07-24", markdown)
        self.assertIn("### 1. owner/project", markdown)
        self.assertIn("Stars：1,234", markdown)
        self.assertIn("当前热度：88.9", markdown)
        self.assertIn("本次未进行 AI 分析", markdown)

    def test_renders_structured_ai_analysis(self) -> None:
        scored = _scored_repository()
        outcome = AnalysisOutcome(
            scored_repository=scored,
            analysis=ProjectAnalysis(
                summary="一个实用项目",
                why_worth_attention="热度较高",
                technical_value="学习工程结构",
                learning_advice="先阅读文档",
                suitable_for=("Python 学习者",),
                recommendation_score=4,
                evidence_limitations=("未阅读源码",),
            ),
            error=None,
        )
        report = DailyReport(
            report_date=date(2026, 7, 24),
            repositories=(scored,),
            analysis_outcomes=(outcome,),
        )

        markdown = render_markdown_report(report)

        self.assertIn("#### AI 分析", markdown)
        self.assertIn("项目简介：一个实用项目", markdown)
        self.assertIn("推荐指数：★★★★☆", markdown)

    def test_ai_failure_keeps_report_and_hides_internal_error(self) -> None:
        scored = _scored_repository()
        outcome = AnalysisOutcome(
            scored_repository=scored,
            analysis=None,
            error="internal provider detail",
        )

        markdown = render_markdown_report(
            DailyReport(
                report_date=date(2026, 7, 24),
                repositories=(scored,),
                analysis_outcomes=(outcome,),
            )
        )

        self.assertIn("AI 分析未完成", markdown)
        self.assertNotIn("internal provider detail", markdown)

    def test_escapes_untrusted_multiline_analysis_text(self) -> None:
        scored = _scored_repository()
        outcome = AnalysisOutcome(
            scored_repository=scored,
            analysis=ProjectAnalysis(
                summary="first\n<script>alert(1)</script> *bold*",
                why_worth_attention="safe",
                technical_value="safe",
                learning_advice="safe",
                suitable_for=("learner",),
                recommendation_score=3,
                evidence_limitations=("limited",),
            ),
            error=None,
        )

        markdown = render_markdown_report(
            DailyReport(
                report_date=date(2026, 7, 24),
                repositories=(scored,),
                analysis_outcomes=(outcome,),
            )
        )

        self.assertNotIn("<script>", markdown)
        self.assertNotIn("\n<script>", markdown)
        self.assertIn("&lt;script&gt;", markdown)
        self.assertIn("\\*bold\\*", markdown)

    def test_renders_empty_report(self) -> None:
        markdown = render_markdown_report(
            DailyReport(report_date=date(2026, 7, 24), repositories=())
        )

        self.assertIn("项目数量：0", markdown)
        self.assertIn("没有可展示的项目", markdown)


class RenderHTMLReportTest(unittest.TestCase):
    def test_renders_standalone_html_with_repository_link(self) -> None:
        report = DailyReport(
            report_date=date(2026, 7, 24),
            repositories=(_scored_repository(),),
        )

        html_report = render_html_report(report)

        self.assertTrue(html_report.startswith("<!doctype html>"))
        self.assertIn('<meta charset="utf-8">', html_report)
        self.assertIn("日期：2026-07-24", html_report)
        self.assertIn("1. owner/project", html_report)
        self.assertIn('href="https://github.com/owner/project"', html_report)
        self.assertIn("Stars 80.0 / Forks 70.0 / 活跃度 99.0", html_report)
        self.assertIn("本项目本次未进行 AI 分析", html_report)

    def test_renders_ai_analysis_and_recommendation(self) -> None:
        scored = _scored_repository()
        outcome = AnalysisOutcome(
            scored_repository=scored,
            analysis=ProjectAnalysis(
                summary="一个实用项目",
                why_worth_attention="热度较高",
                technical_value="学习工程结构",
                learning_advice="先阅读文档",
                suitable_for=("Python 学习者",),
                recommendation_score=4,
                evidence_limitations=("未阅读源码",),
            ),
            error=None,
        )

        html_report = render_html_report(
            DailyReport(
                report_date=date(2026, 7, 24),
                repositories=(scored,),
                analysis_outcomes=(outcome,),
            )
        )

        self.assertIn("<h3", html_report)
        self.assertIn("AI 分析", html_report)
        self.assertIn("项目简介：</strong>一个实用项目", html_report)
        self.assertIn("推荐指数：</strong>★★★★☆", html_report)

    def test_escapes_html_and_hides_internal_failure(self) -> None:
        scored = _scored_repository()
        malicious = AnalysisOutcome(
            scored_repository=scored,
            analysis=ProjectAnalysis(
                summary='<script>alert("x")</script>',
                why_worth_attention="safe",
                technical_value="safe",
                learning_advice="safe",
                suitable_for=("learner",),
                recommendation_score=3,
                evidence_limitations=("limited",),
            ),
            error=None,
        )
        failed = AnalysisOutcome(
            scored_repository=scored,
            analysis=None,
            error="internal provider detail",
        )

        malicious_html = render_html_report(
            DailyReport(
                report_date=date(2026, 7, 24),
                repositories=(scored,),
                analysis_outcomes=(malicious,),
            )
        )
        failed_html = render_html_report(
            DailyReport(
                report_date=date(2026, 7, 24),
                repositories=(scored,),
                analysis_outcomes=(failed,),
            )
        )

        self.assertNotIn("<script>", malicious_html)
        self.assertIn("&lt;script&gt;", malicious_html)
        self.assertIn("AI 分析未完成", failed_html)
        self.assertNotIn("internal provider detail", failed_html)


class SaveMarkdownReportTest(unittest.TestCase):
    def test_creates_directory_and_saves_utf8_report(self) -> None:
        report = DailyReport(report_date=date(2026, 7, 24), repositories=())
        markdown = "# 日报\n\n中文内容\n"

        with TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory) / "reports"
            saved_path = save_markdown_report(
                report,
                markdown,
                output_directory,
            )

            self.assertEqual(saved_path.name, "2026-07-24.md")
            self.assertEqual(saved_path.read_text(encoding="utf-8"), markdown)

    def test_does_not_overwrite_existing_daily_report(self) -> None:
        report = DailyReport(report_date=date(2026, 7, 24), repositories=())

        with TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory)
            save_markdown_report(report, "first\n", output_directory)

            with self.assertRaisesRegex(
                ReportAlreadyExistsError,
                "already exists",
            ):
                save_markdown_report(report, "second\n", output_directory)

            saved_path = output_directory / "2026-07-24.md"
            self.assertEqual(saved_path.read_text(encoding="utf-8"), "first\n")

    def test_maps_directory_creation_failure_to_safe_error(self) -> None:
        report = DailyReport(report_date=date(2026, 7, 24), repositories=())

        with TemporaryDirectory() as temporary_directory:
            invalid_directory = Path(temporary_directory) / "not-a-directory"
            invalid_directory.write_text("occupied", encoding="utf-8")

            with self.assertRaisesRegex(ReportSaveError, "could not be saved"):
                save_markdown_report(report, "content\n", invalid_directory)

    def test_rejects_empty_markdown_before_writing(self) -> None:
        report = DailyReport(report_date=date(2026, 7, 24), repositories=())

        with TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory) / "reports"

            with self.assertRaisesRegex(ValueError, "cannot be empty"):
                save_markdown_report(report, "  \n", output_directory)

            self.assertFalse(output_directory.exists())

    def test_saves_html_as_separate_utf8_file(self) -> None:
        report = DailyReport(report_date=date(2026, 7, 24), repositories=())
        html_report = "<!doctype html><p>中文</p>\n"

        with TemporaryDirectory() as temporary_directory:
            saved_path = save_html_report(
                report,
                html_report,
                Path(temporary_directory),
            )

            self.assertEqual(saved_path.name, "2026-07-24.html")
            self.assertEqual(saved_path.read_text(encoding="utf-8"), html_report)


if __name__ == "__main__":
    unittest.main()
