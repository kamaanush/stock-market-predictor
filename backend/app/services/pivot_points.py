from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PivotLevels:
    pivot: float
    resistance1: float
    resistance2: float
    resistance3: float
    support1: float
    support2: float
    support3: float
    position: str
    nearest_level: str
    distance_percent: float


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


def calculate_pivot_levels(
    previous_high: float,
    previous_low: float,
    previous_close: float,
    current_price: float,
) -> PivotLevels:
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

    resistance1 = (2 * pivot) - low
    support1 = (2 * pivot) - high

    resistance2 = pivot + (high - low)
    support2 = pivot - (high - low)

    resistance3 = high + (2 * (pivot - low))
    support3 = low - (2 * (high - pivot))

    levels = {
        "S3": support3,
        "S2": support2,
        "S1": support1,
        "PIVOT": pivot,
        "R1": resistance1,
        "R2": resistance2,
        "R3": resistance3,
    }

    nearest_level = min(
        levels,
        key=lambda name: abs(price - levels[name]),
    )

    nearest_price = levels[nearest_level]

    distance_percent = (
        abs(price - nearest_price) / price * 100
        if price > 0
        else 0.0
    )

    if price > resistance1:
        position = "ABOVE R1"

    elif price > pivot:
        position = "ABOVE PIVOT"

    elif price < support1:
        position = "BELOW S1"

    elif price < pivot:
        position = "BELOW PIVOT"

    else:
        position = "AT PIVOT"

    return PivotLevels(
        pivot=round(pivot, 2),
        resistance1=round(resistance1, 2),
        resistance2=round(resistance2, 2),
        resistance3=round(resistance3, 2),
        support1=round(support1, 2),
        support2=round(support2, 2),
        support3=round(support3, 2),
        position=position,
        nearest_level=nearest_level,
        distance_percent=round(
            distance_percent,
            2,
        ),
    )