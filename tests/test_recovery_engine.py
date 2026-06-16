import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from recovery_engine import estimate_recovery


def test_recovery_engine_uses_position_tp50_reference():
    result = estimate_recovery({"total_zec": 1}, {"tp50_price": 16800})
    assert result["target_reference"] == "TP50"
    assert result["target_price_thb"] == 16800
