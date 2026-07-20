"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field


class ConfigurationError(ValueError):
    """Raised when application configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated runtime settings for GitHub Trend Agent."""

    github_api_url: str
    github_search_query: str
    github_page_size: int
    github_max_repositories: int
    github_max_retries: int
    request_timeout_seconds: float
    top_n: int
    github_token: str | None = field(default=None, repr=False)

    @classmethod
    def from_env(cls, values: Mapping[str, str] | None = None) -> Settings:
        """Build settings from a supplied mapping or the process environment."""
        source = os.environ if values is None else values

        github_api_url = source.get("GITHUB_API_URL", "https://api.github.com")
        github_api_url = github_api_url.strip().rstrip("/")
        if not github_api_url.startswith("https://"):
            raise ConfigurationError("GITHUB_API_URL must use HTTPS.")

        github_search_query = source.get(
            "GITHUB_SEARCH_QUERY",
            "language:python stars:>1000",
        ).strip()
        if not github_search_query:
            raise ConfigurationError("GITHUB_SEARCH_QUERY cannot be empty.")

        request_timeout_seconds = _positive_float(
            "GITHUB_REQUEST_TIMEOUT_SECONDS",
            source.get("GITHUB_REQUEST_TIMEOUT_SECONDS", "10"),
        )
        github_page_size = _bounded_int(
            "GITHUB_PAGE_SIZE",
            source.get("GITHUB_PAGE_SIZE", "25"),
            minimum=1,
            maximum=100,
        )
        github_max_repositories = _bounded_int(
            "GITHUB_MAX_REPOSITORIES",
            source.get("GITHUB_MAX_REPOSITORIES", "50"),
            minimum=1,
            maximum=1000,
        )
        github_max_retries = _bounded_int(
            "GITHUB_MAX_RETRIES",
            source.get("GITHUB_MAX_RETRIES", "2"),
            minimum=0,
            maximum=5,
        )
        top_n = _positive_int("GITHUB_TOP_N", source.get("GITHUB_TOP_N", "10"))
        if top_n > 100:
            raise ConfigurationError("GITHUB_TOP_N must be between 1 and 100.")
        if top_n > github_max_repositories:
            raise ConfigurationError(
                "GITHUB_TOP_N cannot exceed GITHUB_MAX_REPOSITORIES."
            )
        github_token = source.get("GITHUB_TOKEN", "").strip() or None

        return cls(
            github_api_url=github_api_url,
            github_search_query=github_search_query,
            github_page_size=github_page_size,
            github_max_repositories=github_max_repositories,
            github_max_retries=github_max_retries,
            request_timeout_seconds=request_timeout_seconds,
            top_n=top_n,
            github_token=github_token,
        )

    @property
    def github_auth_enabled(self) -> bool:
        """Return whether authenticated GitHub requests are available."""
        return self.github_token is not None

    def require_github_token(self) -> str:
        """Return the GitHub token or raise a safe, actionable error."""
        if self.github_token is None:
            raise ConfigurationError(
                "GITHUB_TOKEN is required for authenticated GitHub requests."
            )
        return self.github_token


def _positive_int(name: str, raw_value: str) -> int:
    """Parse a positive integer without exposing unrelated configuration."""
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a positive integer.") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be a positive integer.")
    return value


def _bounded_int(
    name: str,
    raw_value: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    """Parse an integer constrained to an inclusive range."""
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(
            f"{name} must be between {minimum} and {maximum}."
        ) from exc
    if not minimum <= value <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum} and {maximum}.")
    return value


def _positive_float(name: str, raw_value: str) -> float:
    """Parse a positive floating-point number."""
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a positive number.") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be a positive number.")
    return value
