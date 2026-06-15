from __future__ import annotations

import os
from dataclasses import dataclass


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    binance_base_url: str = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")
    zec_symbol: str = os.getenv("ZEC_SYMBOL", "ZECUSDT")
    btc_symbol: str = os.getenv("BTC_SYMBOL", "BTCUSDT")
    interval: str = os.getenv("KLINE_INTERVAL", "1h")
    kline_limit: int = int(_float_env("KLINE_LIMIT", 250))
    usd_thb_rate: float = _float_env("USD_THB_RATE", 32.5)
    fx_api_url: str = os.getenv("FX_API_URL", "https://open.er-api.com/v6/latest/USD")
    capital_thb: float = _float_env("CAPITAL_THB", 50000)
    reserve_percent: float = _float_env("RESERVE_PERCENT", 25)
    zec_per_leg: float = _float_env("ZEC_PER_LEG", 1)
    first_leg_tp50_percent: float = _float_env("FIRST_LEG_TP50_PERCENT", 5)
    first_leg_tp100_percent: float = _float_env("FIRST_LEG_TP100_PERCENT", 7)
    second_leg_tp50_percent: float = _float_env("SECOND_LEG_TP50_PERCENT", 7)
    second_leg_tp100_percent: float = _float_env("SECOND_LEG_TP100_PERCENT", 9)
    third_leg_tp50_percent: float = _float_env("THIRD_LEG_TP50_PERCENT", 9)
    third_leg_tp100_percent: float = _float_env("THIRD_LEG_TP100_PERCENT", 11)
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    dry_run: bool = os.getenv("ZEC_GUARDIAN_DRY_RUN", "0") in {"1", "true", "TRUE", "yes"}
    data_dir: str = os.getenv("DATA_DIR", "data")


def load_config() -> Config:
    return Config()
