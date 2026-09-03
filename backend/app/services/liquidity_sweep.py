from __future__ import annotations

from statistics import median
from typing import Any


def _safe_float(
    value: Any,
) -> float:

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return 0.0


def _percent(
    value: float,
    base: float,
) -> float:

    if base <= 0:
        return 0.0

    return (
        value
        / base
        * 100.0
    )


def analyze_liquidity_sweep(
    candles: list[
        dict[str, Any]
    ],
    *,
    lookback: int = 8,
) -> dict[str, Any]:
    """
    Detect false breaks of recent
    support/resistance.

    Bullish sweep:
        price trades below support
        but closes back above support.

    Bearish sweep:
        price trades above resistance
        but closes back below resistance.

    This is a market-structure feature,
    not an automatic trade signal.
    """

    minimum = (
        lookback + 1
    )

    if len(candles) < minimum:

        return {
            "available": False,
            "state":
                "INSUFFICIENT_DATA",
            "direction":
                "NEUTRAL",
            "quality": 0.0,
        }

    candles = candles[
        -minimum:
    ]

    previous = candles[
        :-1
    ]

    latest = candles[
        -1
    ]

    previous_high = max(
        _safe_float(
            candle.get(
                "high"
            )
        )
        for candle
        in previous
    )

    previous_low = min(
        _safe_float(
            candle.get(
                "low"
            )
        )
        for candle
        in previous
    )

    if (
        previous_high <= 0
        or previous_low <= 0
    ):

        return {
            "available": False,
            "state":
                "INVALID_LEVELS",
            "direction":
                "NEUTRAL",
            "quality": 0.0,
        }

    open_price = _safe_float(
        latest.get(
            "open"
        )
    )

    high = _safe_float(
        latest.get(
            "high"
        )
    )

    low = _safe_float(
        latest.get(
            "low"
        )
    )

    close = _safe_float(
        latest.get(
            "close"
        )
    )

    volume = _safe_float(
        latest.get(
            "volume"
        )
    )

    candle_range = (
        high - low
    )

    if candle_range <= 0:

        return {
            "available": False,
            "state":
                "ZERO_RANGE",
            "direction":
                "NEUTRAL",
            "quality": 0.0,
        }

    previous_volumes = [
        _safe_float(
            candle.get(
                "volume"
            )
        )
        for candle
        in previous
        if _safe_float(
            candle.get(
                "volume"
            )
        ) > 0
    ]

    baseline_volume = (
        float(
            median(
                previous_volumes
            )
        )
        if previous_volumes
        else 0.0
    )

    volume_ratio = (
        volume
        / baseline_volume
        if baseline_volume > 0
        else 0.0
    )

    body_high = max(
        open_price,
        close,
    )

    body_low = min(
        open_price,
        close,
    )

    upper_wick = max(
        high
        - body_high,
        0.0,
    )

    lower_wick = max(
        body_low
        - low,
        0.0,
    )

    upper_wick_ratio = (
        upper_wick
        / candle_range
    )

    lower_wick_ratio = (
        lower_wick
        / candle_range
    )

    # -----------------------------------
    # SWEEP CONDITIONS
    # -----------------------------------

    swept_high = (
        high
        > previous_high
        and close
        < previous_high
    )

    swept_low = (
        low
        < previous_low
        and close
        > previous_low
    )

    # -----------------------------------
    # DEPTH
    # -----------------------------------

    high_sweep_percent = (
        _percent(
            high
            - previous_high,
            previous_high,
        )
        if high > previous_high
        else 0.0
    )

    low_sweep_percent = (
        _percent(
            previous_low
            - low,
            previous_low,
        )
        if low < previous_low
        else 0.0
    )

    high_reclaim_percent = (
        _percent(
            previous_high
            - close,
            previous_high,
        )
        if close < previous_high
        else 0.0
    )

    low_reclaim_percent = (
        _percent(
            close
            - previous_low,
            previous_low,
        )
        if close > previous_low
        else 0.0
    )

    state = "NONE"
    direction = "NEUTRAL"

    sweep_depth = 0.0
    reclaim_depth = 0.0
    wick_ratio = 0.0

    if (
        swept_low
        and not swept_high
    ):

        state = (
            "BULLISH_LIQUIDITY_SWEEP"
        )

        direction = "BULLISH"

        sweep_depth = (
            low_sweep_percent
        )

        reclaim_depth = (
            low_reclaim_percent
        )

        wick_ratio = (
            lower_wick_ratio
        )

    elif (
        swept_high
        and not swept_low
    ):

        state = (
            "BEARISH_LIQUIDITY_SWEEP"
        )

        direction = "BEARISH"

        sweep_depth = (
            high_sweep_percent
        )

        reclaim_depth = (
            high_reclaim_percent
        )

        wick_ratio = (
            upper_wick_ratio
        )

    elif (
        swept_high
        and swept_low
    ):

        state = (
            "TWO_SIDED_SWEEP"
        )

        direction = "NEUTRAL"

        sweep_depth = max(
            high_sweep_percent,
            low_sweep_percent,
        )

        reclaim_depth = min(
            high_reclaim_percent,
            low_reclaim_percent,
        )

        wick_ratio = max(
            upper_wick_ratio,
            lower_wick_ratio,
        )

    # -----------------------------------
    # QUALITY
    # -----------------------------------

    if state == "NONE":

        quality = 0.0

    else:

        sweep_quality = min(
            sweep_depth
            / 0.20,
            1.0,
        )

        reclaim_quality = min(
            reclaim_depth
            / 0.20,
            1.0,
        )

        wick_quality = min(
            wick_ratio
            / 0.50,
            1.0,
        )

        volume_quality = min(
            volume_ratio
            / 2.0,
            1.0,
        )

        quality = (
            sweep_quality
            * 0.30
            + reclaim_quality
            * 0.20
            + wick_quality
            * 0.30
            + volume_quality
            * 0.20
        )

    # -----------------------------------
    # STRONG SWEEP
    # -----------------------------------

    strong = (
        state
        in {
            "BULLISH_LIQUIDITY_SWEEP",
            "BEARISH_LIQUIDITY_SWEEP",
        }
        and wick_ratio >= 0.35
        and volume_ratio >= 1.20
        and quality >= 0.55
    )

    return {
        "available": True,

        "state":
            state,

        "direction":
            direction,

        "strong":
            strong,

        "quality": round(
            quality,
            3,
        ),

        "previous_high": round(
            previous_high,
            2,
        ),

        "previous_low": round(
            previous_low,
            2,
        ),

        "sweep_depth_percent": round(
            sweep_depth,
            3,
        ),

        "reclaim_percent": round(
            reclaim_depth,
            3,
        ),

        "wick_ratio": round(
            wick_ratio,
            3,
        ),

        "volume_ratio": round(
            volume_ratio,
            2,
        ),

        "close": round(
            close,
            2,
        ),
    }
