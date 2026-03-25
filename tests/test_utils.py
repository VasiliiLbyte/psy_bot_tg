"""Tests for shared utils."""

from __future__ import annotations

from utils import normalize_telegram_proxy, telegram_proxy_is_configured


def test_normalize_bare_ipv4_gets_socks5() -> None:
    assert normalize_telegram_proxy("127.0.0.1:1080") == "socks5://127.0.0.1:1080"


def test_normalize_preserves_full_url() -> None:
    assert normalize_telegram_proxy("http://127.0.0.1:7890") == "http://127.0.0.1:7890"


def test_normalize_socks5h() -> None:
    assert normalize_telegram_proxy("socks5h://127.0.0.1:1080") == "socks5://127.0.0.1:1080"


def test_normalize_strips_quotes() -> None:
    assert normalize_telegram_proxy('"socks5://127.0.0.1:1080"') == "socks5://127.0.0.1:1080"


def test_telegram_proxy_is_configured() -> None:
    assert telegram_proxy_is_configured("127.0.0.1:1080") is True
    assert telegram_proxy_is_configured("not a url") is False
