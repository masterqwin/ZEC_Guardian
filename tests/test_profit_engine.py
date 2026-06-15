import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from position_manager import buy_lot, default_state
from profit_engine import calculate_profit_state


def test_profit_engine_targets_and_pnl():
    state = default_state()
    state, _ = buy_lot(state, 1, 16000, 500.0)
    profit = calculate_profit_state(state, 17600)

    assert profit["average_cost_thb"] == 16000
    assert profit["unrealized_pnl_percent"] == 10
    assert profit["tp50_price"] == 16800
    assert profit["tp100_price"] == 17600
