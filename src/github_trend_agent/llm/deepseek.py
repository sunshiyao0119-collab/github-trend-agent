"""DeepSeek adapter for the provider-neutral LLM analysis interface."""

import json
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from github_trend_agent.llm.analysis import LLMProviderError


class DeepSeekProvider:
    """Generate validated JSON candidates through DeepSeek Chat Completions."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self._api_key = api_key
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._opener = opener

    def generate_json(self, *, system_prompt: str, user_prompt: str) -> str:
        """Request one non-streaming JSON response without automatic retries."""
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "max_tokens": 1_200,
            "stream": False,
        }
        request = Request(
            self._url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with self._opener(request, timeout=self._timeout_seconds) as response:
                raw_response = response.read()
        except HTTPError as exc:
            raise LLMProviderError(_safe_http_error(exc.code)) from exc
        except (URLError, TimeoutError) as exc:
            raise LLMProviderError("DeepSeek connection failed.") from exc

        try:
            response_payload = json.loads(raw_response)
            content = response_payload["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError("DeepSeek returned an invalid response.") from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("DeepSeek returned empty content.")
        return content


def _safe_http_error(status: int) -> str:
    messages = {
        401: "DeepSeek authentication failed; replace the API key.",
        402: "DeepSeek account balance is insufficient.",
        429: "DeepSeek rate limit was reached.",
    }
    if status >= 500:
        return "DeepSeek service is temporarily unavailable."
    return messages.get(status, f"DeepSeek request failed with HTTP {status}.")
