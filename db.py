"""SQLite storage backend (aiosqlite).

Provides atomic async operations for user records, history and settings.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import aiosqlite

MAX_HISTORY_MESSAGES = 20

_db_path: Path | None = None
_CLARIFICATION_COLUMNS: tuple[str, ...] = (
    "clarification_questions",
    "clarification_index",
    "clarification_answers",
)


def _require_db_path() -> Path:
    if _db_path is None:
        raise RuntimeError("DB is not initialized. Call await init_db(path) first.")
    return _db_path


async def init_db(path: str) -> None:
    """Initialize SQLite database (create tables, pragmas) and set global path."""
    global _db_path
    p = Path(path)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent / p
    p.parent.mkdir(parents=True, exist_ok=True)
    _db_path = p

    async with aiosqlite.connect(p.as_posix()) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("PRAGMA journal_mode = WAL;")
        await db.execute("PRAGMA synchronous = NORMAL;")

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                symptoms TEXT,
                life_context TEXT
            );
            """
        )
        # Lightweight migration: add clarification-related columns if DB already exists.
        # We keep them TEXT so storage can serialize JSON consistently.
        for col in _CLARIFICATION_COLUMNS:
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT;")
            except Exception:
                # Column probably already exists; ignore.
                pass
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        await db.commit()


async def get_system_prompt() -> str:
    path = _require_db_path()
    async with aiosqlite.connect(path.as_posix()) as db:
        async with db.execute(
            "SELECT value FROM settings WHERE key = ?",
            ("system_prompt",),
        ) as cur:
            row = await cur.fetchone()
            return str(row[0]) if row and row[0] is not None else ""


async def set_system_prompt(text: str) -> None:
    path = _require_db_path()
    async with aiosqlite.connect(path.as_posix()) as db:
        await db.execute("BEGIN IMMEDIATE;")
        await db.execute(
            """
            INSERT INTO settings(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            ("system_prompt", text),
        )
        await db.commit()


async def _ensure_user_row(db: aiosqlite.Connection, user_id: int) -> None:
    await db.execute(
        """
        INSERT INTO users(user_id, symptoms, life_context, clarification_questions, clarification_index, clarification_answers)
        VALUES(?, '', '', '', '0', '')
        ON CONFLICT(user_id) DO NOTHING
        """,
        (user_id,),
    )


async def get_user_record(user_id: int) -> dict[str, Any]:
    """Return record compatible with legacy JSON storage structure."""
    path = _require_db_path()
    async with aiosqlite.connect(path.as_posix()) as db:
        await _ensure_user_row(db, user_id)

        async with db.execute(
            "SELECT symptoms, life_context, clarification_questions, clarification_index, clarification_answers FROM users WHERE user_id = ?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
            symptoms = str(row[0] or "") if row else ""
            life_context = str(row[1] or "") if row else ""
            clarification_questions = str(row[2] or "") if row else ""
            clarification_index = str(row[3] or "0") if row else "0"
            clarification_answers = str(row[4] or "") if row else ""

        async with db.execute(
            """
            SELECT role, content
            FROM history
            WHERE user_id = ?
            ORDER BY id ASC
            """,
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()

        return {
            "collected_data": {
                "symptoms": symptoms,
                "life_context": life_context,
                "clarification_questions": clarification_questions,
                "clarification_index": clarification_index,
                "clarification_answers": clarification_answers,
            },
            "history": [{"role": str(r[0]), "content": str(r[1])} for r in rows],
        }


async def update_collected_field(user_id: int, field: str, value: str) -> None:
    if field not in ("symptoms", "life_context", *_CLARIFICATION_COLUMNS):
        raise KeyError(f"Unknown collected field: {field}")
    path = _require_db_path()
    async with aiosqlite.connect(path.as_posix()) as db:
        await db.execute("BEGIN IMMEDIATE;")
        await _ensure_user_row(db, user_id)
        await db.execute(
            f"UPDATE users SET {field} = ? WHERE user_id = ?",
            (value, user_id),
        )
        await db.commit()


async def append_history(user_id: int, role: str, content: str) -> None:
    path = _require_db_path()
    async with aiosqlite.connect(path.as_posix()) as db:
        await db.execute("BEGIN IMMEDIATE;")
        await _ensure_user_row(db, user_id)

        await db.execute(
            "INSERT INTO history(user_id, role, content) VALUES(?, ?, ?)",
            (user_id, role, content),
        )

        await db.execute(
            """
            DELETE FROM history
            WHERE id IN (
                SELECT id
                FROM history
                WHERE user_id = ?
                ORDER BY id ASC
                LIMIT (
                    SELECT MAX(COUNT(*) - ?, 0)
                    FROM history
                    WHERE user_id = ?
                )
            )
            """,
            (user_id, MAX_HISTORY_MESSAGES, user_id),
        )

        await db.commit()


async def reset_user_session(user_id: int) -> None:
    path = _require_db_path()
    async with aiosqlite.connect(path.as_posix()) as db:
        await db.execute("BEGIN IMMEDIATE;")
        await _ensure_user_row(db, user_id)
        await db.execute(
            """
            UPDATE users
            SET symptoms = '',
                life_context = '',
                clarification_questions = '',
                clarification_index = '0',
                clarification_answers = ''
            WHERE user_id = ?
            """,
            (user_id,),
        )
        await db.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
        await db.commit()

