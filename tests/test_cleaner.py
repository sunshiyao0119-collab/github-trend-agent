"""Tests for repository cleaning rules."""

import unittest
from dataclasses import replace
from datetime import UTC, datetime

from github_trend_agent.cleaner import (
    MISSING_DESCRIPTION,
    UNKNOWN_LANGUAGE,
    clean_repositories,
)
from github_trend_agent.models import Repository


def _repository(**changes: object) -> Repository:
    repository = Repository(
        name="owner/project",
        description="A useful project",
        language="Python",
        stars=100,
        forks=10,
        url="https://github.com/owner/project",
        topics=("python",),
        owner="owner",
        updated_at=datetime(2026, 7, 22, tzinfo=UTC),
    )
    return replace(repository, **changes)


class CleanRepositoriesTest(unittest.TestCase):
    """Verify validation, deduplication, and normalization."""

    def test_normalizes_missing_text_and_surrounding_whitespace(self) -> None:
        result = clean_repositories(
            [_repository(name=" owner/project ", description="  ", language=None)]
        )

        self.assertEqual(len(result.repositories), 1)
        self.assertEqual(result.repositories[0].name, "owner/project")
        self.assertEqual(result.repositories[0].description, MISSING_DESCRIPTION)
        self.assertEqual(result.repositories[0].language, UNKNOWN_LANGUAGE)

    def test_removes_duplicate_urls_case_insensitively(self) -> None:
        result = clean_repositories(
            [
                _repository(),
                _repository(url="https://github.com/OWNER/PROJECT/", stars=200),
            ]
        )

        self.assertEqual(len(result.repositories), 1)
        self.assertEqual(result.repositories[0].stars, 100)
        self.assertEqual(result.duplicates_removed, 1)

    def test_rejects_invalid_identity_url_and_counts(self) -> None:
        result = clean_repositories(
            [
                _repository(name=" "),
                _repository(url="https://example.com/owner/project"),
                _repository(stars=-1),
                _repository(forks=-1),
            ]
        )

        self.assertEqual(result.repositories, ())
        self.assertEqual(result.invalid_removed, 4)

    def test_reports_all_cleaning_counts(self) -> None:
        result = clean_repositories(
            [
                _repository(),
                _repository(url="https://github.com/OWNER/PROJECT"),
                _repository(owner=""),
            ]
        )

        self.assertEqual(result.total_received, 3)
        self.assertEqual(len(result.repositories), 1)
        self.assertEqual(result.duplicates_removed, 1)
        self.assertEqual(result.invalid_removed, 1)


if __name__ == "__main__":
    unittest.main()
