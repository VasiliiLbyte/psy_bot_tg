"""LLM response JSON parsing (stage 4)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from models import DiagnosticReport

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Raised when the model output cannot be parsed as DiagnosticReport."""


def evaluation_json_user_instruction() -> str:
    """Instruction appended to the user message so the model returns JSON only."""
    schema_hint = json.dumps(
        DiagnosticReport.model_json_schema(),
        ensure_ascii=False,
        indent=2,
    )
    return (
        "Верни ответ ОДНИМ JSON-объектом без текста до или после, без Markdown и без ```. "
        "Поле preliminary_summary обязательно; остальные поля — как в схеме (пустые списки допустимы). "
        "Не используй ключи «диагноз», «diagnosis» и не формулируй окончательный диагноз.\n\n"
        f"JSON Schema:\n{schema_hint}"
    )


def _extract_json_substring(text: str) -> str:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()

    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]


def extract_json_raw(text: str) -> dict[str, Any]:
    """Best-effort extract a single JSON object from model output."""
    candidate = _extract_json_substring(text)
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ParseError("JSON root must be an object")
    return data


def parse_diagnostic_report(raw: str) -> DiagnosticReport:
    """Parse and validate model output into DiagnosticReport."""
    try:
        data = extract_json_raw(raw)
        return DiagnosticReport.model_validate(data)
    except ParseError:
        raise
    except Exception as exc:
        logger.debug("DiagnosticReport validation failed: %s", exc)
        raise ParseError(str(exc)) from exc


def format_report_for_user(report: DiagnosticReport) -> str:
    """Turn a validated report into a readable Telegram message (no extra disclaimer)."""
    lines: list[str] = [report.preliminary_summary.strip(), ""]

    if report.key_points:
        lines.append("На что обратить внимание:")
        for item in report.key_points:
            lines.append(f"• {item}")
        lines.append("")

    if report.specialist_recommendations:
        lines.append("К кому обратиться:")
        for item in report.specialist_recommendations:
            lines.append(f"• {item}")
        lines.append("")

    if report.self_care_suggestions:
        lines.append("Общие рекомендации:")
        for item in report.self_care_suggestions:
            lines.append(f"• {item}")
        lines.append("")

    if report.urgent_seek_care:
        lines.append(
            "⚠️ По описанию возможна необходимость срочной медицинской помощи. "
            "При ухудшении — скорая (112 / 103) или неотложка."
        )

    return "\n".join(line for line in lines if line is not None).rstrip()
