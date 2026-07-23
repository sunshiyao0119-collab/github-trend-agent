"""Tests for the DeepSeek HTTP adapter without real API calls."""

import io
import json
import unittest
from urllib.error import HTTPError
from urllib.request import Request

from github_trend_agent.llm.analysis import LLMProviderError
from github_trend_agent.llm.deepseek import DeepSeekProvider


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class DeepSeekProviderTest(unittest.TestCase):
    def test_sends_bounded_json_request_and_returns_content(self) -> None:
        captured: list[tuple[Request, float]] = []

        def fake_open(request: Request, *, timeout: float) -> FakeResponse:
            captured.append((request, timeout))
            return FakeResponse(
                {"choices": [{"message": {"content": '{"summary":"ok"}'}}]}
            )

        provider = DeepSeekProvider(
            api_key="test-api-key",
            base_url="https://api.deepseek.com/",
            model="deepseek-v4-flash",
            timeout_seconds=12.5,
            opener=fake_open,
        )

        content = provider.generate_json(
            system_prompt="Return JSON.",
            user_prompt="Analyze this project.",
        )

        request, timeout = captured[0]
        payload = json.loads(request.data or b"")
        self.assertEqual(content, '{"summary":"ok"}')
        self.assertEqual(request.full_url, "https://api.deepseek.com/chat/completions")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-api-key")
        self.assertEqual(timeout, 12.5)
        self.assertEqual(payload["model"], "deepseek-v4-flash")
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertEqual(payload["max_tokens"], 1_200)
        self.assertFalse(payload["stream"])

    def test_maps_insufficient_balance_without_echoing_response(self) -> None:
        raw_error = "sensitive-provider-response"

        def fake_open(request: Request, *, timeout: float) -> FakeResponse:
            del request, timeout
            raise HTTPError(
                "https://api.deepseek.com/chat/completions",
                402,
                "Payment Required",
                {},
                io.BytesIO(raw_error.encode()),
            )

        provider = DeepSeekProvider(
            api_key="test-api-key",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            timeout_seconds=30,
            opener=fake_open,
        )

        with self.assertRaisesRegex(
            LLMProviderError, "balance is insufficient"
        ) as raised:
            provider.generate_json(system_prompt="JSON", user_prompt="Analyze")

        self.assertNotIn(raw_error, str(raised.exception))

    def test_rejects_malformed_success_response(self) -> None:
        provider = DeepSeekProvider(
            api_key="test-api-key",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            timeout_seconds=30,
            opener=lambda request, timeout: FakeResponse({"choices": []}),
        )

        with self.assertRaisesRegex(LLMProviderError, "invalid response"):
            provider.generate_json(system_prompt="JSON", user_prompt="Analyze")


if __name__ == "__main__":
    unittest.main()
