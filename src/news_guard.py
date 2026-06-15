from __future__ import annotations


def evaluate_news_guard() -> dict[str, str | bool]:
    return {
        "ok": True,
        "state": "not_connected",
        "reason": "News guard is reserved for future free news/RSS checks; no negative news source is connected yet.",
    }

