from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from config import load_config
from indicators import build_indicators
from market_data import MarketDataError, fetch_market_pair
from news_guard import evaluate_news_guard
from portfolio import build_trade_plan
from signal_engine import evaluate_signal
from storage import append_signal, ensure_data_files, load_state, save_state
from telegram_alert import (
    format_signal_message,
    mark_alert_sent,
    mark_daily_summary_sent,
    send_telegram_message,
    should_send_alert,
    should_send_daily_summary,
)


def _event_key(grade: str, plan: dict[str, object] | None, error: str | None = None) -> str:
    if error:
        return "error:data_fetch"
    action = plan.get("action", "none") if plan else "none"
    return f"signal:{grade}:{action}"


def run(dry_run_override: bool | None = None) -> int:
    config = load_config()
    dry_run = config.dry_run if dry_run_override is None else dry_run_override
    ensure_data_files(config.data_dir)
    state = load_state(config.data_dir)
    now = datetime.now(timezone.utc).isoformat()
    error: str | None = None
    tried_sources: list[str] = []
    data_source_used: str | None = None
    final_error: str | None = None
    zec_price = None
    signal = None
    plan = None

    try:
        market_pair = fetch_market_pair(config)
        zec = market_pair.zec
        btc = market_pair.btc
        tried_sources = market_pair.tried_sources
        data_source_used = market_pair.data_source_used
        zec_indicators = build_indicators(zec.candles)
        btc_indicators = build_indicators(btc.candles)
        news_guard = evaluate_news_guard()
        signal = evaluate_signal(zec.price_usdt, zec.volume, zec_indicators, btc_indicators)
        zec_price = zec.price_usdt
        plan = build_trade_plan(state, signal.grade, zec.price_usdt, config)
        append_signal(
            config.data_dir,
            {
                "timestamp": now,
                "symbol": config.zec_symbol,
                "price_usdt": zec.price_usdt,
                "price_thb": round(zec.price_usdt * config.usd_thb_rate, 2),
                "grade": signal.grade,
                "score": signal.score,
                "confidence": signal.confidence,
                "reasons": signal.reasons,
                "risk_flags": signal.risk_flags,
                "data_source_used": data_source_used,
                "tried_sources": tried_sources,
                "indicators": zec_indicators,
                "btc_guard": btc_indicators,
                "news_guard": news_guard,
                "plan": plan,
            },
        )
    except MarketDataError as exc:
        error = str(exc)
        tried_sources = exc.tried_sources
        final_error = exc.final_error
        signal = evaluate_signal(0, 0, {}, {}, data_error=error)
        append_signal(
            config.data_dir,
            {
                "timestamp": now,
                "symbol": config.zec_symbol,
                "grade": "C",
                "score": 0,
                "confidence": 0,
                "error": error,
                "tried_sources": tried_sources,
                "final_error": final_error,
                "risk_flags": ["data_error"],
            },
        )

    message = format_signal_message(
        signal,
        zec_price,
        config.usd_thb_rate,
        plan,
        error=error,
        tried_sources=tried_sources,
        final_error=final_error,
        data_source_used=data_source_used,
    )
    send_alert = False
    alert_key = _event_key(signal.grade, plan, error)

    if error or signal.grade in {"A", "C"}:
        if should_send_alert(state, alert_key):
            send_alert = True
            mark_alert_sent(state, alert_key)

    if not send_alert and should_send_daily_summary(state):
        send_alert = True
        mark_daily_summary_sent(state)

    if send_alert:
        send_telegram_message(config.telegram_bot_token, config.telegram_chat_id, message, dry_run=dry_run)
    elif dry_run:
        print("No Telegram alert needed after deduplication.")
        print(message)

    save_state(config.data_dir, state)
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run ZEC Guardian once.")
    parser.add_argument("--dry-run", action="store_true", help="Print alert payload without sending Telegram.")
    args = parser.parse_args()
    return run(dry_run_override=True if args.dry_run else None)


if __name__ == "__main__":
    raise SystemExit(main())
