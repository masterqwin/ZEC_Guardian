import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from portfolio import average_cost_usdt, build_trade_plan


def config():
    return SimpleNamespace(
        usd_thb_rate=32.5,
        capital_thb=50000,
        reserve_percent=25,
        zec_per_leg=1,
        first_leg_tp50_percent=5,
        first_leg_tp100_percent=7,
        second_leg_tp50_percent=7,
        second_leg_tp100_percent=9,
        third_leg_tp50_percent=9,
        third_leg_tp100_percent=11,
    )


def test_no_position_builds_first_leg_plan():
    state = {"position": {"legs": [], "closed_quantity_zec": 0}}
    plan = build_trade_plan(state, "A", 100, config())
    assert plan["mode"] == "no_position"
    assert plan["action"] == "เข้าไม้ 1"
    assert plan["tp50_usdt"] == 105
    assert plan["tp100_usdt"] == 107


def test_average_cost_uses_weighted_quantity():
    legs = [
        {"quantity_zec": 1, "entry_price_usdt": 100},
        {"quantity_zec": 2, "entry_price_usdt": 70},
    ]
    assert round(average_cost_usdt(legs), 4) == 80


def test_signal_a_after_pullback_suggests_second_leg():
    state = {
        "position": {
            "legs": [
                {
                    "leg": 1,
                    "quantity_zec": 1,
                    "entry_price_usdt": 100,
                    "opened_at": "2026-06-01T00:00:00+00:00",
                    "status": "open",
                }
            ],
            "closed_quantity_zec": 0,
        }
    }
    plan = build_trade_plan(state, "A", 90, config())
    assert plan["action"] == "แนะนำไม้ 2"
    assert plan["next_average_cost_usdt"] == 95
