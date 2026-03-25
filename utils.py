"""Shared helpers."""

from __future__ import annotations

import re

# Schemes accepted by aiogram/aiohttp-socks (no socks5h — normalize below).
_VALID_PROXY_SCHEMES = ("http://", "https://", "socks4://", "socks5://")


def normalize_telegram_proxy(raw: str) -> str:
    """Prepare TELEGRAM_PROXY for AiohttpSession.

    - Strips whitespace and matching outer quotes.
    - ``socks5h://`` → ``socks5://`` (aiogram expects the latter).
    - Bare ``host:port`` or ``[IPv6]:port`` → ``socks5://...`` (typical local FoXray/Xray).
    """
    if not raw:
        return ""
    s = raw.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1].strip()

    low = s.lower()
    if low.startswith("socks5h://"):
        return "socks5://" + s[len("socks5h://") :]
    if low.startswith("socks4a://"):
        return "socks4://" + s[len("socks4a://") :]

    if any(low.startswith(p) for p in _VALID_PROXY_SCHEMES):
        return s

    if "@" in s:
        return s

    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}:\d{1,5}", s):
        return f"socks5://{s}"
    if re.fullmatch(r"\[[^\]]+\]:\d{1,5}", s):
        return f"socks5://{s}"
    if re.fullmatch(r"(?i)[a-z0-9][a-z0-9.-]*:\d{1,5}", s):
        return f"socks5://{s}"

    return s


def telegram_proxy_is_configured(proxy: str) -> bool:
    """True if *proxy* is non-empty and has a usable scheme after normalization."""
    p = normalize_telegram_proxy(proxy)
    if not p:
        return False
    low = p.lower()
    return any(low.startswith(s) for s in _VALID_PROXY_SCHEMES)
