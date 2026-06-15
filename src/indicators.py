from __future__ import annotations

from statistics import mean

from market_data import Candle


def ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    multiplier = 2 / (period + 1)
    current = mean(values[:period])
    for value in values[period:]:
        current = (value - current) * multiplier + current
    return current


def rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, period + 1):
        change = values[index] - values[index - 1]
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))

    avg_gain = mean(gains)
    avg_loss = mean(losses)
    for index in range(period + 1, len(values)):
        change = values[index] - values[index - 1]
        gain = max(change, 0)
        loss = abs(min(change, 0))
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(candles: list[Candle], period: int = 14) -> float | None:
    if len(candles) <= period:
        return None
    true_ranges = []
    for index in range(1, len(candles)):
        candle = candles[index]
        prev_close = candles[index - 1].close
        true_ranges.append(
            max(
                candle.high - candle.low,
                abs(candle.high - prev_close),
                abs(candle.low - prev_close),
            )
        )
    if len(true_ranges) < period:
        return None
    return mean(true_ranges[-period:])


def price_change_percent(values: list[float], lookback: int = 24) -> float | None:
    if len(values) <= lookback or values[-lookback - 1] == 0:
        return None
    return ((values[-1] - values[-lookback - 1]) / values[-lookback - 1]) * 100


def volume_average(candles: list[Candle], period: int = 20) -> float | None:
    if len(candles) < period:
        return None
    return mean([c.volume for c in candles[-period:]])


def trend_state(close: float, ema20: float | None, ema50: float | None, ema200: float | None) -> str:
    if ema20 is None or ema50 is None:
        return "unknown"
    if ema200 is not None and close > ema20 > ema50 > ema200:
        return "strong_uptrend"
    if close > ema20 > ema50:
        return "uptrend"
    if close < ema20 < ema50:
        return "downtrend"
    return "sideways"


def build_indicators(candles: list[Candle]) -> dict[str, float | str | None]:
    closes = [c.close for c in candles]
    latest_close = closes[-1] if closes else 0
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    ema200 = ema(closes, 200)
    return {
        "rsi14": rsi(closes, 14),
        "ema20": ema20,
        "ema50": ema50,
        "ema200": ema200,
        "atr14": atr(candles, 14),
        "volume_average20": volume_average(candles, 20),
        "price_change_24h_percent": price_change_percent(closes, 24),
        "trend_state": trend_state(latest_close, ema20, ema50, ema200),
    }

