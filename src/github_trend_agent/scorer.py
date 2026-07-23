"""Explainable current-heat scoring for cleaned repositories."""

import math
from collections.abc import Iterable
from datetime import UTC, datetime

from github_trend_agent.models import CleanRepository, ScoredRepository

STAR_WEIGHT = 0.55
FORK_WEIGHT = 0.20
FRESHNESS_WEIGHT = 0.25
FRESHNESS_HALF_LIFE_DAYS = 30.0


def score_current_heat(
    repositories: Iterable[CleanRepository],
    *,
    now: datetime | None = None,
) -> tuple[ScoredRepository, ...]:
    """Score and rank current heat without claiming historical growth."""
    candidates = tuple(repositories)
    if not candidates:
        return ()

    scoring_time = now or datetime.now(UTC)
    if scoring_time.tzinfo is None:
        raise ValueError("now must include timezone information.")

    max_stars = max(repository.stars for repository in candidates)
    max_forks = max(repository.forks for repository in candidates)
    scored: list[ScoredRepository] = []

    for repository in candidates:
        if repository.pushed_at.tzinfo is None:
            raise ValueError("repository pushed_at must include timezone information.")

        star_score = _log_relative_score(repository.stars, max_stars)
        fork_score = _log_relative_score(repository.forks, max_forks)
        freshness_score = _freshness_score(repository.pushed_at, scoring_time)
        total_score = (
            star_score * STAR_WEIGHT
            + fork_score * FORK_WEIGHT
            + freshness_score * FRESHNESS_WEIGHT
        )
        scored.append(
            ScoredRepository(
                repository=repository,
                total_score=total_score,
                star_score=star_score,
                fork_score=fork_score,
                freshness_score=freshness_score,
            )
        )

    return tuple(
        sorted(
            scored,
            key=lambda item: (-item.total_score, item.repository.name.casefold()),
        )
    )


def _log_relative_score(value: int, maximum: int) -> float:
    if maximum == 0:
        return 0.0
    return math.log1p(value) / math.log1p(maximum) * 100.0


def _freshness_score(pushed_at: datetime, now: datetime) -> float:
    age_seconds = max(0.0, (now - pushed_at).total_seconds())
    age_days = age_seconds / 86_400
    return 100.0 * math.pow(0.5, age_days / FRESHNESS_HALF_LIFE_DAYS)
