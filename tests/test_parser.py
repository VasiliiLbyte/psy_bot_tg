"""Tests for JSON extraction and DiagnosticReport parsing."""

from __future__ import annotations

import pytest

from models import DiagnosticReport
from parser import ParseError, extract_json_raw, format_report_for_user, parse_diagnostic_report


def test_parse_plain_json() -> None:
    raw = (
        '{"preliminary_summary":"Усталость","key_points":["сон"],'
        '"specialist_recommendations":["терапевт"],"self_care_suggestions":[],'
        '"urgent_seek_care":false}'
    )
    r = parse_diagnostic_report(raw)
    assert r.preliminary_summary == "Усталость"
    assert r.key_points == ["сон"]
    assert r.urgent_seek_care is False


def test_parse_fenced_json() -> None:
    raw = """Here you go:
```json
{"preliminary_summary": "Тревога", "urgent_seek_care": true}
```
"""
    r = parse_diagnostic_report(raw)
    assert "Тревога" in r.preliminary_summary
    assert r.urgent_seek_care is True


def test_parse_invalid_raises() -> None:
    with pytest.raises(ParseError):
        parse_diagnostic_report("not json")


def test_format_report_for_user() -> None:
    r = DiagnosticReport(
        preliminary_summary="Кратко.",
        key_points=["a"],
        specialist_recommendations=["b"],
        urgent_seek_care=True,
    )
    text = format_report_for_user(r)
    assert "Кратко." in text
    assert "• a" in text
    assert "скорая" in text.lower() or "103" in text


def test_extract_json_raw_rejects_non_object() -> None:
    with pytest.raises(ParseError):
        extract_json_raw("[1,2,3]")
