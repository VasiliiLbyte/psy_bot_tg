#!/usr/bin/env python3
"""One-shot check: Bot API is reachable (uses TELEGRAM_PROXY like main.py).

Run from project root with venv activated:
  python scripts/telegram_connect_check.py

Exit code: 0 if getMe succeeds, 1 otherwise.
"""

from __future__ import annotations

import asyncio
import os
import sys

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv

_VALID_PROXY_PREFIXES = ("http://", "https://", "socks5://", "socks4://")


def _proxy_url_ok(url: str) -> bool:
    low = url.lower().strip()
    return any(low.startswith(p) for p in _VALID_PROXY_PREFIXES)


async def _run() -> int:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("TELEGRAM_BOT_TOKEN is not set in environment (.env).", file=sys.stderr)
        return 1

    proxy = os.getenv("TELEGRAM_PROXY", "").strip()
    if proxy:
        if not _proxy_url_ok(proxy):
            print(
                "TELEGRAM_PROXY must be a full URL, e.g. socks5://127.0.0.1:1080 "
                "or http://127.0.0.1:7890 (not just host:port).",
                file=sys.stderr,
            )
            return 1
        print("TELEGRAM_PROXY is set (same as main.py will use).")
        session = AiohttpSession(proxy=proxy)
        bot = Bot(token=token, session=session)
    else:
        print("TELEGRAM_PROXY is empty — direct connection to api.telegram.org.")
        bot = Bot(token=token)

    try:
        me = await bot.get_me()
        print(f"OK — Telegram Bot API: @{me.username} (id={me.id}, name={me.first_name!r})")
        return 0
    except Exception as exc:
        print(f"FAIL — could not reach Telegram API: {exc}", file=sys.stderr)
        return 1
    finally:
        await bot.session.close()


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
