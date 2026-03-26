"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

import db
import storage


@pytest.fixture
async def isolated_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point storage at a temporary SQLite db under tmp_path."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_file = data_dir / "bot.db"
    monkeypatch.setattr(storage, "DATA_PATH", db_file)
    await db.init_db(str(db_file))
    return db_file
