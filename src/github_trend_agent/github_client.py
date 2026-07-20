"""Small GitHub REST API client for repository discovery."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from github_trend_agent.config import Settings
from github_trend_agent.models import Repository

GITHUB_API_VERSION = "2026-03-10"


class GitHubClientError(RuntimeError):
    """Raised when GitHub data cannot be requested or validated."""


class GitHubClient:
    """Collect and normalize repository data from the GitHub REST API."""

    def __init__(
        self,
        settings: Settings,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self._settings = settings
        self._opener = opener

    def search_repositories(self, query: str, limit: int) -> list[Repository]:
        """Return repositories matching a GitHub search query."""
        if not query.strip():
            raise ValueError("GitHub search query cannot be empty.")
        if not 1 <= limit <= 100:
            raise ValueError("Repository search limit must be between 1 and 100.")

        parameters = urlencode(
            {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": limit,
            }
        )
        url = f"{self._settings.github_api_url}/search/repositories?{parameters}"
        request = Request(url, headers=self._headers())

        try:
            with self._opener(
                request,
                timeout=self._settings.request_timeout_seconds,
            ) as response:
                raw_payload = response.read()
        except HTTPError as exc:
            message = _read_github_error_message(exc)
            raise GitHubClientError(
                f"GitHub API returned HTTP {exc.code}: {message}"
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise GitHubClientError("GitHub API request failed.") from exc

        try:
            payload = json.loads(raw_payload)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise GitHubClientError("GitHub API returned invalid JSON.") from exc

        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise GitHubClientError("GitHub API response is missing an items list.")

        return [_repository_from_payload(item) for item in payload["items"]]

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "github-trend-agent/0.1",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }
        if self._settings.github_token is not None:
            headers["Authorization"] = f"Bearer {self._settings.github_token}"
        return headers


def _read_github_error_message(error: HTTPError) -> str:
    """Extract a safe error message without including request headers."""
    try:
        payload = json.loads(error.read())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return error.reason

    if isinstance(payload, dict) and isinstance(payload.get("message"), str):
        return payload["message"]
    return error.reason


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

    updated_at_raw = _required_str(payload, "updated_at")
    try:
        updated_at = datetime.fromisoformat(updated_at_raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GitHubClientError("GitHub repository updated_at is invalid.") from exc

    return Repository(
        name=_required_str(payload, "full_name"),
        description=_optional_str(payload, "description"),
        language=_optional_str(payload, "language"),
        stars=_non_negative_int(payload, "stargazers_count"),
        forks=_non_negative_int(payload, "forks_count"),
        url=_required_str(payload, "html_url"),
        topics=tuple(topics_payload),
        owner=_required_str(owner_payload, "login"),
        updated_at=updated_at,
    )


def _required_str(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise GitHubClientError(f"GitHub repository field {field} must be a string.")
    return value


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
