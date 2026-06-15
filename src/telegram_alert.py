from __future__ import annotations

from datetime import datetime, timezone
import sys
from typing import Any

import requests


IMPORTANT_GRADES = {"A", "C"}
NO_ENTRY_ACTION = "\u0e2b\u0e49\u0e32\u0e21\u0e40\u0e02\u0e49\u0e32 / \u0e07\u0e14\u0e0a\u0e49\u0e2d\u0e19"
WAITING_TP_TEXT = "TP50/TP100: \u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e04\u0e33\u0e19\u0e27\u0e13\u0e08\u0e19\u0e01\u0e27\u0e48\u0e32\u0e08\u0e30\u0e21\u0e35 Entry Signal A \u0e2b\u0e23\u0e37\u0e2d\u0e21\u0e35 Position \u0e08\u0e23\u0e34\u0e07"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def format_v2_message(
    signal: Any,
    price_thb: float | None,
    price_usdt: float | None,
    data_source: str | None,
    position_state: dict[str, Any],
    action: str,
    profit_state: dict[str, Any] | None = None,
    leg_plan: dict[str, Any] | None = None,
) -> str:
    price_thb = float(price_thb or 0)
    price_usdt = float(price_usdt or 0)
    total_zec = float(position_state.get("total_zec", 0))

    if total_zec <= 0 and signal.grade != "A":
        return "\n".join(
            [
                "\U0001f7e1 ZEC WAIT MODE",
                f"Price: {price_thb:,.2f} THB / {price_usdt:,.4f} USDT",
                f"Data Source: {data_source or '-'}",
                f"Signal: {signal.grade}",
                f"Action: {action}",
                f"Reason: {' + '.join(signal.reasons)}",
                f"Risk: {' + '.join(signal.risk_flags) if signal.risk_flags else '-'}",
            ]
        )

    if total_zec <= 0 and signal.grade == "A":
        entry = price_thb
        return "\n".join(
            [
                "\U0001f525 ZEC ENTRY SIGNAL",
                "Action: BUY LEG1",
                f"Entry Price: {entry:,.2f} THB / {price_usdt:,.4f} USDT",
                f"Data Source: {data_source or '-'}",
                f"TP50: {entry * 1.05:,.2f} THB",
                f"TP100: {entry * 1.10:,.2f} THB",
                f"TP3: {entry * 1.15:,.2f} THB",
                f"Confidence: {signal.confidence}%",
                f"Reason: {' + '.join(signal.reasons)}",
                f"Risk: {' + '.join(signal.risk_flags) if signal.risk_flags else '-'}",
            ]
        )

    if leg_plan and leg_plan.get("can_buy") and signal.grade == "A":
        return "\n".join(
            [
                "\U0001f525 ZEC LEG PLAN",
                f"Action: BUY {leg_plan['next_leg_id']}",
                f"Suggested Buy: {leg_plan['suggested_buy_price_thb']:,.2f} THB / {leg_plan['suggested_buy_price_usdt']:,.4f} USDT",
                f"Suggested ZEC: {leg_plan['suggested_zec']}",
                f"New Average Cost: {leg_plan['new_average_cost_thb']:,.2f} THB",
                f"New TP50: {leg_plan['new_tp50']:,.2f} THB",
                f"New TP100: {leg_plan['new_tp100']:,.2f} THB",
                f"Cash After Buy: {leg_plan['cash_after_buy']:,.2f} THB",
                f"Reason: {leg_plan['reason']}",
            ]
        )

    profit_state = profit_state or {}
    return "\n".join(
        [
            "\U0001f4ca ZEC POSITION UPDATE",
            f"Total ZEC: {profit_state.get('total_zec', total_zec)}",
            f"Total Cost: {profit_state.get('total_cost_thb', 0):,.2f} THB",
            f"Average Cost: {profit_state.get('average_cost_thb', 0):,.2f} THB",
            f"Current Price: {price_thb:,.2f} THB / {price_usdt:,.4f} USDT",
            f"Data Source: {data_source or '-'}",
            f"Unrealized PNL: {profit_state.get('unrealized_pnl_thb', 0):,.2f} THB ({profit_state.get('unrealized_pnl_percent', 0)}%)",
            f"TP50: {profit_state.get('tp50_price', 0):,.2f} THB",
            f"TP100: {profit_state.get('tp100_price', 0):,.2f} THB",
            f"TP3: {profit_state.get('tp3_price', 0):,.2f} THB",
            f"Amount to sell at TP50: {profit_state.get('amount_to_sell_50_percent', 0)} ZEC",
            f"Holding Days: {profit_state.get('holding_days', 0)}",
            f"Action: {action}",
        ]
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
) -> str:
    if error:
        return "\n".join(
            [
                "\u26a0\ufe0f ZEC GUARDIAN ERROR",
                "Status: data fetch failed",
                f"tried_sources: {', '.join(tried_sources or []) or '-'}",
                f"final_error: {final_error or error}",
                f"Action: {NO_ENTRY_ACTION}",
                "Risk: data_error",
            ]
        )

    icon = "\U0001f525" if signal.grade == "A" else "\U0001f7e1" if signal.grade == "B" else "\U0001f6a8"
    lines = [
        f"{icon} ZEC SIGNAL {signal.grade}",
        _price_line(price_usdt, usd_thb_rate),
    ]
    if data_source_used:
        lines.append(f"Data Source: {data_source_used}")

    if signal.grade == "C":
        lines.append(f"Action: {NO_ENTRY_ACTION}")
    else:
        lines.append(f"Action: {plan.get('action', signal.action) if plan else signal.action}")

    if plan and plan.get("mode") == "has_position":
        _append_position_targets(lines, plan)
    elif signal.grade == "A" and plan and plan.get("mode") == "no_position":
        _append_entry_targets(lines, plan)
    elif signal.grade == "B" and plan and plan.get("mode") == "no_position":
        lines.append(WAITING_TP_TEXT)

    lines.extend(
        [
            f"Confidence: {signal.confidence}%",
            f"Reason: {' + '.join(signal.reasons)}",
        ]
    )
    if signal.risk_flags:
        lines.append(f"Risk: {' + '.join(signal.risk_flags)}")
    elif signal.grade == "C":
        lines.append("Risk: unknown_risk")
    return "\n".join(lines)


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
