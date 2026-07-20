"""Tests for application configuration."""

import unittest

from github_trend_agent.config import ConfigurationError, Settings


class SettingsTest(unittest.TestCase):
    """Verify configuration parsing without reading the user's environment."""

    def test_uses_safe_defaults(self) -> None:
        settings = Settings.from_env({})

        self.assertEqual(settings.github_api_url, "https://api.github.com")
        self.assertEqual(
            settings.github_search_query,
            "language:python stars:>1000",
        )
        self.assertEqual(settings.request_timeout_seconds, 10.0)
        self.assertEqual(settings.top_n, 10)
        self.assertFalse(settings.github_auth_enabled)

    def test_parses_supplied_values(self) -> None:
        settings = Settings.from_env(
            {
                "GITHUB_TOKEN": "test-secret",
                "GITHUB_REQUEST_TIMEOUT_SECONDS": "2.5",
                "GITHUB_TOP_N": "5",
            }
        )

        self.assertTrue(settings.github_auth_enabled)
        self.assertEqual(settings.request_timeout_seconds, 2.5)
        self.assertEqual(settings.top_n, 5)
        self.assertNotIn("test-secret", repr(settings))

    def test_rejects_invalid_top_n(self) -> None:
        for invalid_value in ("0", "101"):
            with self.subTest(invalid_value=invalid_value):
                with self.assertRaisesRegex(ConfigurationError, "GITHUB_TOP_N"):
                    Settings.from_env({"GITHUB_TOP_N": invalid_value})

    def test_requires_token_only_when_requested(self) -> None:
        settings = Settings.from_env({})

        with self.assertRaisesRegex(ConfigurationError, "GITHUB_TOKEN"):
            settings.require_github_token()


if __name__ == "__main__":
    unittest.main()
