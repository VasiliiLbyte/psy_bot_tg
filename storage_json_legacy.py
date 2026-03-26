"""JSON storage with file locking (data.json).

Legacy implementation kept for reference and rollback purposes.
"""

from __future__ import annotations

import asyncio
import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

from filelock import FileLock

logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).resolve().parent / "data" / "data.json"
LOCK_PATH = Path(__file__).resolve().parent / "data" / "data.json.lock"

MAX_HISTORY_MESSAGES = 20

_DEFAULT_ROOT: dict[str, Any] = {
    "system_prompt": "",
    "users": {},
}


def _default_user_record() -> dict[str, Any]:
    return {
        "collected_data": {
            "symptoms": "",
            "life_context": "",
        },
        "history": [],
    }


def _trim_history(history: list[dict[str, Any]], max_items: int = MAX_HISTORY_MESSAGES) -> list[dict[str, Any]]:
    if len(history) <= max_items:
        return history
    return history[-max_items:]


def _read_file_locked() -> dict[str, Any]:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_PATH.is_file():
        root = deepcopy(_DEFAULT_ROOT)
        tmp = DATA_PATH.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(root, fh, ensure_ascii=False, indent=2)
        tmp.replace(DATA_PATH)
        return root

    with FileLock(LOCK_PATH):
        with open(DATA_PATH, encoding="utf-8") as fh:
            return json.load(fh)


def _write_file_locked(root: dict[str, Any]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(LOCK_PATH):
        tmp = DATA_PATH.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(root, fh, ensure_ascii=False, indent=2)
        tmp.replace(DATA_PATH)


async def load_root() -> dict[str, Any]:
    """Load full data.json (with global system_prompt and users)."""
    try:
        return await asyncio.to_thread(_read_file_locked)
    except (OSError, json.JSONDecodeError):
        logger.exception("Failed to load %s", DATA_PATH)
        raise


async def save_root(root: dict[str, Any]) -> None:
    """Persist full document."""
    try:
        await asyncio.to_thread(_write_file_locked, root)
    except OSError:
        logger.exception("Failed to save %s", DATA_PATH)
        raise


def _user_key(user_id: int) -> str:
    return str(user_id)


async def reset_user_session(user_id: int) -> None:
    """Start a new survey: empty collected_data and history for this user."""
    root = await load_root()
    users: dict[str, Any] = root.setdefault("users", {})
    users[_user_key(user_id)] = _default_user_record()
    await save_root(root)


async def get_user_record(user_id: int) -> dict[str, Any]:
    root = await load_root()
    users: dict[str, Any] = root.setdefault("users", {})
    key = _user_key(user_id)
    if key not in users:
        users[key] = _default_user_record()
        await save_root(root)
    return deepcopy(users[key])


async def update_user_record(user_id: int, **fields: Any) -> None:
    """Shallow-merge top-level fields on the user object (e.g. collected_data)."""
    root = await load_root()
    users: dict[str, Any] = root.setdefault("users", {})
    key = _user_key(user_id)
    record = users.setdefault(key, _default_user_record())
    for name, value in fields.items():
        record[name] = value
    await save_root(root)


async def set_collected_field(user_id: int, field: str, value: str) -> None:
    root = await load_root()
    users: dict[str, Any] = root.setdefault("users", {})
    key = _user_key(user_id)
    record = users.setdefault(key, _default_user_record())
    collected: dict[str, str] = record.setdefault("collected_data", {})
    collected[field] = value
    await save_root(root)


async def append_history(user_id: int, role: str, content: str) -> None:
    """Append one message; trim to last MAX_HISTORY_MESSAGES."""
    root = await load_root()
    users: dict[str, Any] = root.setdefault("users", {})
    key = _user_key(user_id)
    record = users.setdefault(key, _default_user_record())
    hist: list[dict[str, Any]] = record.setdefault("history", [])
    hist.append({"role": role, "content": content})
    record["history"] = _trim_history(hist)
    await save_root(root)

