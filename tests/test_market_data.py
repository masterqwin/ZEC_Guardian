import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from market_data import MarketDataError, fetch_market_pair
from signal_engine import evaluate_signal


class FakeResponse:
    def __init__(self, payload, status_code=200, reason="OK"):
        self.payload = payload
        self.status_code = status_code
        self.reason = reason

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Client Error: {self.reason}")

    def json(self):
        return self.payload


def config():
    return SimpleNamespace(
        binance_base_url="https://api.binance.com",
        zec_symbol="ZECUSDT",
        btc_symbol="BTCUSDT",
        interval="1h",
        kline_limit=60,
    )


def kraken_payload(close_start=100):
    rows = []
    for index in range(60):
        close = close_start + index
        rows.append([1700000000 + (index * 3600), close - 1, close + 2, close - 3, close, close, 1000 + index, 10])
    return {"error": [], "result": {"PAIR": rows, "last": "1"}}


def test_binance_451_falls_back_to_kraken(monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=15):
        calls.append(url)
        if "api.binance.com" in url:
            return FakeResponse({"msg": "restricted"}, status_code=451, reason="Unavailable For Legal Reasons")
        return FakeResponse(kraken_payload())

    monkeypatch.setattr("market_data.requests.get", fake_get)

    pair = fetch_market_pair(config())

    assert pair.data_source_used == "Kraken"
    assert pair.tried_sources == ["Binance", "Kraken"]
    assert pair.zec.source == "Kraken"
    assert pair.btc.source == "Kraken"


def test_all_sources_fail_returns_market_data_error(monkeypatch):
    def fake_get(url, params=None, timeout=15):
        return FakeResponse({"error": ["forced failure"]}, status_code=500, reason="Server Error")

    monkeypatch.setattr("market_data.requests.get", fake_get)

    with pytest.raises(MarketDataError) as exc_info:
        fetch_market_pair(config())

    assert exc_info.value.tried_sources == ["Binance", "Kraken", "CoinGecko"]
    assert "CoinGecko" in exc_info.value.final_error


def test_incomplete_data_cannot_be_signal_a():
    signal = evaluate_signal(
        zec_price=100,
        zec_volume=100,
        zec_indicators={"rsi14": 30},
        btc_indicators={"rsi14": 45},
    )

    assert signal.grade == "C"
    assert signal.grade != "A"
    assert "incomplete_data" in signal.risk_flags
