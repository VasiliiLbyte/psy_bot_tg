"""Telegram helper utilities."""

from __future__ import annotations

import asyncio
from typing import Any

from aiogram import Bot

_TYPING_INTERVAL_SECONDS = 4.0


async def keep_typing(bot: Bot, chat_id: int) -> None:
    """Send 'typing' chat action periodically until cancelled."""
    try:
        while True:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(_TYPING_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        # Expected cancellation path.
        return

