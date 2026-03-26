"""Handlers package."""

from handlers.commands import router as commands_router
from handlers.callbacks import router as callbacks_router
from handlers.messages import router as messages_router

__all__ = ["commands_router", "callbacks_router", "messages_router"]
