"""Typed domain models used across the application."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class Repository:
    """A normalized GitHub repository returned by the collection layer."""

    name: str
    description: str | None
    language: str | None
    stars: int
    forks: int
    url: str
    topics: tuple[str, ...]
    owner: str
    updated_at: datetime
    pushed_at: datetime


@dataclass(frozen=True, slots=True)
class CleanRepository:
    """A repository normalized and validated for downstream analysis."""

    name: str
    description: str
    language: str
    stars: int
    forks: int
    url: str
    topics: tuple[str, ...]
    owner: str
    updated_at: datetime
    pushed_at: datetime


@dataclass(frozen=True, slots=True)
class CleaningResult:
    """Clean repositories and the data-quality counts for one run."""

    repositories: tuple[CleanRepository, ...]
    total_received: int
    duplicates_removed: int
    invalid_removed: int


@dataclass(frozen=True, slots=True)
class ScoredRepository:
    """A clean repository with explainable current-heat components."""

    repository: CleanRepository
    total_score: float
    star_score: float
    fork_score: float
    freshness_score: float


@dataclass(frozen=True, slots=True)
class ProjectAnalysis:
    """Validated structured analysis returned by an LLM."""

    summary: str
    why_worth_attention: str
    technical_value: str
    learning_advice: str
    suitable_for: tuple[str, ...]
    recommendation_score: int
    evidence_limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AnalysisOutcome:
    """One repository analysis result, including recoverable failure details."""

    scored_repository: ScoredRepository
    analysis: ProjectAnalysis | None
    error: str | None


@dataclass(frozen=True, slots=True)
class DailyReport:
    """The provider-neutral data required to render one daily report."""

    report_date: date
    repositories: tuple[ScoredRepository, ...]
    analysis_outcomes: tuple[AnalysisOutcome, ...] = ()


@dataclass(frozen=True, slots=True)
class RateLimitInfo:
    """Rate-limit state reported by the most recent GitHub response."""

    limit: int | None
    remaining: int | None
    reset_at: datetime | None
    resource: str | None


@dataclass(frozen=True, slots=True)
class RepositorySearchResult:
    """Repositories plus collection metadata needed by callers."""

    repositories: tuple[Repository, ...]
    pages_fetched: int
    rate_limit: RateLimitInfo
