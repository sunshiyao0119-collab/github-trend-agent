"""GitHub REST API client with bounded pagination and retry behavior."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from github_trend_agent.config import Settings
from github_trend_agent.models import RateLimitInfo, Repository, RepositorySearchResult

GITHUB_API_VERSION = "2026-03-10"
_TRANSIENT_HTTP_STATUSES = frozenset({500, 502, 503, 504})
_LINK_PATTERN = re.compile(r'<([^>]+)>;\s*rel="([^"]+)"')


class GitHubClientError(RuntimeError):
    """Raised when GitHub data cannot be requested or validated."""


class GitHubClient:
    """Collect and normalize repository data from the GitHub REST API."""

    def __init__(
        self,
        settings: Settings,
        opener: Callable[..., Any] = urlopen,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._settings = settings
        self._opener = opener
        self._sleeper = sleeper
        self._clock = clock

    def search_repositories(
        self,
        query: str,
        *,
        max_repositories: int,
        page_size: int,
    ) -> RepositorySearchResult:
        """Return a bounded, paginated repository search result."""
        if not query.strip():
            raise ValueError("GitHub search query cannot be empty.")
        if not 1 <= max_repositories <= 1000:
            raise ValueError("Repository limit must be between 1 and 1000.")
        if not 1 <= page_size <= 100:
            raise ValueError("GitHub page size must be between 1 and 100.")

        per_page = min(page_size, max_repositories)
        parameters = urlencode(
            {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": per_page,
            }
        )
        next_url: str | None = (
            f"{self._settings.github_api_url}/search/repositories?{parameters}"
        )
        max_pages = (max_repositories + per_page - 1) // per_page
        repositories: list[Repository] = []
        pages_fetched = 0
        rate_limit = RateLimitInfo(None, None, None, None)

        while next_url is not None and pages_fetched < max_pages:
            payload, headers = self._request_json(next_url)
            items = payload.get("items") if isinstance(payload, dict) else None
            if not isinstance(items, list):
                raise GitHubClientError("GitHub API response is missing an items list.")

            remaining_capacity = max_repositories - len(repositories)
            repositories.extend(
                _repository_from_payload(item) for item in items[:remaining_capacity]
            )
            pages_fetched += 1
            rate_limit = _rate_limit_from_headers(headers)

            if len(repositories) >= max_repositories:
                break
            next_url = _next_link(_header(headers, "Link"))

        return RepositorySearchResult(
            repositories=tuple(repositories),
            pages_fetched=pages_fetched,
            rate_limit=rate_limit,
        )

    def _request_json(self, url: str) -> tuple[object, object]:
        """Request one page, retrying only transient or rate-limited failures."""
        for retry_number in range(self._settings.github_max_retries + 1):
            request = Request(url, headers=self._headers())
            try:
                with self._opener(
                    request,
                    timeout=self._settings.request_timeout_seconds,
                ) as response:
                    raw_payload = response.read()
                    headers = response.headers
            except HTTPError as exc:
                message = _read_github_error_message(exc)
                delay = _http_retry_delay(
                    exc,
                    message=message,
                    retry_number=retry_number,
                    clock=self._clock,
                )
                if delay is None or retry_number >= self._settings.github_max_retries:
                    raise GitHubClientError(
                        f"GitHub API returned HTTP {exc.code}: {message}"
                    ) from exc
                self._sleeper(delay)
                continue
            except (URLError, TimeoutError, OSError) as exc:
                if retry_number >= self._settings.github_max_retries:
                    raise GitHubClientError("GitHub API request failed.") from exc
                self._sleeper(2.0**retry_number)
                continue

            try:
                return json.loads(raw_payload), headers
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise GitHubClientError("GitHub API returned invalid JSON.") from exc

        raise AssertionError("Retry loop exited unexpectedly.")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "github-trend-agent/0.1",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }
        if self._settings.github_token is not None:
            headers["Authorization"] = f"Bearer {self._settings.github_token}"
        return headers


def _http_retry_delay(
    error: HTTPError,
    *,
    message: str,
    retry_number: int,
    clock: Callable[[], float],
) -> float | None:
    """Return a standards-aware retry delay, or None for fast failure."""
    if error.code in _TRANSIENT_HTTP_STATUSES:
        return 2.0**retry_number

    remaining = _header(error.headers, "X-RateLimit-Remaining")
    is_rate_limited = (
        error.code == 429 or remaining == "0" or "rate limit" in message.lower()
    )
    if error.code not in {403, 429} or not is_rate_limited:
        return None

    retry_after = _positive_float_header(error.headers, "Retry-After")
    if retry_after is not None:
        return retry_after

    reset_at = _positive_float_header(error.headers, "X-RateLimit-Reset")
    if remaining == "0" and reset_at is not None:
        return max(reset_at - clock(), 0.0) + 1.0

    return 60.0 * (2.0**retry_number)


def _read_github_error_message(error: HTTPError) -> str:
    """Extract a safe error message without including request headers."""
    try:
        payload = json.loads(error.read())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return error.reason

    if isinstance(payload, dict) and isinstance(payload.get("message"), str):
        return payload["message"]
    return error.reason


def _next_link(link_header: str | None) -> str | None:
    if link_header is None:
        return None
    links = {relation: url for url, relation in _LINK_PATTERN.findall(link_header)}
    return links.get("next")


def _rate_limit_from_headers(headers: object) -> RateLimitInfo:
    reset_timestamp = _positive_int_header(headers, "X-RateLimit-Reset")
    reset_at = (
        datetime.fromtimestamp(reset_timestamp, tz=UTC)
        if reset_timestamp is not None
        else None
    )
    return RateLimitInfo(
        limit=_positive_int_header(headers, "X-RateLimit-Limit"),
        remaining=_non_negative_int_header(headers, "X-RateLimit-Remaining"),
        reset_at=reset_at,
        resource=_header(headers, "X-RateLimit-Resource"),
    )


def _header(headers: object, name: str) -> str | None:
    getter = getattr(headers, "get", None)
    if getter is None:
        return None
    value = getter(name)
    if value is None:
        value = getter(name.lower())
    return value if isinstance(value, str) else None


def _positive_float_header(headers: object, name: str) -> float | None:
    raw_value = _header(headers, name)
    if raw_value is None:
        return None
    try:
        value = float(raw_value)
    except ValueError:
        return None
    return value if value > 0 else None


def _positive_int_header(headers: object, name: str) -> int | None:
    value = _non_negative_int_header(headers, name)
    return value if value is not None and value > 0 else None


def _non_negative_int_header(headers: object, name: str) -> int | None:
    raw_value = _header(headers, name)
    if raw_value is None:
        return None
    try:
        value = int(raw_value)
    except ValueError:
        return None
    return value if value >= 0 else None


def _repository_from_payload(payload: object) -> Repository:
    """Validate one GitHub response item and convert it to the domain model."""
    if not isinstance(payload, dict):
        raise GitHubClientError("GitHub repository item must be an object.")

    owner_payload = payload.get("owner")
    if not isinstance(owner_payload, dict):
        raise GitHubClientError("GitHub repository item is missing its owner.")

    topics_payload = payload.get("topics", [])
    if not isinstance(topics_payload, list) or not all(
        isinstance(topic, str) for topic in topics_payload
    ):
        raise GitHubClientError("GitHub repository topics must be a string list.")

    return Repository(
        name=_required_str(payload, "full_name"),
        description=_optional_str(payload, "description"),
        language=_optional_str(payload, "language"),
        stars=_non_negative_int(payload, "stargazers_count"),
        forks=_non_negative_int(payload, "forks_count"),
        url=_required_str(payload, "html_url"),
        topics=tuple(topics_payload),
        owner=_required_str(owner_payload, "login"),
        updated_at=_required_datetime(payload, "updated_at"),
        pushed_at=_required_datetime(payload, "pushed_at"),
    )


def _required_str(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise GitHubClientError(f"GitHub repository field {field} must be a string.")
    return value


def _required_datetime(payload: Mapping[str, object], field: str) -> datetime:
    raw_value = _required_str(payload, field)
    try:
        return datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GitHubClientError(f"GitHub repository {field} is invalid.") from exc


def _optional_str(payload: Mapping[str, object], field: str) -> str | None:
    value = payload.get(field)
    if value is None or isinstance(value, str):
        return value
    raise GitHubClientError(
        f"GitHub repository field {field} must be a string or null."
    )


def _non_negative_int(payload: Mapping[str, object], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GitHubClientError(
            f"GitHub repository field {field} must be a non-negative integer."
        )
    return value
