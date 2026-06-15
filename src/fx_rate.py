from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class FxRate:
    rate: float
    source: str


def convert_usdt_to_thb(amount_usdt: float, fx_rate: float) -> float:
    return round(float(amount_usdt) * float(fx_rate), 2)


def fetch_usd_thb_rate(config: Any) -> FxRate:
    configured_rate = float(getattr(config, "usd_thb_rate", 32.5))
    try:
        response = requests.get(getattr(config, "fx_api_url", "https://open.er-api.com/v6/latest/USD"), timeout=10)
        response.raise_for_status()
        payload = response.json()
        rate = float(payload.get("rates", {}).get("THB", 0))
        if rate <= 0:
            raise ValueError("THB rate missing from FX response")
        return FxRate(rate=rate, source="open.er-api.com")
    except Exception:
        return FxRate(rate=configured_rate, source="config_fallback")
