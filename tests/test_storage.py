"""Tests for storage facade (SQLite-backed)."""

from __future__ import annotations

from pathlib import Path

import pytest

import storage


@pytest.mark.asyncio
async def test_load_root_creates_default(isolated_storage: Path) -> None:
    root = await storage.load_root()
    assert root == {"system_prompt": "", "users": {}}
    assert isolated_storage.is_file()


@pytest.mark.asyncio
async def test_get_user_record_creates_and_roundtrip(isolated_storage: Path) -> None:
    rec = await storage.get_user_record(1001)
    assert rec["collected_data"]["symptoms"] == ""
    assert rec["collected_data"]["life_context"] == ""
    assert rec["history"] == []

    await storage.set_collected_field(1001, "symptoms", "головная боль")
    rec2 = await storage.get_user_record(1001)
    assert rec2["collected_data"]["symptoms"] == "головная боль"


@pytest.mark.asyncio
async def test_append_history_trims_to_max(isolated_storage: Path) -> None:
    uid = 42
    n = storage.MAX_HISTORY_MESSAGES + 7
    for i in range(n):
        await storage.append_history(uid, "user", f"m{i}")

    rec = await storage.get_user_record(uid)
    hist = rec["history"]
    assert len(hist) == storage.MAX_HISTORY_MESSAGES
    assert hist[0]["content"] == f"m{7}"
    assert hist[-1]["content"] == f"m{n - 1}"


@pytest.mark.asyncio
async def test_reset_user_session_clears_user(isolated_storage: Path) -> None:
    uid = 99
    await storage.set_collected_field(uid, "symptoms", "x")
    await storage.append_history(uid, "user", "hello")

    await storage.reset_user_session(uid)

    rec = await storage.get_user_record(uid)
    assert rec["collected_data"]["symptoms"] == ""
    assert rec["history"] == []


@pytest.mark.asyncio
async def test_save_root_persists(isolated_storage: Path) -> None:
    root = await storage.load_root()
    root["system_prompt"] = "SYS"
    await storage.save_root(root)

    root2 = await storage.load_root()
    assert root2["system_prompt"] == "SYS"
