from __future__ import annotations

from datetime import datetime, timezone
import sys
from typing import Any

import requests

from reason_formatter import (
    confidence_text,
    format_action_lines,
    format_btc_guard,
    format_reason_lines,
    rolling_drop_translation,
)


IMPORTANT_GRADES = {"A", "C"}
BRAND_HEADER = "\U0001f6e1\ufe0f SEK Trade Guardian\nMode: ZEC Guardian Mode"
NO_ENTRY_ACTION = "\u0e2b\u0e49\u0e32\u0e21\u0e40\u0e02\u0e49\u0e32 / \u0e07\u0e14\u0e0a\u0e49\u0e2d\u0e19"
WAITING_TP_TEXT = "TP50/TP100: \u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e04\u0e33\u0e19\u0e27\u0e13\u0e08\u0e19\u0e01\u0e27\u0e48\u0e32\u0e08\u0e30\u0e21\u0e35 Entry Signal A \u0e2b\u0e23\u0e37\u0e2d\u0e21\u0e35 Position \u0e08\u0e23\u0e34\u0e07"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def branded_message(message_type: str, lines: list[str]) -> str:
    return "\n".join([BRAND_HEADER, message_type, *lines])


def should_send_alert(state: dict[str, Any], event_key: str, dedupe_minutes: int = 360) -> bool:
    alerts = state.setdefault("alerts", {})
    existing = alerts.get(event_key)
    if not existing:
        return True
    last = datetime.fromisoformat(existing["sent_at"].replace("Z", "+00:00"))
    age_minutes = (datetime.now(timezone.utc) - last).total_seconds() / 60
    return age_minutes >= dedupe_minutes


def mark_alert_sent(state: dict[str, Any], event_key: str) -> None:
    state.setdefault("alerts", {})[event_key] = {"sent_at": _now_iso()}


def should_send_daily_summary(state: dict[str, Any]) -> bool:
    today = datetime.now(timezone.utc).date().isoformat()
    daily = state.setdefault("daily_summary", {})
    return daily.get("last_sent_date") != today


def mark_daily_summary_sent(state: dict[str, Any]) -> None:
    state.setdefault("daily_summary", {})["last_sent_date"] = datetime.now(timezone.utc).date().isoformat()


def _price_line(price_usdt: float | None, usd_thb_rate: float) -> str:
    price = price_usdt or 0
    return f"\u0e23\u0e32\u0e04\u0e32: {price * usd_thb_rate:,.2f} THB / {price:,.4f} USDT"


def _append_entry_targets(lines: list[str], plan: dict[str, Any]) -> None:
    if plan.get("buy_zone_usdt") is not None:
        lines.append(f"Buy Zone: {plan['buy_zone_usdt']:,.4f} USDT")
    lines.append(f"TP50: {plan['tp50_usdt']} USDT")
    lines.append(f"TP100: {plan['tp100_usdt']} USDT")


def _score_lines(label: str, value: Any, thai: str, suffix: str = "") -> list[str]:
    display = "-" if value is None else f"{value}{suffix}"
    return [f"{label}: {display}", f"({thai})"]


def _why_not_entry_lines(blockers: list[Any] | None) -> list[str]:
    return ["Why Not Entry:", *format_reason_lines(blockers)]


def _append_position_targets(lines: list[str], plan: dict[str, Any]) -> None:
    lines.append(f"Average Cost: {plan['average_cost_usdt']:,.4f} USDT / {plan['average_cost_thb']:,.2f} THB")
    lines.append(
        "Unrealized PNL: "
        f"{plan['unrealized_pnl_usdt']:,.4f} USDT / {plan['unrealized_pnl_thb']:,.2f} THB "
        f"({plan['unrealized_pnl_percent']}%)"
    )
    lines.append(f"TP50: {plan['tp50_usdt']} USDT / {plan['tp50_thb']} THB")
    lines.append(f"TP100: {plan['tp100_usdt']} USDT / {plan['tp100_thb']} THB")
    lines.append(f"Holding Days: {plan['holding_days']}")


def _normalize_signal_label(signal: Any, entry_result: dict[str, Any]) -> str:
    label = entry_result.get("label", signal.grade)
    if label == "B":
        return "WAIT"
    if label == "A":
        return "ENTRY"
    if label == "C":
        return "DANGER"
    return label


def format_v2_message(
    signal: Any,
    price_thb: float | None,
    price_usdt: float | None,
    data_source: str | None,
    position_state: dict[str, Any],
    action: str,
    profit_state: dict[str, Any] | None = None,
    leg_plan: dict[str, Any] | None = None,
    fx_rate: float | None = None,
    fx_source: str | None = None,
    entry_result: dict[str, Any] | None = None,
    bounce_result: dict[str, Any] | None = None,
    opportunity_result: dict[str, Any] | None = None,
    btc_guard: dict[str, Any] | None = None,
    event: dict[str, Any] | None = None,
    signal_id: str | None = None,
) -> str:
    price_thb = float(price_thb or 0)
    price_usdt = float(price_usdt or 0)
    total_zec = float(position_state.get("total_zec", 0))
    entry_result = entry_result or {}
    bounce_result = bounce_result or {}
    opportunity_result = opportunity_result or {}
    btc_guard = btc_guard or {}
    signal_label = _normalize_signal_label(signal, entry_result)

    if event:
        event_type = event.get("event_type")
        is_rolling_drop = str(event_type).startswith("ROLLING_DROP")
        title = (
            "\u26a0\ufe0f ZEC ROLLING 24H DROP\n(ราคาลงสะสมในรอบ 24 ชั่วโมง)"
            if is_rolling_drop
            else "\u26a0\ufe0f PRICE DROP ALERT"
        )
        lines = [f"Event: {event_type}", f"Price: {price_thb:,.2f} THB / {price_usdt:,.4f} USDT"]
        if signal_id:
            lines.insert(0, f"Signal ID: {signal_id}")
        if is_rolling_drop:
            lines.insert(1, f"({rolling_drop_translation(event_type)})")
        if event.get("high_24h") is not None:
            lines.append(f"24h High: {event['high_24h']:,.2f} THB")
            lines.append(f"Drop From 24h High: {event['drop_from_24h_high_percent']}%")
        lines.extend(_score_lines("Entry Score", entry_result.get("entry_score", "-"), "คะแนนความน่าสนใจในการเข้า"))
        lines.extend(_score_lines("Bounce Probability", bounce_result.get("bounce_probability", "-"), "โอกาสเด้งกลับ", "%"))
        lines.extend(_score_lines("Opportunity Score", opportunity_result.get("opportunity_score", "-"), "ความคุ้มค่าในการเข้า", "%"))
        lines.append(f"BTC Guard: {format_btc_guard(btc_guard.get('status', '-'))}")
        lines.extend(format_action_lines(action))
        lines.extend(_why_not_entry_lines(entry_result.get("blockers", [])))
        return branded_message(title, lines)

    if total_zec <= 0 and signal_label in {"WAIT", "DANGER", "NEAR_ENTRY"}:
        title = "\U0001f7e0 NEAR ENTRY" if signal_label == "NEAR_ENTRY" else "\U0001f7e1 WAIT MODE"
        lines = [
            f"Price: {price_thb:,.2f} THB / {price_usdt:,.4f} USDT",
            f"Data Source: {data_source or '-'}",
            f"FX Rate: {fx_rate or '-'}",
            f"FX Source: {fx_source or '-'}",
            f"Signal: {signal_label}",
        ]
        lines.extend(_score_lines("Entry Score", entry_result.get("entry_score", "-"), "คะแนนความน่าสนใจในการเข้า"))
        lines.extend(_score_lines("Bounce Probability", bounce_result.get("bounce_probability", "-"), "โอกาสเด้งกลับ", "%"))
        lines.extend(_score_lines("Opportunity Score", opportunity_result.get("opportunity_score", "-"), "ความคุ้มค่าในการเข้า", "%"))
        lines.extend(
            [
                f"BTC Guard: {format_btc_guard(btc_guard.get('status', '-'))}",
                f"BTC 24h: {btc_guard.get('change_24h', '-')}",
                f"BTC 7d: {btc_guard.get('change_7d', '-')}",
            ]
        )
        lines.extend(format_action_lines(action))
        lines.extend(_why_not_entry_lines(entry_result.get("blockers", [])))
        lines.append(f"Risk: {' + '.join(signal.risk_flags) if signal.risk_flags else '-'}")
        return branded_message(title, lines)

    if total_zec <= 0 and signal_label in {"ENTRY", "STRONG_ENTRY", "SS_PLUS"}:
        entry = price_thb
        title = (
            "\U0001f6a8 SS+ RARE SETUP\n(สัญญาณพิเศษระดับสูง)"
            if signal_label == "SS_PLUS"
            else "\U0001f525 ENTRY SIGNAL"
        )
        action = "STRONG BUY" if signal_label == "SS_PLUS" else "BUY LEG1"
        lines = [
            f"Signal: {signal_label}",
            f"Signal ID: {signal_id}" if signal_id else "Signal ID: -",
            *format_action_lines(action),
            f"Entry Price: {entry:,.2f} THB / {price_usdt:,.4f} USDT",
            f"Data Source: {data_source or '-'}",
            f"FX Rate: {fx_rate or '-'}",
            f"FX Source: {fx_source or '-'}",
            f"TP50: {entry * 1.05:,.2f} THB",
            "กำไรประมาณ +5%",
            f"TP100: {entry * 1.10:,.2f} THB",
            "กำไรประมาณ +10%",
            f"TP3: {entry * 1.15:,.2f} THB",
            "กำไรประมาณ +15%",
        ]
        lines.extend(_score_lines("Entry Score", entry_result.get("entry_score", "-"), "คะแนนความน่าสนใจในการเข้า"))
        lines.extend(_score_lines("Bounce Probability", bounce_result.get("bounce_probability", "-"), "โอกาสเด้งกลับ", "%"))
        lines.extend(_score_lines("Opportunity Score", opportunity_result.get("opportunity_score", "-"), "ความคุ้มค่าในการเข้า", "%"))
        lines.extend(
            [
                f"BTC Guard: {format_btc_guard(btc_guard.get('status', '-'))}",
                f"Confidence: {signal.confidence}%",
                confidence_text(signal.confidence),
                f"Reason: {' + '.join(entry_result.get('reasons', signal.reasons))}",
                f"Risk: {' + '.join(signal.risk_flags) if signal.risk_flags else '-'}",
                "Note: Very strong historical-style setup, not a guaranteed bounce." if signal_label == "SS_PLUS" else "Manual confirmation required. No auto trading.",
            ]
        )
        return branded_message(title, lines)

    if leg_plan and leg_plan.get("can_buy") and signal.grade == "A":
        return branded_message(
            "\U0001f525 LEG PLAN",
            [
                f"Action: BUY {leg_plan['next_leg_id']}",
                f"Suggested Buy: {leg_plan['suggested_buy_price_thb']:,.2f} THB / {leg_plan['suggested_buy_price_usdt']:,.4f} USDT",
                f"FX Rate: {fx_rate or '-'}",
                f"FX Source: {fx_source or '-'}",
                f"Suggested ZEC: {leg_plan['suggested_zec']}",
                f"New Average Cost: {leg_plan['new_average_cost_thb']:,.2f} THB",
                f"New TP50: {leg_plan['new_tp50']:,.2f} THB",
                f"New TP100: {leg_plan['new_tp100']:,.2f} THB",
                f"Cash After Buy: {leg_plan['cash_after_buy']:,.2f} THB",
                f"Reason: {leg_plan['reason']}",
            ],
        )

    profit_state = profit_state or {}
    return branded_message(
        "\U0001f4ca POSITION UPDATE",
        [
            f"Total ZEC: {profit_state.get('total_zec', total_zec)}",
            f"Total Cost: {profit_state.get('total_cost_thb', 0):,.2f} THB",
            f"Average Cost: {profit_state.get('average_cost_thb', 0):,.2f} THB",
            f"Current Price: {price_thb:,.2f} THB / {price_usdt:,.4f} USDT",
            f"Data Source: {data_source or '-'}",
            f"FX Rate: {fx_rate or '-'}",
            f"FX Source: {fx_source or '-'}",
            f"Entry Score: {entry_result.get('entry_score', '-')}",
            f"Bounce Probability: {bounce_result.get('bounce_probability', '-')}",
            f"Opportunity Score: {opportunity_result.get('opportunity_score', '-')}",
            f"BTC Guard: {btc_guard.get('status', '-')}",
            f"Unrealized PNL: {profit_state.get('unrealized_pnl_thb', 0):,.2f} THB ({profit_state.get('unrealized_pnl_percent', 0)}%)",
            f"TP50: {profit_state.get('tp50_price', 0):,.2f} THB",
            f"TP100: {profit_state.get('tp100_price', 0):,.2f} THB",
            f"TP3: {profit_state.get('tp3_price', 0):,.2f} THB",
            f"Amount to sell at TP50: {profit_state.get('amount_to_sell_50_percent', 0)} ZEC",
            f"Holding Days: {profit_state.get('holding_days', 0)}",
            f"Action: {action}",
        ],
    )


def format_signal_message(
    signal: Any,
    price_usdt: float | None,
    usd_thb_rate: float,
    plan: dict[str, Any] | None,
    error: str | None = None,
    tried_sources: list[str] | None = None,
    final_error: str | None = None,
    data_source_used: str | None = None,
    fx_rate: float | None = None,
    fx_source: str | None = None,
) -> str:
    if error:
        return branded_message(
            "\u274c ERROR",
            [
                "Reason:",
                f"สาเหตุ: {final_error or error}",
                f"tried_sources: {', '.join(tried_sources or []) or '-'}",
                f"final_error: {final_error or error}",
                f"FX Rate: {fx_rate or '-'}",
                f"FX Source: {fx_source or '-'}",
                "Action:",
                f"คำแนะนำ: {NO_ENTRY_ACTION}",
                "Risk:",
                "ความเสี่ยง: data_error",
            ],
        )

    icon = "\U0001f525" if signal.grade == "A" else "\U0001f7e1" if signal.grade == "B" else "\U0001f6a8"
    lines = [f"{icon} ZEC SIGNAL {signal.grade}", _price_line(price_usdt, usd_thb_rate)]
    if data_source_used:
        lines.append(f"Data Source: {data_source_used}")
    if fx_rate:
        lines.append(f"FX Rate: {fx_rate}")
    if fx_source:
        lines.append(f"FX Source: {fx_source}")
    lines.append(f"Action: {NO_ENTRY_ACTION}" if signal.grade == "C" else f"Action: {plan.get('action', signal.action) if plan else signal.action}")

    if plan and plan.get("mode") == "has_position":
        _append_position_targets(lines, plan)
    elif signal.grade == "A" and plan and plan.get("mode") == "no_position":
        _append_entry_targets(lines, plan)
    elif signal.grade == "B" and plan and plan.get("mode") == "no_position":
        lines.append(WAITING_TP_TEXT)

    lines.append(f"Confidence: {signal.confidence}%")
    lines.append(f"Reason: {' + '.join(signal.reasons)}")
    if signal.risk_flags:
        lines.append(f"Risk: {' + '.join(signal.risk_flags)}")
    elif signal.grade == "C":
        lines.append("Risk: unknown_risk")
    return branded_message("ZEC SIGNAL", lines)


def send_telegram_message(token: str, chat_id: str, message: str, dry_run: bool = False) -> bool:
    if dry_run:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print("DRY RUN TELEGRAM MESSAGE:")
        print(message)
        return False
    if not token or not chat_id:
        print("Telegram credentials are missing; skipping send.")
        return False
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": message},
        timeout=15,
    )
    response.raise_for_status()
    return True
