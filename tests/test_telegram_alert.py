import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from telegram_alert import format_signal_message


def signal(grade, risk_flags=None):
    return SimpleNamespace(
        grade=grade,
        action="raw action",
        confidence=70,
        reasons=["reason one"],
        risk_flags=risk_flags or [],
    )


def test_signal_a_without_position_shows_entry_targets():
    plan = {
        "mode": "no_position",
        "action": "entry",
        "buy_zone_usdt": 100,
        "tp50_usdt": 105,
        "tp100_usdt": 107,
    }
    message = format_signal_message(signal("A"), 100, 36.5, plan)
    assert "Buy Zone: 100.0000 USDT" in message
    assert "TP50: 105 USDT" in message
    assert "TP100: 107 USDT" in message


def test_signal_b_without_position_hides_numeric_targets():
    plan = {
        "mode": "no_position",
        "action": "wait",
        "buy_zone_usdt": 100,
        "tp50_usdt": 105,
        "tp100_usdt": 107,
    }
    message = format_signal_message(signal("B"), 100, 36.5, plan)
    assert "TP50/TP100:" in message
    assert "TP50: 105 USDT" not in message
    assert "TP100: 107 USDT" not in message


def test_signal_c_hides_entry_targets_and_shows_risk():
    plan = {
        "mode": "no_position",
        "action": "wait",
        "buy_zone_usdt": 100,
        "tp50_usdt": 105,
        "tp100_usdt": 107,
    }
    message = format_signal_message(signal("C", ["BTC Guard risk"]), 100, 36.5, plan)
    assert "Action: ห้ามเข้า / งดช้อน" in message
    assert "Buy Zone" not in message
    assert "TP50:" not in message
    assert "TP100:" not in message
    assert "Risk: BTC Guard risk" in message


def test_position_message_shows_position_metrics_and_targets():
    plan = {
        "mode": "has_position",
        "action": "hold",
        "average_cost_usdt": 90,
        "average_cost_thb": 3285,
        "unrealized_pnl_usdt": 10,
        "unrealized_pnl_thb": 365,
        "unrealized_pnl_percent": 11.11,
        "tp50_usdt": 96.3,
        "tp50_thb": 3514.95,
        "tp100_usdt": 98.1,
        "tp100_thb": 3580.65,
        "holding_days": 4,
    }
    message = format_signal_message(signal("B"), 100, 36.5, plan)
    assert "Average Cost: 90.0000 USDT / 3,285.00 THB" in message
    assert "Unrealized PNL: 10.0000 USDT / 365.00 THB (11.11%)" in message
    assert "TP50: 96.3 USDT / 3514.95 THB" in message
    assert "TP100: 98.1 USDT / 3580.65 THB" in message
    assert "Holding Days: 4" in message
