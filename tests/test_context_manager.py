"""Tests for prompt assembly and token-budget trimming."""

from __future__ import annotations

import tiktoken

from context_manager import (
    DEFAULT_MAX_CONTEXT_TOKENS,
    build_evaluation_chat_messages,
    count_tokens_for_messages,
    format_collected_data_block,
    history_to_messages,
)


def test_format_collected_data_block() -> None:
    text = format_collected_data_block(
        {"symptoms": "головная боль", "life_context": "неделя"},
    )
    assert "Собранные данные:" in text
    assert "головная боль" in text
    assert "неделя" in text


def test_history_normalizes_role() -> None:
    hist = history_to_messages([{"role": "Assistant", "content": "Hi"}])
    assert hist == [{"role": "assistant", "content": "Hi"}]
    hist2 = history_to_messages([{"role": "unknown", "content": "x"}])
    assert hist2[0]["role"] == "user"


def test_build_messages_order_and_includes_current_user() -> None:
    messages = build_evaluation_chat_messages(
        system_prompt="SYS",
        collected_data={"symptoms": "s", "life_context": "c"},
        history=[{"role": "user", "content": "u1"}, {"role": "assistant", "content": "a1"}],
        current_user_content="FINAL",
        max_context_tokens=DEFAULT_MAX_CONTEXT_TOKENS,
    )
    assert messages[0] == {"role": "system", "content": "SYS"}
    assert "Собранные данные:" in messages[1]["content"]
    assert messages[2]["role"] == "user" and messages[2]["content"] == "u1"
    assert messages[-1] == {"role": "user", "content": "FINAL"}


def test_trimming_drops_oldest_history_first() -> None:
    enc = tiktoken.get_encoding("cl100k_base")
    token_budget = 800
    # Large enough vs. budget that assembled(prefix + history + suffix) exceeds it reliably.
    filler = ("word " * 4000) + "\nunique_marker_for_huge_user_turn_xyz\n"
    assert len(enc.encode(filler)) > token_budget * 2
    history = [
        {"role": "user", "content": filler},
        {"role": "assistant", "content": "short"},
    ]
    messages = build_evaluation_chat_messages(
        system_prompt="x",
        collected_data={"symptoms": "s", "life_context": "c"},
        history=history,
        current_user_content="evaluate please",
        max_context_tokens=token_budget,
    )
    joined = "\n".join(m["content"] for m in messages)
    assert "unique_marker_for_huge_user_turn_xyz" not in joined
    assert "short" in joined
    assert count_tokens_for_messages(messages) <= token_budget


def test_empty_system_omits_first_message() -> None:
    messages = build_evaluation_chat_messages(
        system_prompt="   ",
        collected_data={"symptoms": "s", "life_context": "c"},
        history=[],
        current_user_content="u",
        max_context_tokens=DEFAULT_MAX_CONTEXT_TOKENS,
    )
    assert messages[0]["role"] == "system"
    assert "Собранные данные:" in messages[0]["content"]
