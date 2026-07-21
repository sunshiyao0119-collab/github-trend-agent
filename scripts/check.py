"""Run the project's local quality gate with one cross-platform command."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """Run formatting, lint, and test checks; stop at the first failure."""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    checks = (
        (
            "format",
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--check",
                "--no-cache",
                ".",
            ],
        ),
        (
            "lint",
            [sys.executable, "-m", "ruff", "check", "--no-cache", "."],
        ),
        (
            "secrets",
            [sys.executable, "scripts/check_secrets.py"],
        ),
        (
            "tests",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-v",
            ],
        ),
    )

    for name, command in checks:
        print(f"== {name} ==", flush=True)
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            check=False,
        )
        if result.returncode != 0:
            return result.returncode

    print("All quality checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
