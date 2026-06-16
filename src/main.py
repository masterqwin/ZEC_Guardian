from __future__ import annotations

import argparse
import sys
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from config import load_config
from dataclasses import replace
from fx_rate import fetch_usd_thb_rate
from btc_guard import evaluate_btc_guard
from bounce_engine import estimate_bounce_probability
from daily_summary import build_daily_summary
from entry_score_engine import evaluate_entry_score
from event_engine import detect_events, should_send_event
from indicators import build_indicators
from learning_engine import append_learning_record, build_learning_record
from leg_planner import plan_next_leg
from market_data import MarketDataError, fetch_market_pair
from news_guard import evaluate_news_guard
from opportunity_engine import evaluate_opportunity
from portfolio import build_trade_plan
from position_manager import buy_lot, recalculate_position, sell_all, sell_percent, sell_zec
from profit_engine import action_from_profit, calculate_profit_state
from qa_engine import build_qa_status
from recovery_engine import estimate_recovery
from signal_engine import evaluate_signal
from signal_outcome_tracker import create_outcome_record, update_pending_outcomes
from storage import append_signal, ensure_data_files, load_state, save_state
from telegram_alert import (
    format_signal_message,
    format_v2_message,
    mark_alert_sent,
    mark_daily_summary_sent,
    send_telegram_message,
    should_send_alert,
    should_send_daily_summary,
)
from trade_journal import append_trade, buy_trade_record


def _event_key(grade: str, action: str, error: str | None = None) -> str:
    if error:
        return "error:data_fetch"
    return f"signal:{grade}:{action}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _manual_summary(state: dict[str, Any], trade: dict[str, Any]) -> str:
    position = state["position"]
    lines = [
        "ZEC Guardian Manual Update",
        f"Action: {trade['type']}",
        f"Cash THB: {state['cash_thb']:,.2f}",
        f"Realized Profit THB: {state['realized_profit_thb']:,.2f}",
        f"Total ZEC: {position['total_zec']}",
        f"Total Cost THB: {position['total_cost_thb']:,.2f}",
        f"Average Cost THB: {position['average_cost_thb']:,.2f}",
    ]
    return "\n".join(lines)


def _send_manual_position_update(config: Any, state: dict[str, Any], trade: dict[str, Any], dry_run: bool) -> None:
    if trade["type"] == "BUY":
        current_price_thb = float(trade["price_thb"])
        current_price_usdt = float(trade["price_usdt"])
    else:
        current_price_thb = float(trade["price_thb"])
        current_price_usdt = float(trade["price_usdt"])
    profit_state = calculate_profit_state(state, current_price_thb)
    dummy_signal = type("SignalLike", (), {"grade": "B", "confidence": 0, "reasons": ["Manual position update"], "risk_flags": []})()
    message = format_v2_message(
        dummy_signal,
        current_price_thb,
        current_price_usdt,
        "Manual",
        state["position"],
        f"MANUAL {trade['type']}",
        profit_state=profit_state,
    )
    send_telegram_message(config.telegram_bot_token, config.telegram_chat_id, message, dry_run=dry_run)


def handle_manual_command(args: argparse.Namespace) -> int:
    config = load_config()
    dry_run = bool(args.dry_run)
    ensure_data_files(config.data_dir)
    state = load_state(config.data_dir)
    timestamp = _now_iso()

    if args.buy:
        state, lot = buy_lot(state, args.zec, args.price_thb, args.price_usdt, timestamp=timestamp)
        trade = buy_trade_record(lot, deepcopy(state["position"]), timestamp)
    elif args.sell_percent is not None:
        state, trade = sell_percent(state, args.sell_percent, args.price_thb, args.price_usdt, timestamp=timestamp)
    elif args.sell_zec is not None:
        state, trade = sell_zec(state, args.sell_zec, args.price_thb, args.price_usdt, timestamp=timestamp)
    elif args.sell_all:
        state, trade = sell_all(state, args.price_thb, args.price_usdt, timestamp=timestamp)
    else:
        raise ValueError("No manual command was provided")

    save_state(config.data_dir, state)
    append_trade(config.data_dir, trade)
    print(_manual_summary(state, trade))
    if config.telegram_bot_token and config.telegram_chat_id:
        _send_manual_position_update(config, state, trade, dry_run=dry_run)
    return 0


def _recommended_action(state: dict[str, Any], signal_grade: str, profit_state: dict[str, Any] | None, leg_plan: dict[str, Any] | None) -> str:
    if float(state["position"]["total_zec"]) <= 0:
        return "BUY LEG1" if signal_grade == "A" else "WAIT / NO TRADE"
    if leg_plan and leg_plan.get("can_buy"):
        return f"BUY {leg_plan['next_leg_id']}"
    return action_from_profit(profit_state or {}, signal_grade)


def run(dry_run_override: bool | None = None) -> int:
    config = load_config()
    dry_run = config.dry_run if dry_run_override is None else dry_run_override
    ensure_data_files(config.data_dir)
    state = recalculate_position(load_state(config.data_dir))
    now = _now_iso()
    error: str | None = None
    tried_sources: list[str] = []
    data_source_used: str | None = None
    final_error: str | None = None
    zec_price_usdt: float | None = None
    zec_price_thb: float | None = None
    signal = None
    plan: dict[str, Any] | None = None
    profit_state: dict[str, Any] | None = None
    leg_plan: dict[str, Any] | None = None
    entry_result: dict[str, Any] | None = None
    bounce_result: dict[str, Any] | None = None
    recovery_result: dict[str, Any] | None = None
    opportunity_result: dict[str, Any] | None = None
    btc_guard_result: dict[str, Any] | None = None
    event: dict[str, Any] | None = None
    qa_status: dict[str, Any] | None = None
    recommended_action = "WAIT / NO TRADE"
    fx = fetch_usd_thb_rate(config)

    try:
        market_pair = fetch_market_pair(config)
        zec = market_pair.zec
        btc = market_pair.btc
        tried_sources = market_pair.tried_sources
        data_source_used = market_pair.data_source_used
        zec_indicators = build_indicators(zec.candles)
        zec_indicators["current_volume"] = zec.volume
        btc_indicators = build_indicators(btc.candles)
        news_guard = evaluate_news_guard()
        btc_guard_result = evaluate_btc_guard(btc, btc_indicators)
        direct_thb = zec.price_thb is not None
        fx_used = not direct_thb
        zec_price_usdt = zec.price_usdt
        zec_price_thb = round(float(zec.price_thb), 2) if direct_thb else round(zec.price_usdt * fx.rate, 2)
        entry_result = evaluate_entry_score(zec_price_thb, zec_indicators, btc_guard_result)
        bounce_result = estimate_bounce_probability(entry_result, btc_guard_result)
        opportunity_result = evaluate_opportunity(entry_result["entry_score"], bounce_result["bounce_probability"])
        signal = evaluate_signal(zec.price_usdt, zec.volume, zec_indicators, btc_indicators)
        signal_grade_for_legacy = "A" if entry_result["label"] in {"ENTRY", "STRONG_ENTRY", "SS_PLUS"} else "B" if entry_result["label"] == "NEAR_ENTRY" else "C" if entry_result["label"] == "DANGER" else "B"
        plan = build_trade_plan(state, signal_grade_for_legacy, zec.price_usdt, replace(config, usd_thb_rate=(fx.rate if fx_used else zec_price_thb / zec.price_usdt)))

        if float(state["position"]["total_zec"]) > 0:
            profit_state = calculate_profit_state(state, zec_price_thb)
            is_dip = zec_price_thb < float(state["position"]["average_cost_thb"])
            if entry_result["label"] in {"ENTRY", "STRONG_ENTRY", "SS_PLUS"} and is_dip:
                leg_plan = plan_next_leg(state, "A", zec_price_thb, zec.price_usdt)
        recovery_result = estimate_recovery(state["position"], profit_state)
        recommended_action = _recommended_action(state, signal_grade_for_legacy, profit_state, leg_plan)
        if float(state["position"]["total_zec"]) <= 0 and entry_result["label"] == "NEAR_ENTRY":
            recommended_action = "WATCH CLOSELY"
        event_list = detect_events(zec_price_thb, state, entry_result["entry_score"], entry_result["label"])
        event = event_list[0] if event_list else None
        update_pending_outcomes(config.data_dir, zec_price_thb)
        qa_status = build_qa_status(state, data_source_used, entry_result["label"], event.get("event_type") if event else None)

        append_signal(
            config.data_dir,
            {
                "timestamp": now,
                "symbol": config.zec_symbol,
                "price_usdt": zec.price_usdt,
                "price_thb": zec_price_thb,
                "grade": signal_grade_for_legacy,
                "signal_type": entry_result["label"],
                "score": signal.score,
                "confidence": signal.confidence,
                "entry_score": entry_result["entry_score"],
                "bounce_probability": bounce_result["bounce_probability"],
                "recovery_probability": recovery_result["recovery_7d"],
                "opportunity_score": opportunity_result["opportunity_score"],
                "btc_guard_status": btc_guard_result["status"],
                "why_not_entry": entry_result["blockers"],
                "reasons": signal.reasons,
                "risk_flags": signal.risk_flags,
                "data_source_used": data_source_used,
                "tried_sources": tried_sources,
                "fx_rate": fx.rate if fx_used else None,
                "fx_source": fx.source if fx_used else None,
                "indicators": zec_indicators,
                "btc_guard": btc_indicators,
                "btc_guard_detail": btc_guard_result,
                "news_guard": news_guard,
                "position": deepcopy(state["position"]),
                "profit_state": profit_state,
                "leg_plan": leg_plan,
                "event": event,
                "qa_status": qa_status,
                "recommended_action": recommended_action,
                "plan": plan,
            },
        )
        learning_record = build_learning_record(
            now,
            zec_price_thb,
            zec.price_usdt,
            signal,
            data_source_used,
            state["position"],
            recommended_action,
            entry_score=entry_result["entry_score"],
            bounce_probability=bounce_result["bounce_probability"],
            recovery_probability=recovery_result["recovery_7d"],
            opportunity_score=opportunity_result["opportunity_score"],
            btc_guard=btc_guard_result,
            blockers=entry_result["blockers"],
            event_type=event.get("event_type") if event else None,
            signal_type=entry_result["label"],
        )
        append_learning_record(config.data_dir, create_outcome_record(learning_record))
    except MarketDataError as exc:
        error = str(exc)
        tried_sources = exc.tried_sources
        final_error = exc.final_error
        signal = evaluate_signal(0, 0, {}, {}, data_error=error)
        qa_status = build_qa_status(state, data_source_used, "DANGER", "SYSTEM_ERROR", error=error)
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
                "position": deepcopy(state["position"]),
            },
        )

    if error:
        message = format_signal_message(
            signal,
            zec_price_usdt,
            config.usd_thb_rate,
            plan,
            error=error,
            tried_sources=tried_sources,
            final_error=final_error,
            data_source_used=data_source_used,
            fx_rate=fx.rate,
            fx_source=fx.source,
        )
    else:
        message = format_v2_message(
            signal,
            zec_price_thb,
            zec_price_usdt,
            data_source_used,
            state["position"],
            recommended_action,
            profit_state=profit_state,
            leg_plan=leg_plan,
            fx_rate=fx.rate if (zec_price_thb is not None and zec_price_usdt and data_source_used != "CoinGecko") else None,
            fx_source=fx.source if (zec_price_thb is not None and zec_price_usdt and data_source_used != "CoinGecko") else None,
            entry_result=entry_result,
            bounce_result=bounce_result,
            opportunity_result=opportunity_result,
            btc_guard=btc_guard_result,
            event=event,
        )

    alert_key = _event_key(getattr(signal, "grade", "C"), recommended_action, error)
    send_alert = False
    major_event = event and should_send_event(event, state)
    if major_event:
        send_alert = True
    elif error or getattr(signal, "grade", "C") in {"A", "C"} or (entry_result and entry_result.get("label") in {"ENTRY", "STRONG_ENTRY", "SS_PLUS", "NEAR_ENTRY"}) or float(state["position"]["total_zec"]) > 0:
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

    if zec_price_thb is not None:
        state.setdefault("alerts", {})["last_reference_price_thb"] = zec_price_thb
        if entry_result:
            state["alerts"]["last_entry_score"] = entry_result["entry_score"]
            if entry_result["label"] in {"ENTRY", "STRONG_ENTRY", "SS_PLUS"}:
                state["alerts"]["last_entry_signal_price_thb"] = zec_price_thb
    state["last_daily_summary_preview"] = build_daily_summary(
        state,
        {
            "qa_status": qa_status or {},
            "price_thb": zec_price_thb or 0,
            "btc_guard": btc_guard_result or {},
            "signal_label": entry_result.get("label") if entry_result else "DANGER",
            "entry_score": entry_result.get("entry_score") if entry_result else 0,
            "bounce_probability": bounce_result.get("bounce_probability") if bounce_result else 0,
            "opportunity_score": opportunity_result.get("opportunity_score") if opportunity_result else 0,
            "last_event": event.get("event_type") if event else "-",
        },
    )
    save_state(config.data_dir, state)
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run ZEC Guardian once.")
    parser.add_argument("--dry-run", action="store_true", help="Print alert payload without sending Telegram.")
    parser.add_argument("--buy", action="store_true", help="Record a manual buy.")
    parser.add_argument("--sell-percent", type=float, help="Record a manual sell by percent of current position.")
    parser.add_argument("--sell-zec", type=float, help="Record a manual sell by ZEC amount.")
    parser.add_argument("--sell-all", action="store_true", help="Record a manual sell of the whole position.")
    parser.add_argument("--zec", type=float, help="ZEC quantity for manual buy.")
    parser.add_argument("--price-thb", type=float, help="Manual trade price in THB.")
    parser.add_argument("--price-usdt", type=float, help="Manual trade price in USDT.")
    args = parser.parse_args()

    manual = args.buy or args.sell_percent is not None or args.sell_zec is not None or args.sell_all
    if manual:
        if args.price_thb is None or args.price_usdt is None:
            parser.error("manual commands require --price-thb and --price-usdt")
        if args.buy and args.zec is None:
            parser.error("--buy requires --zec")
        return handle_manual_command(args)
    return run(dry_run_override=True if args.dry_run else None)


if __name__ == "__main__":
    raise SystemExit(main())
