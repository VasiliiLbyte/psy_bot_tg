"""Tests for Telegram helper utilities."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

import utils_tg


class _DummyBot:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str]] = []

    async def send_chat_action(self, *, chat_id: int, action: str) -> Any:
        self.calls.append((chat_id, action))
        return None


@pytest.mark.asyncio
async def test_keep_typing_cancels_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    # Speed up the loop so we don't wait 4 seconds in tests.
    original_sleep = utils_tg.asyncio.sleep

    async def fast_sleep(_seconds: float) -> None:
        await original_sleep(0)

    monkeypatch.setattr(utils_tg.asyncio, "sleep", fast_sleep)

    bot = _DummyBot()
    before = {
        t
        for t in asyncio.all_tasks()
        if not t.done() and getattr(t.get_coro(), "__name__", "") == "keep_typing"
    }

    task = asyncio.create_task(utils_tg.keep_typing(bot, chat_id=123))
    await asyncio.sleep(0)  # let it run at least once
    task.cancel()
    await task  # keep_typing swallows CancelledError and exits

    after = {
        t
        for t in asyncio.all_tasks()
        if not t.done() and getattr(t.get_coro(), "__name__", "") == "keep_typing"
    }

    assert bot.calls and bot.calls[0] == (123, "typing")
    assert after == before

