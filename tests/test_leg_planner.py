import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from leg_planner import plan_next_leg
from position_manager import buy_lot, default_state


def test_leg_planner_new_average_after_second_buy():
    state = default_state()
    state, _ = buy_lot(state, 0.5, 17000, 532.7)
    plan = plan_next_leg(state, "A", 16000, 500.0)

    assert plan["new_total_zec"] == 1.5
    assert plan["new_total_cost_thb"] == 24500
    assert plan["new_average_cost_thb"] == 16333.33


def test_leg_planner_blocks_reserve_spend():
    state = default_state(capital_thb=50000, reserve_percent=25, zec_per_leg=1)
    state, _ = buy_lot(state, 0.5, 17000, 532.7)
    state["cash_thb"] = 13000
    plan = plan_next_leg(state, "A", 16000, 500.0)

    assert plan["can_buy"] is False
    assert plan["reason"] == "INSUFFICIENT CASH"
