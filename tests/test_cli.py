"""Tests for the command-line entry point."""

import unittest

from github_trend_agent.cli import build_startup_message
from github_trend_agent.config import Settings


class BuildStartupMessageTest(unittest.TestCase):
    """Verify the initial user-visible application output."""

    def test_returns_application_ready_message(self) -> None:
        settings = Settings.from_env({})

        self.assertEqual(
            build_startup_message(settings),
            "GitHub Trend Agent is ready (unauthenticated mode).",
        )


if __name__ == "__main__":
    unittest.main()
