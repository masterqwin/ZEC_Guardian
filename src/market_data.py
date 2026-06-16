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
    source: str
    price_thb: float | None = None
    change_24h_percent: float | None = None
    change_7d_percent: float | None = None
    market_cap: float | None = None
    rank: int | None = None


@dataclass(frozen=True)
class MarketPair:
    zec: MarketSnapshot
    btc: MarketSnapshot
    data_source_used: str
    tried_sources: list[str]


class MarketDataError(RuntimeError):
    def __init__(self, message: str, tried_sources: list[str] | None = None, final_error: str | None = None):
        super().__init__(message)
        self.tried_sources = tried_sources or []
        self.final_error = final_error or message


def _validate_candles(source: str, symbol: str, candles: list[Candle]) -> MarketSnapshot:
    if len(candles) < 50:
        raise MarketDataError(f"Incomplete market data from {source} for {symbol}: {len(candles)} candles")
    latest = candles[-1]
    return MarketSnapshot(
        symbol=symbol,
        candles=candles,
        price_usdt=latest.close,
        volume=latest.volume,
        source=source,
    )


def _with_market_meta(snapshot: MarketSnapshot, meta: dict[str, Any]) -> MarketSnapshot:
    return MarketSnapshot(
        symbol=snapshot.symbol,
        candles=snapshot.candles,
        price_usdt=float(meta.get("current_price_usd") or snapshot.price_usdt),
        volume=float(meta.get("total_volume") or snapshot.volume),
        source=snapshot.source,
        price_thb=float(meta["current_price_thb"]) if meta.get("current_price_thb") is not None else None,
        change_24h_percent=meta.get("price_change_percentage_24h"),
        change_7d_percent=meta.get("price_change_percentage_7d_in_currency"),
        market_cap=meta.get("market_cap"),
        rank=meta.get("market_cap_rank"),
    )


def _parse_binance_candle(row: list[Any]) -> Candle:
    return Candle(
        open_time=int(row[0]),
        open=float(row[1]),
        high=float(row[2]),
        low=float(row[3]),
        close=float(row[4]),
        volume=float(row[5]),
        close_time=int(row[6]),
    )


def _fetch_binance_klines(base_url: str, symbol: str, interval: str, limit: int) -> MarketSnapshot:
    url = f"{base_url.rstrip('/')}/api/v3/klines"
    response = requests.get(
        url,
        params={"symbol": symbol, "interval": interval, "limit": limit},
        timeout=15,
    )
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list):
        raise MarketDataError(f"Malformed Binance response for {symbol}")
    candles = [_parse_binance_candle(row) for row in rows]
    return _validate_candles("Binance", symbol, candles)


def fetch_klines(base_url: str, symbol: str, interval: str, limit: int) -> MarketSnapshot:
    try:
        return _fetch_binance_klines(base_url, symbol, interval, limit)
    except Exception as exc:
        raise MarketDataError(f"Unable to fetch {symbol} market data from Binance: {exc}") from exc


def _kraken_pair(symbol: str) -> str:
    mapping = {
        "ZECUSDT": "ZECUSD",
        "ZECUSD": "ZECUSD",
        "BTCUSDT": "XBTUSD",
        "BTCUSD": "XBTUSD",
    }
    return mapping.get(symbol.upper(), symbol.upper().replace("USDT", "USD"))


def _interval_to_kraken_minutes(interval: str) -> int:
    mapping = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}
    return mapping.get(interval, 60)


def _parse_kraken_candle(row: list[Any], interval_minutes: int) -> Candle:
    open_time = int(float(row[0]) * 1000)
    return Candle(
        open_time=open_time,
        open=float(row[1]),
        high=float(row[2]),
        low=float(row[3]),
        close=float(row[4]),
        volume=float(row[6]),
        close_time=open_time + (interval_minutes * 60 * 1000) - 1,
    )


def _fetch_kraken_ohlc(symbol: str, interval: str, limit: int) -> MarketSnapshot:
    pair = _kraken_pair(symbol)
    interval_minutes = _interval_to_kraken_minutes(interval)
    response = requests.get(
        "https://api.kraken.com/0/public/OHLC",
        params={"pair": pair, "interval": interval_minutes},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    errors = payload.get("error") or []
    if errors:
        raise MarketDataError(f"Kraken returned errors for {symbol}: {', '.join(errors)}")
    result = payload.get("result") or {}
    rows = next((value for key, value in result.items() if key != "last"), None)
    if not isinstance(rows, list):
        raise MarketDataError(f"Malformed Kraken response for {symbol}")
    candles = [_parse_kraken_candle(row, interval_minutes) for row in rows[-limit:]]
    return _validate_candles("Kraken", symbol, candles)


def _coingecko_id(symbol: str) -> str:
    mapping = {
        "ZECUSDT": "zcash",
        "ZECUSD": "zcash",
        "BTCUSDT": "bitcoin",
        "BTCUSD": "bitcoin",
    }
    if symbol.upper() not in mapping:
        raise MarketDataError(f"No CoinGecko mapping for {symbol}")
    return mapping[symbol.upper()]


def _coingecko_days(limit: int) -> int:
    return max(3, min(30, int((limit / 24) + 2)))


def _fetch_coingecko_market_chart(symbol: str, limit: int) -> MarketSnapshot:
    coin_id = _coingecko_id(symbol)
    response = requests.get(
        f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
        params={"vs_currency": "usd", "days": _coingecko_days(limit), "interval": "hourly"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    prices = payload.get("prices") or []
    volumes = payload.get("total_volumes") or []
    if not isinstance(prices, list) or not isinstance(volumes, list):
        raise MarketDataError(f"Malformed CoinGecko response for {symbol}")

    candles: list[Candle] = []
    last_close: float | None = None
    price_points = prices[-limit:]
    volume_points = volumes[-limit:]
    for index, price_row in enumerate(price_points):
        open_time = int(price_row[0])
        close = float(price_row[1])
        open_price = last_close if last_close is not None else close
        volume = float(volume_points[index][1]) if index < len(volume_points) else 0.0
        candles.append(
            Candle(
                open_time=open_time,
                open=open_price,
                high=max(open_price, close),
                low=min(open_price, close),
                close=close,
                volume=volume,
                close_time=open_time + (60 * 60 * 1000) - 1,
            )
        )
        last_close = close
    return _validate_candles("CoinGecko", symbol, candles)


def _fetch_coingecko_markets() -> dict[str, dict[str, Any]]:
    response = requests.get(
        "https://api.coingecko.com/api/v3/coins/markets",
        params={
            "vs_currency": "thb",
            "ids": "zcash,bitcoin",
            "price_change_percentage": "24h,7d",
        },
        timeout=20,
    )
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list):
        raise MarketDataError("Malformed CoinGecko markets response")
    thb_rows = {row["id"]: row for row in rows}

    response_usd = requests.get(
        "https://api.coingecko.com/api/v3/coins/markets",
        params={"vs_currency": "usd", "ids": "zcash,bitcoin", "price_change_percentage": "24h,7d"},
        timeout=20,
    )
    response_usd.raise_for_status()
    usd_rows = {row["id"]: row for row in response_usd.json()}
    result: dict[str, dict[str, Any]] = {}
    for coin_id in ["zcash", "bitcoin"]:
        thb = thb_rows.get(coin_id) or {}
        usd = usd_rows.get(coin_id) or {}
        result[coin_id] = {
            "current_price_thb": thb.get("current_price"),
            "current_price_usd": usd.get("current_price"),
            "total_volume": thb.get("total_volume"),
            "price_change_percentage_24h": thb.get("price_change_percentage_24h"),
            "price_change_percentage_7d_in_currency": thb.get("price_change_percentage_7d_in_currency"),
            "market_cap": thb.get("market_cap"),
            "market_cap_rank": thb.get("market_cap_rank"),
        }
    return result


def _fetch_coingecko_pair(config: Any) -> tuple[MarketSnapshot, MarketSnapshot]:
    markets = _fetch_coingecko_markets()
    zec = _with_market_meta(_fetch_coingecko_market_chart(config.zec_symbol, config.kline_limit), markets["zcash"])
    btc = _with_market_meta(_fetch_coingecko_market_chart(config.btc_symbol, config.kline_limit), markets["bitcoin"])
    return zec, btc


def _fetch_pair_from_source(source: str, config: Any) -> tuple[MarketSnapshot, MarketSnapshot]:
    if source == "Binance":
        return (
            _fetch_binance_klines(config.binance_base_url, config.zec_symbol, config.interval, config.kline_limit),
            _fetch_binance_klines(config.binance_base_url, config.btc_symbol, config.interval, config.kline_limit),
        )
    if source == "Kraken":
        return (
            _fetch_kraken_ohlc(config.zec_symbol, config.interval, config.kline_limit),
            _fetch_kraken_ohlc(config.btc_symbol, config.interval, config.kline_limit),
        )
    if source == "CoinGecko":
        return _fetch_coingecko_pair(config)
    raise MarketDataError(f"Unknown market data source: {source}")


def fetch_market_pair(config: Any) -> MarketPair:
    tried_sources: list[str] = []
    errors: list[str] = []
    for source in ["CoinGecko", "Kraken", "Binance"]:
        tried_sources.append(source)
        try:
            zec, btc = _fetch_pair_from_source(source, config)
            return MarketPair(zec=zec, btc=btc, data_source_used=source, tried_sources=tried_sources)
        except Exception as exc:
            errors.append(f"{source}: {exc}")

    final_error = errors[-1] if errors else "No market data source was attempted"
    raise MarketDataError(
        "Unable to fetch complete ZEC/BTC market data from all sources",
        tried_sources=tried_sources,
        final_error=final_error,
    )
