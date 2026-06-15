import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fx_rate import convert_usdt_to_thb


def test_usdt_to_thb_uses_fallback_rate_32_5():
    assert convert_usdt_to_thb(527.2, 32.5) == 17134.0
