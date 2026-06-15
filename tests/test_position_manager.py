import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from position_manager import buy_lot, default_state, sell_all, sell_percent


def test_average_cost_after_partial_sell_and_new_buy():
    state = default_state()
    state, _ = buy_lot(state, 1, 17000, 532.7, timestamp="2026-06-16T00:00:00+00:00")
    state, _ = sell_percent(state, 50, 17850, 560.0, timestamp="2026-06-16T01:00:00+00:00")
    state, _ = buy_lot(state, 1, 16000, 500.0, timestamp="2026-06-16T02:00:00+00:00")

    assert state["position"]["lots"][0]["remaining_zec"] == 0.5
    assert state["position"]["total_zec"] == 1.5
    assert state["position"]["total_cost_thb"] == 24500
    assert state["position"]["average_cost_thb"] == 16333.33


def test_sell_percent_reduces_remaining_zec():
    state = default_state()
    state, _ = buy_lot(state, 1, 17000, 532.7)
    state, trade = sell_percent(state, 50, 17850, 560.0)

    assert trade["zec_sold"] == 0.5
    assert state["position"]["total_zec"] == 0.5


def test_sell_all_resets_position_to_wait():
    state = default_state()
    state, _ = buy_lot(state, 1, 17000, 532.7)
    state, _ = sell_all(state, 18200, 570.0)

    assert state["position"]["total_zec"] == 0
    assert state["position"]["total_cost_thb"] == 0
    assert state["position"]["average_cost_thb"] == 0
    assert state["mode"] == "WAIT"
