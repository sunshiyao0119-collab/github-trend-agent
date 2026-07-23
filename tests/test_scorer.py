"""Tests for explainable current-heat scoring."""

import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from github_trend_agent.models import CleanRepository
from github_trend_agent.scorer import score_current_heat

NOW = datetime(2026, 7, 22, tzinfo=UTC)


def _repository(**changes: object) -> CleanRepository:
    repository = CleanRepository(
        name="owner/project",
        description="A useful project",
        language="Python",
        stars=100,
        forks=10,
        url="https://github.com/owner/project",
        topics=("python",),
        owner="owner",
        updated_at=NOW,
        pushed_at=NOW,
    )
    return replace(repository, **changes)


class ScoreCurrentHeatTest(unittest.TestCase):
    """Verify score components, ranking, and edge cases."""

    def test_returns_empty_result_for_empty_candidates(self) -> None:
        self.assertEqual(score_current_heat([], now=NOW), ())

    def test_best_value_in_batch_receives_full_relative_component(self) -> None:
        result = score_current_heat(
            [
                _repository(name="small", stars=100, forks=10),
                _repository(name="large", stars=10_000, forks=1_000),
            ],
            now=NOW,
        )

        large = next(item for item in result if item.repository.name == "large")
        self.assertAlmostEqual(large.star_score, 100.0)
        self.assertAlmostEqual(large.fork_score, 100.0)

    def test_log_scale_reduces_the_gap_between_star_counts(self) -> None:
        result = score_current_heat(
            [
                _repository(name="small", stars=100),
                _repository(name="large", stars=10_000),
            ],
            now=NOW,
        )

        small = next(item for item in result if item.repository.name == "small")
        self.assertGreater(small.star_score, 49.0)

    def test_freshness_has_a_thirty_day_half_life(self) -> None:
        result = score_current_heat(
            [_repository(pushed_at=NOW - timedelta(days=30))],
            now=NOW,
        )

        self.assertAlmostEqual(result[0].freshness_score, 50.0)

    def test_ranks_by_total_score_then_name(self) -> None:
        result = score_current_heat(
            [
                _repository(name="older", pushed_at=NOW - timedelta(days=90)),
                _repository(name="recent", pushed_at=NOW),
            ],
            now=NOW,
        )

        self.assertEqual([item.repository.name for item in result], ["recent", "older"])

    def test_rejects_datetime_without_timezone(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone"):
            score_current_heat([_repository()], now=datetime(2026, 7, 22))


if __name__ == "__main__":
    unittest.main()
