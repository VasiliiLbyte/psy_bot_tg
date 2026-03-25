"""HTTP client for OpenRouter API (stage 3).

Provides an async wrapper around OpenRouter chat/completions endpoint
with retry, configurable timeouts, and structured error handling.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

# Optional transport for tests / custom networking (e.g. httpx.MockTransport).
AsyncTransport = httpx.AsyncBaseTransport

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
CHAT_COMPLETIONS_PATH = "/chat/completions"

DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2.0
INITIAL_RETRY_DELAY = 1.0

RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class OpenRouterError(Exception):
    """Base exception for OpenRouter client errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class OpenRouterClient:
    """Async client for OpenRouter chat completions."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = OPENROUTER_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        transport: AsyncTransport | None = None,
    ) -> None:
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        if not self._api_key:
            raise OpenRouterError("OPENROUTER_API_KEY is not set")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            client_kw: dict[str, Any] = {
                "base_url": self._base_url,
                "headers": {
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/VasiliiLbyte/psy_bot_tg",
                },
                "timeout": httpx.Timeout(self._timeout),
            }
            if self._transport is not None:
                client_kw["transport"] = self._transport
            self._client = httpx.AsyncClient(**client_kw)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        *,
        temperature: float = 0.4,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Send a chat completion request and return the parsed JSON response.

        Retries on transient errors (429 / 5xx) with exponential backoff.
        """
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        client = await self._get_client()
        last_exc: Exception | None = None
        delay = INITIAL_RETRY_DELAY

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await client.post(CHAT_COMPLETIONS_PATH, json=payload)
                if response.status_code == 200:
                    return response.json()

                if response.status_code in RETRYABLE_STATUS_CODES and attempt < self._max_retries:
                    logger.warning(
                        "OpenRouter %d on attempt %d/%d, retrying in %.1fs",
                        response.status_code, attempt, self._max_retries, delay,
                    )
                    import asyncio
                    await asyncio.sleep(delay)
                    delay *= RETRY_BACKOFF_FACTOR
                    continue

                body = response.text[:500]
                raise OpenRouterError(
                    f"OpenRouter returned {response.status_code}: {body}",
                    status_code=response.status_code,
                )

            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    logger.warning(
                        "OpenRouter timeout on attempt %d/%d, retrying in %.1fs",
                        attempt, self._max_retries, delay,
                    )
                    import asyncio
                    await asyncio.sleep(delay)
                    delay *= RETRY_BACKOFF_FACTOR
                    continue

            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    logger.warning(
                        "OpenRouter network error on attempt %d/%d: %s",
                        attempt, self._max_retries, exc,
                    )
                    import asyncio
                    await asyncio.sleep(delay)
                    delay *= RETRY_BACKOFF_FACTOR
                    continue

        raise OpenRouterError(
            f"All {self._max_retries} attempts failed: {last_exc}"
        )

    def extract_content(self, response: dict[str, Any]) -> str:
        """Pull the assistant message text from a chat completion response."""
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise OpenRouterError(f"Unexpected response structure: {exc}") from exc
