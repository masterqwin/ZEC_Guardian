import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from signal_engine import evaluate_signal


def base_indicators(**overrides):
    payload = {
        "rsi14": 34,
        "ema20": 100,
        "ema50": 98,
        "atr14": 3,
        "volume_average20": 1000,
        "price_change_24h_percent": -2,
        "trend_state": "sideways",
    }
    payload.update(overrides)
    return payload


def test_signal_a_requires_complete_data_and_good_btc_guard():
    signal = evaluate_signal(
        zec_price=101,
        zec_volume=850,
        zec_indicators=base_indicators(),
        btc_indicators=base_indicators(rsi14=48, price_change_24h_percent=-1),
    )
    assert signal.grade == "A"
    assert signal.score >= 70


def test_incomplete_data_forces_signal_c():
    indicators = base_indicators(rsi14=None)
    signal = evaluate_signal(
        zec_price=101,
        zec_volume=850,
        zec_indicators=indicators,
        btc_indicators=base_indicators(),
    )
    assert signal.grade == "C"
    assert "incomplete_data" in signal.risk_flags


def test_btc_breakdown_forces_signal_c():
    signal = evaluate_signal(
        zec_price=101,
        zec_volume=850,
        zec_indicators=base_indicators(),
        btc_indicators=base_indicators(rsi14=25, price_change_24h_percent=-7),
    )
    assert signal.grade == "C"
    assert "BTC Guard เสีย" in signal.risk_flags

