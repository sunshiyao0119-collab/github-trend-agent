"""Typed domain models used across the application."""

from dataclasses import dataclass
from datetime import datetime


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
