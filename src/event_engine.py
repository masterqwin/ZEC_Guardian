from __future__ import annotations

from typing import Any


MAJOR_DROP_EVENTS = {"PRICE_DROP_5", "PRICE_DROP_7", "PRICE_DROP_10", "ROLLING_DROP_5", "ROLLING_DROP_7", "ROLLING_DROP_10"}
ROLLING_DROP_EVENTS = {"ROLLING_DROP_3", "ROLLING_DROP_5", "ROLLING_DROP_7", "ROLLING_DROP_10"}


def detect_rolling_drop(current_price: float, high_24h: float | None) -> dict[str, Any] | None:
    if not high_24h or high_24h <= 0:
        return None
    drop = ((current_price - high_24h) / high_24h) * 100
    if drop <= -10:
        event_type = "ROLLING_DROP_10"
    elif drop <= -7:
        event_type = "ROLLING_DROP_7"
    elif drop <= -5:
        event_type = "ROLLING_DROP_5"
    elif drop <= -3:
        event_type = "ROLLING_DROP_3"
    else:
        return None
    return {
        "event_type": event_type,
        "priority": "HIGH" if event_type != "ROLLING_DROP_3" else "MEDIUM",
        "high_24h": round(high_24h, 2),
        "drop_from_24h_high_percent": round(drop, 2),
    }


def detect_events(current_price: float, state: dict[str, Any], entry_score: int, signal_label: str, high_24h: float | None = None) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    rolling = detect_rolling_drop(current_price, high_24h)
    if rolling:
        events.append(rolling)
    alerts = state.setdefault("alerts", {})
    reference = alerts.get("last_reference_price_thb") or alerts.get("last_alert_price_thb") or current_price
    drop = ((current_price - float(reference)) / float(reference)) * 100 if reference else 0
    if drop <= -10:
        events.append({"event_type": "PRICE_DROP_10", "priority": "HIGH", "price_change_percent": round(drop, 2)})
    elif drop <= -7:
        events.append({"event_type": "PRICE_DROP_7", "priority": "HIGH", "price_change_percent": round(drop, 2)})
    elif drop <= -5:
        events.append({"event_type": "PRICE_DROP_5", "priority": "HIGH", "price_change_percent": round(drop, 2)})
    elif drop <= -3:
        events.append({"event_type": "PRICE_DROP_3", "priority": "MEDIUM", "price_change_percent": round(drop, 2)})

    thresholds = [(97, "SS_PLUS_REACHED"), (95, "STRONG_ENTRY_REACHED"), (85, "ENTRY_REACHED"), (70, "NEAR_ENTRY_REACHED")]
    last_score = int(alerts.get("last_entry_score", 0))
    for threshold, name in thresholds:
        if entry_score >= threshold > last_score:
            events.append({"event_type": name, "priority": "HIGH" if threshold >= 85 else "MEDIUM", "threshold": threshold})
            break
    if signal_label in {"ENTRY", "STRONG_ENTRY", "SS_PLUS"}:
        entry_price = alerts.get("last_entry_signal_price_thb")
        if entry_price and current_price >= float(entry_price) * 1.05:
            events.append({"event_type": "FOMO_WARNING", "priority": "HIGH", "fomo_score": 90})
    return events


def should_send_event(event: dict[str, Any], state: dict[str, Any]) -> bool:
    event_type = event.get("event_type")
    if event_type in MAJOR_DROP_EVENTS or str(event_type).endswith("_REACHED"):
        return True
    if event_type in ROLLING_DROP_EVENTS:
        last = state.get("alerts", {}).get("last_rolling_drop_event")
        order = {"ROLLING_DROP_3": 3, "ROLLING_DROP_5": 5, "ROLLING_DROP_7": 7, "ROLLING_DROP_10": 10}
        return order.get(event_type, 0) > order.get(last, 0)
    return event_type not in state.get("alerts", {})
