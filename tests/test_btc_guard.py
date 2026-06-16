import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from btc_guard import evaluate_btc_guard
from entry_score_engine import evaluate_entry_score


def test_btc_danger_blocks_entry():
    guard = evaluate_btc_guard({"price_usdt": 60000, "change_24h_percent": -6, "change_7d_percent": -2}, {})
    result = evaluate_entry_score(16000, {"rsi14": 30, "ema20": 16010, "volume_average20": 100, "current_volume": 80, "price_change_24h_percent": -3}, guard)

    assert guard["status"] == "DANGER"
    assert result["label"] == "DANGER"
