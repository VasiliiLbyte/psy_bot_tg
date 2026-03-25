"""Application entrypoint."""

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv

from handlers import commands_router, messages_router

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

    proxy = os.getenv("TELEGRAM_PROXY", "").strip()
    if proxy:
        logger.info("Using TELEGRAM_PROXY for Bot API requests")
        session = AiohttpSession(proxy=proxy)
        bot = Bot(token=token, session=session)
    else:
        bot = Bot(token=token)

    dp = Dispatcher()
    dp.include_router(commands_router)
    dp.include_router(messages_router)

    await dp.start_polling(bot)


def main() -> None:
    _configure_logging()
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
