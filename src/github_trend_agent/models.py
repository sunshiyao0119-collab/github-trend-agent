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
