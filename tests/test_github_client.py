"""Tests for GitHub pagination, rate limits, and retry behavior."""

import io
import json
import unittest
from urllib.error import HTTPError
from urllib.request import Request

from github_trend_agent.config import Settings
from github_trend_agent.github_client import (
    GITHUB_API_VERSION,
    GitHubClient,
    GitHubClientError,
)


class FakeResponse:
    """Minimal context-managed HTTP response used by unit tests."""

    def __init__(self, payload: object, headers: dict[str, str] | None = None) -> None:
        self._body = json.dumps(payload).encode()
        self.headers = headers or {}

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class GitHubClientTest(unittest.TestCase):
    """Verify pagination, error handling, and bounded retries."""

    def setUp(self) -> None:
        self.settings = Settings.from_env({})

    def test_follows_next_link_and_returns_collection_metadata(self) -> None:
        second_url = "https://api.github.com/search/repositories?page=2"
        responses = [
            FakeResponse(
                {"items": [_repository_payload("one"), _repository_payload("two")]},
                {
                    "Link": f'<{second_url}>; rel="next"',
                    "X-RateLimit-Remaining": "9",
                },
            ),
            FakeResponse(
                {"items": [_repository_payload("three")]},
                {
                    "X-RateLimit-Limit": "10",
                    "X-RateLimit-Remaining": "8",
                    "X-RateLimit-Reset": "2000000000",
                    "X-RateLimit-Resource": "search",
                },
            ),
        ]
        captured_requests: list[Request] = []

        def fake_open(request: Request, *, timeout: float) -> FakeResponse:
            captured_requests.append(request)
            self.assertEqual(timeout, 10.0)
            return responses.pop(0)

        result = GitHubClient(self.settings, fake_open).search_repositories(
            "language:python",
            max_repositories=3,
            page_size=2,
        )

        self.assertEqual(
            [item.name for item in result.repositories],
            [
                "example/one",
                "example/two",
                "example/three",
            ],
        )
        self.assertEqual(result.pages_fetched, 2)
        self.assertEqual(result.rate_limit.limit, 10)
        self.assertEqual(result.rate_limit.remaining, 8)
        self.assertEqual(result.rate_limit.resource, "search")
        self.assertIn("per_page=2", captured_requests[0].full_url)
        self.assertEqual(captured_requests[1].full_url, second_url)

        headers = {
            key.lower(): value for key, value in captured_requests[0].header_items()
        }
        self.assertEqual(headers["x-github-api-version"], GITHUB_API_VERSION)
        self.assertNotIn("authorization", headers)

    def test_reports_non_retryable_github_api_error(self) -> None:
        settings = Settings.from_env({"GITHUB_MAX_RETRIES": "0"})

        def fake_open(request: Request, *, timeout: float) -> FakeResponse:
            del request, timeout
            raise _http_error(422, "Validation Failed")

        with self.assertRaisesRegex(GitHubClientError, "Validation Failed"):
            GitHubClient(settings, fake_open).search_repositories(
                "python",
                max_repositories=3,
                page_size=3,
            )

    def test_rejects_response_without_items(self) -> None:
        def fake_open(request: Request, *, timeout: float) -> FakeResponse:
            del request, timeout
            return FakeResponse({"total_count": 0})

        with self.assertRaisesRegex(GitHubClientError, "items list"):
            GitHubClient(self.settings, fake_open).search_repositories(
                "python",
                max_repositories=3,
                page_size=3,
            )

    def test_retries_transient_server_error_with_exponential_delay(self) -> None:
        attempts = 0
        delays: list[float] = []

        def fake_open(request: Request, *, timeout: float) -> FakeResponse:
            nonlocal attempts
            del request, timeout
            attempts += 1
            if attempts == 1:
                raise _http_error(503, "Service Unavailable")
            return FakeResponse({"items": [_repository_payload("recovered")]})

        result = GitHubClient(
            self.settings,
            fake_open,
            sleeper=delays.append,
        ).search_repositories("python", max_repositories=1, page_size=1)

        self.assertEqual(result.repositories[0].name, "example/recovered")
        self.assertEqual(delays, [1.0])

    def test_respects_retry_after_for_rate_limit(self) -> None:
        attempts = 0
        delays: list[float] = []

        def fake_open(request: Request, *, timeout: float) -> FakeResponse:
            nonlocal attempts
            del request, timeout
            attempts += 1
            if attempts == 1:
                raise _http_error(
                    429,
                    "Too Many Requests",
                    {"Retry-After": "7"},
                )
            return FakeResponse({"items": [_repository_payload("recovered")]})

        GitHubClient(
            self.settings,
            fake_open,
            sleeper=delays.append,
        ).search_repositories("python", max_repositories=1, page_size=1)

        self.assertEqual(delays, [7.0])

    def test_waits_until_primary_rate_limit_reset(self) -> None:
        attempts = 0
        delays: list[float] = []

        def fake_open(request: Request, *, timeout: float) -> FakeResponse:
            nonlocal attempts
            del request, timeout
            attempts += 1
            if attempts == 1:
                raise _http_error(
                    403,
                    "API rate limit exceeded",
                    {
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": "110",
                    },
                )
            return FakeResponse({"items": [_repository_payload("recovered")]})

        GitHubClient(
            self.settings,
            fake_open,
            sleeper=delays.append,
            clock=lambda: 100.0,
        ).search_repositories("python", max_repositories=1, page_size=1)

        self.assertEqual(delays, [11.0])


def _http_error(
    status: int,
    message: str,
    headers: dict[str, str] | None = None,
) -> HTTPError:
    return HTTPError(
        "https://api.github.com/search/repositories",
        status,
        message,
        headers or {},
        io.BytesIO(json.dumps({"message": message}).encode()),
    )


def _repository_payload(name: str) -> dict[str, object]:
    return {
        "full_name": f"example/{name}",
        "description": "Example repository",
        "language": "Python",
        "stargazers_count": 1200,
        "forks_count": 100,
        "html_url": f"https://github.com/example/{name}",
        "topics": ["github", "trends"],
        "owner": {"login": "example"},
        "updated_at": "2026-07-20T08:00:00Z",
    }


if __name__ == "__main__":
    unittest.main()
