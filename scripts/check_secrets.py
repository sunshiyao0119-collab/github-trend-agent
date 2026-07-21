"""Reject likely GitHub tokens in files eligible for Git tracking."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOKEN_PATTERNS = (
    re.compile(b"github" + b"_pat_"),
    re.compile(b"gh" + b"p_"),
    re.compile(rb"(?m)^\s*GITHUB_TOKEN\s*=\s*[^\s#]+"),
)


def main() -> int:
    """Scan tracked and unignored files without printing matching secrets."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        print("Secret scan failed: unable to list Git files.")
        return result.returncode

    unsafe_paths: list[str] = []
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        relative_path = raw_path.decode(errors="surrogateescape")
        file_path = PROJECT_ROOT / relative_path
        try:
            content = file_path.read_bytes()
        except OSError:
            continue
        if any(pattern.search(content) for pattern in TOKEN_PATTERNS):
            unsafe_paths.append(relative_path)

    if unsafe_paths:
        print("Secret scan failed in:")
        for path in unsafe_paths:
            print(f"- {path}")
        return 1

    print("Secret scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
