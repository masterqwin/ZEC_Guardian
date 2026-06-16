import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from telegram_alert import format_signal_message, format_v2_message


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
    message = format_signal_message(signal("A"), 100, 32.5, plan)
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
    message = format_signal_message(signal("B"), 100, 32.5, plan)
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
    message = format_signal_message(signal("C", ["BTC Guard risk"]), 100, 32.5, plan)
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
    message = format_signal_message(signal("B"), 100, 32.5, plan)
    assert "Average Cost: 90.0000 USDT / 3,285.00 THB" in message
    assert "Unrealized PNL: 10.0000 USDT / 365.00 THB (11.11%)" in message
    assert "TP50: 96.3 USDT / 3514.95 THB" in message
    assert "TP100: 98.1 USDT / 3580.65 THB" in message
    assert "Holding Days: 4" in message


def test_v2_wait_mode_does_not_show_tp_numbers():
    message = format_v2_message(
        signal("B"),
        17000,
        532.7,
        "Kraken",
        {"total_zec": 0, "total_cost_thb": 0, "average_cost_thb": 0, "lots": []},
        "WAIT / NO TRADE",
    )

    assert "TP50" not in message
    assert "TP100" not in message
    assert "Action: WAIT / NO TRADE" in message


def test_v2_position_update_shows_average_cost_and_unrealized_pnl():
    message = format_v2_message(
        signal("B"),
        17600,
        550,
        "Kraken",
        {"total_zec": 1, "total_cost_thb": 16000, "average_cost_thb": 16000, "lots": []},
        "TAKE PROFIT ALL",
        profit_state={
            "total_zec": 1,
            "total_cost_thb": 16000,
            "average_cost_thb": 16000,
            "unrealized_pnl_thb": 1600,
            "unrealized_pnl_percent": 10,
            "tp50_price": 16800,
            "tp100_price": 17600,
            "tp3_price": 18400,
            "amount_to_sell_50_percent": 0.5,
            "holding_days": 2,
        },
    )

    assert "Average Cost: 16,000.00 THB" in message
    assert "Unrealized PNL: 1,600.00 THB (10%)" in message
