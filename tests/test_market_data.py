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


def coingecko_markets_payload(vs_currency="thb"):
    if vs_currency == "thb":
        return [
            {"id": "zcash", "current_price": 17134, "total_volume": 1000000, "price_change_percentage_24h": -2, "price_change_percentage_7d_in_currency": -4, "market_cap": 100, "market_cap_rank": 90},
            {"id": "bitcoin", "current_price": 2100000, "total_volume": 2000000, "price_change_percentage_24h": -1, "price_change_percentage_7d_in_currency": 2, "market_cap": 1000, "market_cap_rank": 1},
        ]
    return [
        {"id": "zcash", "current_price": 527.2},
        {"id": "bitcoin", "current_price": 65000},
    ]


def coingecko_chart_payload(close_start=100):
    prices = []
    volumes = []
    for index in range(60):
        prices.append([1700000000000 + (index * 3600000), close_start + index])
        volumes.append([1700000000000 + (index * 3600000), 1000 + index])
    return {"prices": prices, "total_volumes": volumes}


def test_coingecko_direct_thb_price_is_primary(monkeypatch):
    def fake_get(url, params=None, timeout=15):
        if "coins/markets" in url:
            return FakeResponse(coingecko_markets_payload(params.get("vs_currency")))
        if "market_chart" in url:
            return FakeResponse(coingecko_chart_payload())
        return FakeResponse({}, status_code=500, reason="should not use fallback")

    monkeypatch.setattr("market_data.requests.get", fake_get)

    pair = fetch_market_pair(config())

    assert pair.data_source_used == "CoinGecko"
    assert pair.zec.price_thb == 17134
    assert pair.zec.price_usdt == 527.2


def test_coingecko_fail_falls_back_to_kraken(monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=15):
        calls.append(url)
        if "coingecko" in url:
            return FakeResponse({"error": "rate limited"}, status_code=429, reason="Rate Limited")
        return FakeResponse(kraken_payload())

    monkeypatch.setattr("market_data.requests.get", fake_get)

    pair = fetch_market_pair(config())

    assert pair.data_source_used == "Kraken"
    assert pair.tried_sources == ["CoinGecko", "Kraken"]
    assert pair.zec.source == "Kraken"
    assert pair.btc.source == "Kraken"


def test_all_sources_fail_returns_market_data_error(monkeypatch):
    def fake_get(url, params=None, timeout=15):
        return FakeResponse({"error": ["forced failure"]}, status_code=500, reason="Server Error")

    monkeypatch.setattr("market_data.requests.get", fake_get)

    with pytest.raises(MarketDataError) as exc_info:
        fetch_market_pair(config())

    assert exc_info.value.tried_sources == ["CoinGecko", "Kraken", "Binance"]
    assert "Binance" in exc_info.value.final_error


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
