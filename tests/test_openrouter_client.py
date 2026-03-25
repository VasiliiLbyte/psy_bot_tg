"""Integration-style tests for OpenRouter client with mocked HTTP."""

from __future__ import annotations

import httpx
import pytest

import openrouter_client as orc
from openrouter_client import OpenRouterClient, OpenRouterError


def _ok_completion_json(content: str) -> dict:
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": content},
            }
        ],
    }


@pytest.mark.asyncio
async def test_chat_completion_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orc, "INITIAL_RETRY_DELAY", 0.0)

    def sync_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_ok_completion_json('{"a":1}'))

    transport = httpx.MockTransport(sync_handler)
    client = OpenRouterClient(
        api_key="test-key",
        base_url="http://openrouter.test",
        transport=transport,
    )
    try:
        data = await client.chat_completion([{"role": "user", "content": "hi"}], "m")
        assert data["choices"][0]["message"]["content"] == '{"a":1}'
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_chat_completion_retries_on_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orc, "INITIAL_RETRY_DELAY", 0.0)

    calls: list[int] = []

    def sync_handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=_ok_completion_json("ok"))

    transport = httpx.MockTransport(sync_handler)
    client = OpenRouterClient(
        api_key="test-key",
        base_url="http://openrouter.test",
        max_retries=3,
        transport=transport,
    )
    try:
        data = await client.chat_completion([], "m")
        assert client.extract_content(data) == "ok"
        assert len(calls) == 2
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_chat_completion_fails_after_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orc, "INITIAL_RETRY_DELAY", 0.0)

    def sync_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    transport = httpx.MockTransport(sync_handler)
    client = OpenRouterClient(
        api_key="test-key",
        base_url="http://openrouter.test",
        max_retries=2,
        transport=transport,
    )
    try:
        with pytest.raises(OpenRouterError) as excinfo:
            await client.chat_completion([], "m")
        assert excinfo.value.status_code == 503
    finally:
        await client.close()


def test_extract_content_and_bad_structure() -> None:
    client = OpenRouterClient(api_key="k", base_url="http://localhost")
    assert client.extract_content(_ok_completion_json("x")) == "x"
    with pytest.raises(OpenRouterError):
        client.extract_content({"choices": []})
