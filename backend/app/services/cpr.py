from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CPRResult:
    pivot: float
    bottom_central: float
    top_central: float
    width: float
    width_percent: float
    classification: str
    position: str


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_cpr(
    *,
    previous_high: float,
    previous_low: float,
    previous_close: float,
    current_price: float,
) -> CPRResult:
    high = safe_float(previous_high)
    low = safe_float(previous_low)
    close = safe_float(previous_close)
    price = safe_float(current_price)

    if high <= 0 or low <= 0 or close <= 0:
        raise ValueError(
            "Previous high, low and close must be positive"
        )

    if high < low:
        raise ValueError(
            "Previous high cannot be lower than previous low"
        )

    pivot = (high + low + close) / 3
    bottom_central = (high + low) / 2
    top_central = (2 * pivot) - bottom_central

    lower_cpr = min(
        bottom_central,
        top_central,
    )

    upper_cpr = max(
        bottom_central,
        top_central,
    )

    width = upper_cpr - lower_cpr

    width_percent = (
        width / pivot * 100
        if pivot > 0
        else 0.0
    )

    if width_percent <= 0.25:
        classification = "NARROW"
    elif width_percent <= 0.50:
        classification = "MODERATE"
    else:
        classification = "WIDE"

    if price > upper_cpr:
        position = "ABOVE CPR"
    elif price < lower_cpr:
        position = "BELOW CPR"
    else:
        position = "INSIDE CPR"

    return CPRResult(
        pivot=round(pivot, 2),
        bottom_central=round(
            lower_cpr,
            2,
        ),
        top_central=round(
            upper_cpr,
            2,
        ),
        width=round(width, 2),
        width_percent=round(
            width_percent,
            3,
        ),
        classification=classification,
        position=position,
    )