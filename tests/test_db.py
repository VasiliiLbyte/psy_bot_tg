"""Tests for SQLite backend concurrency behavior."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

import db


@pytest.mark.asyncio
async def test_concurrent_writes_two_users(tmp_path: Path) -> None:
    db_file = tmp_path / "bot.db"
    await db.init_db(str(db_file))

    async def user_flow(uid: int) -> None:
        await db.reset_user_session(uid)
        await db.update_collected_field(uid, "symptoms", f"s{uid}")
        await db.update_collected_field(uid, "life_context", f"c{uid}")
        for i in range(db.MAX_HISTORY_MESSAGES + 5):
            await db.append_history(uid, "user", f"u{uid}-{i}")

    await asyncio.gather(user_flow(1), user_flow(2))

    rec1 = await db.get_user_record(1)
    rec2 = await db.get_user_record(2)

    assert rec1["collected_data"]["symptoms"] == "s1"
    assert rec1["collected_data"]["life_context"] == "c1"
    assert rec2["collected_data"]["symptoms"] == "s2"
    assert rec2["collected_data"]["life_context"] == "c2"

    assert len(rec1["history"]) == db.MAX_HISTORY_MESSAGES
    assert len(rec2["history"]) == db.MAX_HISTORY_MESSAGES
    assert rec1["history"][0]["content"] == "u1-5"
    assert rec2["history"][0]["content"] == "u2-5"

