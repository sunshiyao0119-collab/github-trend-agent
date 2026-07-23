"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from dotenv import dotenv_values, find_dotenv


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
    llm_provider: str
    llm_analysis_limit: int
    llm_request_timeout_seconds: float
    deepseek_api_url: str
    deepseek_model: str
    github_token: str | None = field(default=None, repr=False)
    deepseek_api_key: str | None = field(default=None, repr=False)

    @classmethod
    def from_env(cls, values: Mapping[str, str] | None = None) -> Settings:
        """Build settings from a supplied mapping or the process environment."""
        source = _runtime_environment() if values is None else values

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
        llm_provider = source.get("LLM_PROVIDER", "none").strip().casefold()
        if llm_provider not in {"none", "deepseek"}:
            raise ConfigurationError("LLM_PROVIDER must be none or deepseek.")
        llm_analysis_limit = _bounded_int(
            "LLM_ANALYSIS_LIMIT",
            source.get("LLM_ANALYSIS_LIMIT", "1"),
            minimum=1,
            maximum=10,
        )
        if llm_analysis_limit > top_n:
            raise ConfigurationError("LLM_ANALYSIS_LIMIT cannot exceed GITHUB_TOP_N.")
        llm_request_timeout_seconds = _positive_float(
            "LLM_REQUEST_TIMEOUT_SECONDS",
            source.get("LLM_REQUEST_TIMEOUT_SECONDS", "30"),
        )
        deepseek_api_url = (
            source.get(
                "DEEPSEEK_API_URL",
                "https://api.deepseek.com",
            )
            .strip()
            .rstrip("/")
        )
        if not deepseek_api_url.startswith("https://"):
            raise ConfigurationError("DEEPSEEK_API_URL must use HTTPS.")
        deepseek_model = source.get(
            "DEEPSEEK_MODEL",
            "deepseek-v4-flash",
        ).strip()
        if not deepseek_model:
            raise ConfigurationError("DEEPSEEK_MODEL cannot be empty.")
        deepseek_api_key = source.get("DEEPSEEK_API_KEY", "").strip() or None
        if llm_provider == "deepseek" and deepseek_api_key is None:
            raise ConfigurationError(
                "DEEPSEEK_API_KEY is required when LLM_PROVIDER=deepseek."
            )

        return cls(
            github_api_url=github_api_url,
            github_search_query=github_search_query,
            github_page_size=github_page_size,
            github_max_repositories=github_max_repositories,
            github_max_retries=github_max_retries,
            request_timeout_seconds=request_timeout_seconds,
            top_n=top_n,
            llm_provider=llm_provider,
            llm_analysis_limit=llm_analysis_limit,
            llm_request_timeout_seconds=llm_request_timeout_seconds,
            deepseek_api_url=deepseek_api_url,
            deepseek_model=deepseek_model,
            github_token=github_token,
            deepseek_api_key=deepseek_api_key,
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

    @property
    def llm_analysis_enabled(self) -> bool:
        """Return whether a real LLM provider should be called."""
        return self.llm_provider != "none"

    def require_deepseek_api_key(self) -> str:
        """Return the DeepSeek key or raise without exposing configuration."""
        if self.deepseek_api_key is None:
            raise ConfigurationError("DEEPSEEK_API_KEY is required for DeepSeek.")
        return self.deepseek_api_key


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


def _runtime_environment() -> dict[str, str]:
    """Load local .env values, then let process variables override them."""
    env_path = find_dotenv(usecwd=True)
    file_values = dotenv_values(env_path) if env_path else {}
    source = {
        key: value for key, value in file_values.items() if isinstance(value, str)
    }
    source.update(os.environ)
    return source
