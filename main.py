"""Application entrypoint."""

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from handlers import commands_router, messages_router
from utils import normalize_telegram_proxy, telegram_proxy_is_configured

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )


async def run_bot() -> None:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in environment")

    proxy_raw = os.getenv("TELEGRAM_PROXY", "").strip()
    proxy = normalize_telegram_proxy(proxy_raw) if proxy_raw else ""
    if proxy_raw and proxy != proxy_raw:
        logger.info("TELEGRAM_PROXY normalized for aiohttp (host:port → socks5://)")
    if telegram_proxy_is_configured(proxy):
        logger.info("Using TELEGRAM_PROXY for Bot API requests")
        session = AiohttpSession(proxy=proxy)
        bot = Bot(token=token, session=session)
    else:
        if proxy_raw:
            logger.warning(
                "TELEGRAM_PROXY is set but invalid or unsupported URL; "
                "using direct connection. Example: socks5://127.0.0.1:1080"
            )
        bot = Bot(token=token)

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(commands_router)
    dp.include_router(messages_router)

    await dp.start_polling(bot)


def main() -> None:
    _configure_logging()
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
