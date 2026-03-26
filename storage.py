"""Storage facade (SQLite).

Public API is kept compatible with the previous JSON storage module.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import db

logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).resolve().parent / "data" / "bot.db"
# Kept for backward compatibility with tests/fixtures that patch it.
LOCK_PATH = Path(__file__).resolve().parent / "data" / "bot.db.lock"

MAX_HISTORY_MESSAGES = db.MAX_HISTORY_MESSAGES


async def load_root() -> dict[str, Any]:
    """Compatibility: return {'system_prompt': str, 'users': {}} snapshot."""
    system_prompt = await db.get_system_prompt()
    # Legacy callers only rely on system_prompt; keep structure stable.
    return {"system_prompt": system_prompt, "users": {}}


async def save_root(root: dict[str, Any]) -> None:
    """Compatibility: persist system_prompt (users are managed via dedicated APIs)."""
    system_prompt = root.get("system_prompt", "")
    await db.set_system_prompt(str(system_prompt) if system_prompt is not None else "")


async def reset_user_session(user_id: int) -> None:
    await db.reset_user_session(user_id)


async def get_user_record(user_id: int) -> dict[str, Any]:
    return await db.get_user_record(user_id)


async def update_user_record(user_id: int, **fields: Any) -> None:
    """Legacy helper: supports updating collected_data shallowly if provided."""
    if "collected_data" in fields and isinstance(fields["collected_data"], dict):
        collected = fields["collected_data"]
        for k, v in collected.items():
            await set_collected_field(user_id, str(k), "" if v is None else str(v))
        return
    raise NotImplementedError("update_user_record is not supported for these fields in SQLite backend")


async def set_collected_field(user_id: int, field: str, value: str) -> None:
    await db.update_collected_field(user_id, field, value)


async def append_history(user_id: int, role: str, content: str) -> None:
    await db.append_history(user_id, role, content)
