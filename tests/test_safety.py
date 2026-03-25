"""Tests for crisis phrasing detection and incident logging."""

from __future__ import annotations

import json

import pytest

import safety


def test_check_benign_text() -> None:
    r = safety.check_user_message("Головная боль третий день, температура нет")
    assert r.is_critical is False


def test_check_suicide_phrase() -> None:
    r = safety.check_user_message("Думаю о суициде")
    assert r.is_critical is True
    assert r.category == "suicide_self_harm"


def test_violence_phrase_negation_not_triggered() -> None:
    r = safety.check_user_message("я точно не убью всех на работе")
    assert r.is_critical is False


def test_violence_phrase_triggered() -> None:
    r = safety.check_user_message("Сейчас убью всех")
    assert r.is_critical is True
    assert r.category == "violence_others"


def test_violence_single_word_negation() -> None:
    assert safety.check_user_message("я не взорву ничего").is_critical is False
    assert safety.check_user_message("я взорву здание").is_critical is True


@pytest.mark.asyncio
async def test_log_safety_incident_append(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(safety, "INCIDENTS_PATH", tmp_path / "incidents.json")
    monkeypatch.setattr(safety, "INCIDENTS_LOCK_PATH", tmp_path / "incidents.json.lock")
    result = safety.SafetyCheckResult(
        is_critical=True,
        category="suicide_self_harm",
        rule_id="ru_suicide",
    )
    await safety.log_safety_incident(7, result, "long " * 80)
    payload = json.loads((tmp_path / "incidents.json").read_text(encoding="utf-8"))
    assert len(payload["incidents"]) == 1
    row = payload["incidents"][0]
    assert row["user_id"] == 7
    assert row["category"] == "suicide_self_harm"
    assert row["rule_id"] == "ru_suicide"
    assert len(row["text_excerpt"]) <= safety.MAX_EXCERPT_LEN + 2


@pytest.mark.asyncio
async def test_log_safety_incident_skips_non_critical(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(safety, "INCIDENTS_PATH", tmp_path / "incidents.json")
    monkeypatch.setattr(safety, "INCIDENTS_LOCK_PATH", tmp_path / "incidents.json.lock")
    await safety.log_safety_incident(
        1,
        safety.SafetyCheckResult(is_critical=False),
        "ok",
    )
    path = tmp_path / "incidents.json"
    assert not path.is_file()


def test_normalize_for_matching() -> None:
    assert safety.normalize_for_matching("  A\nB\tc ") == "a b c"
