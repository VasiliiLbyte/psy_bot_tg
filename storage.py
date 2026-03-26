"""Storage facade (SQLite).

Public API is kept compatible with the previous JSON storage module.
"""

from __future__ import annotations

import json
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


async def init_clarification(user_id: int, questions: list[str]) -> None:
    """Persist clarification questions and reset index/answers."""
    payload_questions = json.dumps(list(questions), ensure_ascii=False)
    await db.update_collected_field(user_id, "clarification_questions", payload_questions)
    await db.update_collected_field(user_id, "clarification_index", "0")
    await db.update_collected_field(user_id, "clarification_answers", json.dumps([], ensure_ascii=False))


async def get_clarification_state(user_id: int) -> tuple[list[str], int, list[str]]:
    """Return (questions, index, answers) for current clarification session."""
    record = await db.get_user_record(user_id)
    collected = record.get("collected_data", {})
    if not isinstance(collected, dict):
        return ([], 0, [])

    raw_questions = str(collected.get("clarification_questions", "") or "")
    raw_index = str(collected.get("clarification_index", "") or "0")
    raw_answers = str(collected.get("clarification_answers", "") or "")

    questions: list[str] = []
    answers: list[str] = []
    idx = 0

    try:
        data = json.loads(raw_questions) if raw_questions else []
        if isinstance(data, list):
            questions = [str(x).strip() for x in data if str(x).strip()]
    except Exception:
        logger.exception("Failed to parse clarification_questions for user %d", user_id)

    try:
        idx = int(raw_index) if raw_index else 0
    except Exception:
        logger.exception("Failed to parse clarification_index for user %d", user_id)
        idx = 0

    try:
        data = json.loads(raw_answers) if raw_answers else []
        if isinstance(data, list):
            answers = [str(x).strip() for x in data]
    except Exception:
        logger.exception("Failed to parse clarification_answers for user %d", user_id)

    return (questions, max(idx, 0), answers)


async def advance_clarification(user_id: int, answer: str) -> tuple[int, int]:
    """Append answer, advance index; returns (new_index, total_questions)."""
    questions, idx, answers = await get_clarification_state(user_id)
    total = len(questions)

    answers = list(answers)
    answers.append(str(answer))
    new_idx = idx + 1

    await db.update_collected_field(
        user_id,
        "clarification_answers",
        json.dumps(answers, ensure_ascii=False),
    )
    await db.update_collected_field(user_id, "clarification_index", str(new_idx))
    return (new_idx, total)
