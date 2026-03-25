"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

import storage


@pytest.fixture
def isolated_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point storage at a temporary data.json under tmp_path."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_file = data_dir / "data.json"
    lock_file = data_dir / "data.json.lock"
    monkeypatch.setattr(storage, "DATA_PATH", data_file)
    monkeypatch.setattr(storage, "LOCK_PATH", lock_file)
    return data_file
