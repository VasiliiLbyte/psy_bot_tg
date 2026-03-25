"""Dialog context and prompt assembly (stage 5).

Loads logical pieces (system prompt, collected data, history) prepared by the
caller from ``storage`` / ``data.json``, builds chat messages for the LLM,
counts tokens with ``tiktoken`` (``cl100k_base``), and trims oldest history
entries if the budget is exceeded — см. docs/context-management.md.
"""

from __future__ import annotations

import logging
from typing import Any

import tiktoken

logger = logging.getLogger(__name__)

ENCODING_NAME = "cl100k_base"
DEFAULT_MAX_CONTEXT_TOKENS = 100_000
# Nominal per-message framing (roles, separators) for coarse budgeting.
_PER_MESSAGE_OVERHEAD = 4

_encoding: tiktoken.Encoding | None = None


def _get_encoding() -> tiktoken.Encoding:
    global _encoding
    if _encoding is None:
        _encoding = tiktoken.get_encoding(ENCODING_NAME)
    return _encoding


def count_tokens_for_messages(messages: list[dict[str, str]]) -> int:
    """Approximate total tokens for a list of chat messages."""
    enc = _get_encoding()
    total = 0
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        total += _PER_MESSAGE_OVERHEAD
        total += len(enc.encode(role))
        total += len(enc.encode(content))
    return total


def format_collected_data_block(collected_data: dict[str, Any]) -> str:
    """Human-readable «Собранные данные» block per docs/context-management.md."""
    symptoms = str(collected_data.get("symptoms", "") or "не указано")
    life = str(collected_data.get("life_context", "") or "не указано")
    return (
        "Собранные данные:\n"
        f"Симптомы: {symptoms}\n"
        f"Контекст: {life}"
    )


def _normalize_role(role: str) -> str:
    r = (role or "user").strip().lower()
    if r in ("system", "assistant", "user"):
        return r
    return "user"


def history_to_messages(history: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Map stored history items to OpenRouter/OpenAI-style role/content dicts."""
    out: list[dict[str, str]] = []
    for entry in history:
        role = _normalize_role(str(entry.get("role", "user")))
        content = str(entry.get("content", ""))
        out.append({"role": role, "content": content})
    return out


def build_evaluation_chat_messages(
    *,
    system_prompt: str,
    collected_data: dict[str, Any],
    history: list[dict[str, Any]],
    current_user_content: str,
    max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
) -> list[dict[str, str]]:
    """Assemble evaluation messages: system + collected + history + current user.

    If the total exceeds ``max_context_tokens``, the oldest history messages
    are dropped first until within budget (or history is exhausted).
    """
    prefix: list[dict[str, str]] = []
    stripped = system_prompt.strip()
    if stripped:
        prefix.append({"role": "system", "content": stripped})

    prefix.append({
        "role": "system",
        "content": format_collected_data_block(collected_data),
    })

    history_messages = history_to_messages(history)
    suffix = [{"role": "user", "content": current_user_content}]

    def assembled(hist: list[dict[str, str]]) -> list[dict[str, str]]:
        return prefix + hist + suffix

    trimmed = history_messages[:]
    while trimmed and count_tokens_for_messages(assembled(trimmed)) > max_context_tokens:
        dropped = trimmed.pop(0)
        logger.info(
            "Context trim: removed oldest history message (role=%s) to stay under %s tokens",
            dropped.get("role"),
            max_context_tokens,
        )

    final = assembled(trimmed)
    if count_tokens_for_messages(final) > max_context_tokens:
        logger.warning(
            "Token budget %s exceeded after history trim; prefix/suffix may be too large",
            max_context_tokens,
        )

    return final
