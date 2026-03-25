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
from pathlib import Path

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv

# Allow ``from utils`` when cwd is project root (same as main.py imports).
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from utils import normalize_telegram_proxy, telegram_proxy_is_configured


async def _run() -> int:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("TELEGRAM_BOT_TOKEN is not set in environment (.env).", file=sys.stderr)
        return 1

    proxy_raw = os.getenv("TELEGRAM_PROXY", "").strip()
    proxy = normalize_telegram_proxy(proxy_raw) if proxy_raw else ""
    if proxy_raw and proxy != proxy_raw:
        print(
            "Note: TELEGRAM_PROXY was normalized (e.g. host:port → socks5://…). "
            f"Effective: {proxy!r}",
        )

    if proxy_raw:
        if not telegram_proxy_is_configured(proxy):
            print(
                "TELEGRAM_PROXY is set but not a usable URL after normalization.\n"
                "Use e.g. socks5://127.0.0.1:1080 or http://127.0.0.1:7890, "
                "or bare 127.0.0.1:1080 (socks5 will be assumed).",
                file=sys.stderr,
            )
            return 1
        print("TELEGRAM_PROXY is set (same logic as main.py).")
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
