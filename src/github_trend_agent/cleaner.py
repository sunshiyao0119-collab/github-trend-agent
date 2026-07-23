"""Repository validation and normalization rules."""

from collections.abc import Iterable
from urllib.parse import urlparse

from github_trend_agent.models import CleaningResult, CleanRepository, Repository

MISSING_DESCRIPTION = "No description provided."
UNKNOWN_LANGUAGE = "Unknown"


def clean_repositories(repositories: Iterable[Repository]) -> CleaningResult:
    """Validate, deduplicate, and normalize collected repositories."""
    cleaned: list[CleanRepository] = []
    seen_urls: set[str] = set()
    total_received = 0
    duplicates_removed = 0
    invalid_removed = 0

    for repository in repositories:
        total_received += 1
        if not _is_valid(repository):
            invalid_removed += 1
            continue

        url = repository.url.strip().rstrip("/")
        url_key = url.casefold()
        if url_key in seen_urls:
            duplicates_removed += 1
            continue
        seen_urls.add(url_key)

        cleaned.append(
            CleanRepository(
                name=repository.name.strip(),
                description=_text_or_default(
                    repository.description,
                    MISSING_DESCRIPTION,
                ),
                language=_text_or_default(repository.language, UNKNOWN_LANGUAGE),
                stars=repository.stars,
                forks=repository.forks,
                url=url,
                topics=repository.topics,
                owner=repository.owner.strip(),
                updated_at=repository.updated_at,
                pushed_at=repository.pushed_at,
            )
        )

    return CleaningResult(
        repositories=tuple(cleaned),
        total_received=total_received,
        duplicates_removed=duplicates_removed,
        invalid_removed=invalid_removed,
    )


def _is_valid(repository: Repository) -> bool:
    if not repository.name.strip() or not repository.owner.strip():
        return False
    if repository.stars < 0 or repository.forks < 0:
        return False

    parsed_url = urlparse(repository.url.strip())
    return (
        parsed_url.scheme == "https"
        and parsed_url.netloc.casefold() == "github.com"
        and len([part for part in parsed_url.path.split("/") if part]) == 2
    )


def _text_or_default(value: str | None, default: str) -> str:
    normalized = value.strip() if value else ""
    return normalized or default
