from __future__ import annotations

from typing import Any


MAJOR_DROP_EVENTS = {"PRICE_DROP_5", "PRICE_DROP_7", "PRICE_DROP_10"}


def detect_events(current_price: float, state: dict[str, Any], entry_score: int, signal_label: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
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
    if event.get("event_type") in MAJOR_DROP_EVENTS or event.get("event_type", "").endswith("_REACHED"):
        return True
    return event.get("event_type") not in state.get("alerts", {})
