"""Safety: critical-phrase filtering, disclaimers, incident audit log."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

from filelock import FileLock

logger = logging.getLogger(__name__)

INCIDENTS_PATH: Final[Path] = Path(__file__).resolve().parent / "data" / "incidents.json"
INCIDENTS_LOCK_PATH: Final[Path] = Path(__file__).resolve().parent / "data" / "incidents.json.lock"

MAX_EXCERPT_LEN: Final[int] = 240

# Дисклеймеры (см. docs/development-guidelines.md, docs/architecture.md).
BRIEF_NON_MEDICAL_NOTICE: Final[str] = (
    "Это не медицинская консультация и не замена приёма врача."
)

RECOMMENDATIONS_FOOTER_DISCLAIMER: Final[str] = (
    "\n\n⚠️ Это не медицинская консультация. Обратитесь к специалисту. "
    "При острых состояниях вызывайте скорую помощь (112 / 103)."
)

_EMERGENCY_USER_MESSAGE: Final[str] = (
    "По вашему сообщению видны признаки возможной срочной угрозы жизни или здоровью. "
    "Продолжить анкетирование здесь небезопасно — обратитесь за экстренной помощью.\n\n"
    "Если опасность сейчас: вызовите скорую (103 или 112) или обратитесь в ближайший "
    "пункт неотложной помощи.\n\n"
    "Когда ситуация стабилизируется, при необходимости начните заново: /start.\n\n"
    + BRIEF_NON_MEDICAL_NOTICE
)


@dataclass(frozen=True, slots=True)
class SafetyCheckResult:
    """Result of screening user text for crisis / emergency wording."""

    is_critical: bool
    category: str | None = None
    rule_id: str | None = None


# (category, rule_id, needle): несколько слов — только как соседние токены;
# одно слово — для violence_others только целый токен (и не после «не»);
# иначе — вхождение подстроки в нормализованный текст.
_CRITICAL_RULES: tuple[tuple[str, str, str], ...] = (
    ("suicide_self_harm", "ru_suicide", "суицид"),
    ("suicide_self_harm", "ru_samoubiistvo", "самоубийств"),
    ("suicide_self_harm", "ru_pokonchit", "покончить с собой"),
    ("suicide_self_harm", "ru_ne_hochu_zhit", "не хочу жить"),
    ("suicide_self_harm", "ru_hochu_umret", "хочу умереть"),
    ("suicide_self_harm", "ru_net_smysla", "нет смысла жить"),
    ("suicide_self_harm", "ru_hochu_pokonchit", "хочу покончить"),
    ("suicide_self_harm", "ru_povesitsya", "повеситься"),
    ("suicide_self_harm", "ru_poveshus", "повешусь"),
    ("suicide_self_harm", "ru_vybrositsya", "выброшусь"),
    ("suicide_self_harm", "ru_prygnu", "прыгну с"),
    ("suicide_self_harm", "ru_zarezat_sebia", "зарежу себя"),
    ("suicide_self_harm", "ru_otravlius", "отравлюсь"),
    ("suicide_self_harm", "ru_peredoz", "передозировк"),
    ("suicide_self_harm", "ru_navredit_sebe", "навредить себе"),
    ("suicide_self_harm", "ru_rezhu_sebia", "режу себя"),
    ("suicide_self_harm", "en_kill_myself", "kill myself"),
    ("suicide_self_harm", "en_want_to_die", "want to die"),
    ("suicide_self_harm", "en_suicide", "suicide"),
    ("violence_others", "ru_ubiu_ego", "убью его"),
    ("violence_others", "ru_ubiu_ee", "убью её"),
    ("violence_others", "ru_ubiu_ee2", "убью ее"),
    ("violence_others", "ru_ubiu_vseh", "убью всех"),
    ("violence_others", "ru_ubit_ego", "убить его"),
    ("violence_others", "ru_ubit_ee", "убить её"),
    ("violence_others", "ru_ubit_ee2", "убить ее"),
    ("violence_others", "ru_ubit_vseh", "убить всех"),
    ("violence_others", "ru_vzorvu", "взорву"),
    ("violence_others", "ru_rasstreliaiu", "расстреляю"),
    ("acute_medical", "ru_ne_dyshit", "не дышит"),
    ("acute_medical", "ru_poterial_soznanie", "потерял сознание"),
    ("acute_medical", "ru_poteriala_soznanie", "потеряла сознание"),
    ("acute_medical", "ru_infarkt_seichas", "инфаркт сейчас"),
    ("acute_medical", "ru_insult_seichas", "инсульт сейчас"),
    ("acute_medical", "ru_krovotech_ne_ostanavl", "кровотечение не останавливается"),
)


def normalize_for_matching(text: str) -> str:
    """Lowercase / casefold and collapse whitespace for substring checks."""
    folded = text.casefold()
    parts = folded.split()
    return " ".join(parts)


def _strip_token_edges(token: str) -> str:
    return token.strip(".,!?;:\"'()[]")


def _tokens(normalized_sentence: str) -> list[str]:
    return [
        t
        for raw in normalized_sentence.split()
        if (t := _strip_token_edges(raw))
    ]


def _phrase_in_tokens(
    tokens: list[str],
    phrase_words: list[str],
    category: str,
) -> bool:
    n = len(phrase_words)
    if n == 0 or len(tokens) < n:
        return False
    for i in range(len(tokens) - n + 1):
        if tokens[i : i + n] != phrase_words:
            continue
        if category == "violence_others" and i > 0 and tokens[i - 1] == "не":
            continue
        return True
    return False


def _violence_single_word_hit(tokens: list[str], word: str) -> bool:
    for i, tok in enumerate(tokens):
        if tok != word:
            continue
        if i > 0 and tokens[i - 1] == "не":
            continue
        return True
    return False


def check_user_message(text: str) -> SafetyCheckResult:
    """Return whether the user text matches known crisis or emergency wording."""
    normalized = normalize_for_matching(text.strip())
    if not normalized:
        return SafetyCheckResult(is_critical=False)
    tokens = _tokens(normalized)
    for category, rule_id, needle in _CRITICAL_RULES:
        phrase_words = needle.casefold().split()
        if len(phrase_words) > 1:
            if _phrase_in_tokens(tokens, phrase_words, category):
                return SafetyCheckResult(
                    is_critical=True,
                    category=category,
                    rule_id=rule_id,
                )
            continue
        word = phrase_words[0]
        if category == "violence_others":
            if _violence_single_word_hit(tokens, word):
                return SafetyCheckResult(
                    is_critical=True,
                    category=category,
                    rule_id=rule_id,
                )
            continue
        if word in normalized:
            return SafetyCheckResult(
                is_critical=True,
                category=category,
                rule_id=rule_id,
            )
    return SafetyCheckResult(is_critical=False)


def emergency_reply_for_user() -> str:
    """Fixed response when critical phrasing is detected (no LLM)."""
    return _EMERGENCY_USER_MESSAGE


def _default_incidents_root() -> dict[str, Any]:
    return {"incidents": []}


def _read_incidents_locked() -> dict[str, Any]:
    INCIDENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not INCIDENTS_PATH.is_file():
        root = _default_incidents_root()
        tmp = INCIDENTS_PATH.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(root, fh, ensure_ascii=False, indent=2)
        tmp.replace(INCIDENTS_PATH)
        return root

    with FileLock(INCIDENTS_LOCK_PATH):
        with open(INCIDENTS_PATH, encoding="utf-8") as fh:
            return json.load(fh)


def _write_incidents_locked(root: dict[str, Any]) -> None:
    INCIDENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(INCIDENTS_LOCK_PATH):
        tmp = INCIDENTS_PATH.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(root, fh, ensure_ascii=False, indent=2)
        tmp.replace(INCIDENTS_PATH)


def _truncate_excerpt(text: str, max_len: int = MAX_EXCERPT_LEN) -> str:
    one_line = " ".join(text.strip().split())
    if len(one_line) <= max_len:
        return one_line
    return one_line[: max_len - 1] + "…"


async def log_safety_incident(
    user_id: int,
    result: SafetyCheckResult,
    raw_user_text: str,
) -> None:
    """Append one incident record for audit (data/incidents.json)."""
    if not result.is_critical:
        return
    excerpt = _truncate_excerpt(raw_user_text)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "category": result.category,
        "rule_id": result.rule_id,
        "text_excerpt": excerpt,
    }

    def _append() -> None:
        root = _read_incidents_locked()
        incidents: list[dict[str, Any]] = root.setdefault("incidents", [])
        incidents.append(entry)
        root["incidents"] = incidents
        _write_incidents_locked(root)

    try:
        await asyncio.to_thread(_append)
    except (OSError, json.JSONDecodeError, TypeError):
        logger.exception("Failed to persist safety incident for user %s", user_id)
        return

    logger.warning(
        "Safety incident recorded: user_id=%s category=%s rule_id=%s",
        user_id,
        result.category,
        result.rule_id,
    )
