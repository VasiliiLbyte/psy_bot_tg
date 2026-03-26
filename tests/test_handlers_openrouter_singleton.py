"""Tests for aiogram DI passing singleton OpenRouterClient into handlers."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from handlers import messages as messages_handlers
from openrouter_client import OpenRouterClient


@dataclass
class _DummySafetyResult:
    is_critical: bool = False


class _DummyMessage:
    def __init__(self, user_id: int, text: str, *, chat_id: int = 1, bot: Any | None = None) -> None:
        self.from_user = SimpleNamespace(id=user_id)
        self.chat = SimpleNamespace(id=chat_id)
        self.bot = bot if bot is not None else SimpleNamespace(send_chat_action=_async_noop_kw)
        self.text = text
        self.answers: list[str] = []

    async def answer(self, text: str, **_kwargs: Any) -> None:
        self.answers.append(text)


class _DummyState:
    def __init__(self) -> None:
        self.states: list[Any] = []

    async def set_state(self, state: Any) -> None:
        self.states.append(state)


@pytest.mark.asyncio
async def test_openrouter_client_is_singleton_in_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    # Avoid touching real storage / safety behavior.
    monkeypatch.setattr(
        messages_handlers,
        "check_user_message",
        lambda _text: _DummySafetyResult(is_critical=False),
    )
    monkeypatch.setattr(messages_handlers.storage, "set_collected_field", lambda *_a, **_k: _async_noop())
    monkeypatch.setattr(messages_handlers.storage, "append_history", lambda *_a, **_k: _async_noop())
    monkeypatch.setattr(messages_handlers, "RECOMMENDATIONS_FOOTER_DISCLAIMER", "")

    received_clients: list[OpenRouterClient] = []

    async def _fake_run_evaluation(openrouter_client: OpenRouterClient, user_id: int) -> str:
        received_clients.append(openrouter_client)
        return f"ok:{user_id}"

    monkeypatch.setattr(messages_handlers, "_run_evaluation", _fake_run_evaluation)

    client = OpenRouterClient(api_key="test-key", base_url="http://openrouter.test")

    msg1 = _DummyMessage(user_id=1, text="context 1")
    msg2 = _DummyMessage(user_id=1, text="context 2")
    state1 = _DummyState()
    state2 = _DummyState()

    await messages_handlers.on_context(msg1, state1, openrouter_client=client)
    await messages_handlers.on_context(msg2, state2, openrouter_client=client)

    assert len(received_clients) == 2
    assert received_clients[0] is received_clients[1] is client


async def _async_noop() -> None:
    return None


async def _async_noop_kw(*_a: Any, **_k: Any) -> None:
    return None

