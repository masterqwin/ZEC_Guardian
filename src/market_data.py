from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class Candle:
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    candles: list[Candle]
    price_usdt: float
    volume: float


class MarketDataError(RuntimeError):
    pass


def _parse_candle(row: list[Any]) -> Candle:
    return Candle(
        open_time=int(row[0]),
        open=float(row[1]),
        high=float(row[2]),
        low=float(row[3]),
        close=float(row[4]),
        volume=float(row[5]),
        close_time=int(row[6]),
    )


def fetch_klines(base_url: str, symbol: str, interval: str, limit: int) -> MarketSnapshot:
    url = f"{base_url.rstrip('/')}/api/v3/klines"
    try:
        response = requests.get(
            url,
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=15,
        )
        response.raise_for_status()
        rows = response.json()
    except Exception as exc:
        raise MarketDataError(f"Unable to fetch {symbol} market data: {exc}") from exc

    if not isinstance(rows, list) or len(rows) < 50:
        raise MarketDataError(f"Incomplete market data for {symbol}")

    try:
        candles = [_parse_candle(row) for row in rows]
    except Exception as exc:
        raise MarketDataError(f"Malformed market data for {symbol}: {exc}") from exc

    latest = candles[-1]
    return MarketSnapshot(
        symbol=symbol,
        candles=candles,
        price_usdt=latest.close,
        volume=latest.volume,
    )


def fetch_market_pair(config: Any) -> tuple[MarketSnapshot, MarketSnapshot]:
    zec = fetch_klines(config.binance_base_url, config.zec_symbol, config.interval, config.kline_limit)
    btc = fetch_klines(config.binance_base_url, config.btc_symbol, config.interval, config.kline_limit)
    return zec, btc

