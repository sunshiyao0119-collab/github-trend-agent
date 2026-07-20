"""Tests for the GitHub repository collection client."""

import io
import json
import unittest
from urllib.error import HTTPError

from github_trend_agent.config import Settings
from github_trend_agent.github_client import (
    GITHUB_API_VERSION,
    GitHubClient,
    GitHubClientError,
)


class FakeResponse:
    """Minimal context-managed HTTP response used by unit tests."""

    def __init__(self, payload: object) -> None:
        self._body = json.dumps(payload).encode()

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class GitHubClientTest(unittest.TestCase):
    """Verify successful, failed, and invalid GitHub responses."""

    def setUp(self) -> None:
        self.settings = Settings.from_env({})

    def test_searches_and_normalizes_repositories(self) -> None:
        captured_request = None

        def fake_open(request: object, *, timeout: float) -> FakeResponse:
            nonlocal captured_request
            captured_request = request
            self.assertEqual(timeout, 10.0)
            return FakeResponse({"items": [_repository_payload()]})

        repositories = GitHubClient(self.settings, fake_open).search_repositories(
            "language:python",
            3,
        )

        self.assertEqual(len(repositories), 1)
        self.assertEqual(repositories[0].name, "example/trend-agent")
        self.assertEqual(repositories[0].stars, 1200)
        self.assertIsNotNone(captured_request)
        headers = {key.lower(): value for key, value in captured_request.header_items()}
        self.assertEqual(headers["x-github-api-version"], GITHUB_API_VERSION)
        self.assertNotIn("authorization", headers)

    def test_reports_github_api_error(self) -> None:
        def fake_open(request: object, *, timeout: float) -> FakeResponse:
            del timeout
            raise HTTPError(
                request.full_url,
                403,
                "Forbidden",
                {},
                io.BytesIO(b'{"message":"API rate limit exceeded"}'),
            )

        with self.assertRaisesRegex(GitHubClientError, "rate limit exceeded"):
            GitHubClient(self.settings, fake_open).search_repositories("python", 3)

    def test_rejects_response_without_items(self) -> None:
        def fake_open(request: object, *, timeout: float) -> FakeResponse:
            del request, timeout
            return FakeResponse({"total_count": 0})

        with self.assertRaisesRegex(GitHubClientError, "items list"):
            GitHubClient(self.settings, fake_open).search_repositories("python", 3)


def _repository_payload() -> dict[str, object]:
    return {
        "full_name": "example/trend-agent",
        "description": "Example repository",
        "language": "Python",
        "stargazers_count": 1200,
        "forks_count": 100,
        "html_url": "https://github.com/example/trend-agent",
        "topics": ["github", "trends"],
        "owner": {"login": "example"},
        "updated_at": "2026-07-20T08:00:00Z",
    }


if __name__ == "__main__":
    unittest.main()
