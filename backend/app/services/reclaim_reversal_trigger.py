from __future__ import annotations

from statistics import median
from typing import Any


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def analyze_reclaim_reversal_trigger(
    *,
    candles: list[dict[str, Any]],
    opportunity: dict[str, Any],
    lookback: int = 8,
) -> dict[str, Any]:

    opportunity_score = _num(
        opportunity.get("score")
    )

    if opportunity_score < 40:

        return {
            "state": "SKIP_LOW_OPPORTUNITY",
            "direction": "NONE",
            "quality": 0.0,
        }

    if len(candles) < lookback + 1:

        return {
            "state": "INSUFFICIENT_DATA",
            "direction": "NONE",
            "quality": 0.0,
        }

    history = candles[
        -(lookback + 1):-1
    ]

    current = candles[-1]

    reference_high = max(
        _num(c["high"])
        for c in history
    )

    reference_low = min(
        _num(c["low"])
        for c in history
    )

    ranges = [
        _num(c["high"]) - _num(c["low"])
        for c in history
        if _num(c["high"]) > _num(c["low"])
    ]

    if not ranges:

        return {
            "state": "INVALID_RANGE",
            "direction": "NONE",
            "quality": 0.0,
        }

    baseline_range = median(
        ranges
    )

    volumes = [
        _num(
            c.get("volume", 0)
        )
        for c in history
        if _num(
            c.get("volume", 0)
        ) > 0
    ]

    baseline_volume = (
        median(volumes)
        if volumes
        else 0.0
    )

    o = _num(current["open"])
    h = _num(current["high"])
    l = _num(current["low"])
    c = _num(current["close"])

    volume = _num(
        current.get(
            "volume",
            0,
        )
    )

    candle_range = h - l

    if candle_range <= 0:

        return {
            "state": "ZERO_RANGE",
            "direction": "NONE",
            "quality": 0.0,
        }

    body = abs(
        c - o
    )

    body_ratio = (
        body / candle_range
    )

    close_location = (
        (c - l)
        / candle_range
    )

    upper_wick = (
        h - max(o, c)
    )

    lower_wick = (
        min(o, c) - l
    )

    upper_wick_ratio = (
        upper_wick / candle_range
    )

    lower_wick_ratio = (
        lower_wick / candle_range
    )

    expansion_ratio = (
        candle_range
        / baseline_range
        if baseline_range > 0
        else 0.0
    )

    local_volume_ratio = (
        volume / baseline_volume
        if baseline_volume > 0
        else 0.0
    )

    rvol = _num(
        opportunity.get("rvol")
    )

    volume_confirmed = (
        local_volume_ratio >= 1.10
        or rvol >= 1.50
    )

    # ==================================
    # BULLISH FAILED BREAKDOWN
    #
    # Price trades below support but
    # closes back inside / above it.
    # ==================================

    downside_sweep = (
        l < reference_low
    )

    bullish_reclaim = (
        downside_sweep
        and c > reference_low
        and c > o
        and close_location >= 0.60
        and lower_wick_ratio >= 0.20
        and expansion_ratio >= 0.90
        and volume_confirmed
    )

    # ==================================
    # BEARISH FAILED BREAKOUT
    # ==================================

    upside_sweep = (
        h > reference_high
    )

    bearish_reclaim = (
        upside_sweep
        and c < reference_high
        and c < o
        and close_location <= 0.40
        and upper_wick_ratio >= 0.20
        and expansion_ratio >= 0.90
        and volume_confirmed
    )

    if bullish_reclaim:

        direction = "BULLISH"

        state = (
            "BULLISH_FAILED_BREAKDOWN_RECLAIM"
        )

        sweep_percent = (
            (
                reference_low - l
            )
            / reference_low
            * 100
        )

        reclaim_percent = (
            (
                c - reference_low
            )
            / reference_low
            * 100
        )

        wick_ratio = (
            lower_wick_ratio
        )

    elif bearish_reclaim:

        direction = "BEARISH"

        state = (
            "BEARISH_FAILED_BREAKOUT_RECLAIM"
        )

        sweep_percent = (
            (
                h - reference_high
            )
            / reference_high
            * 100
        )

        reclaim_percent = (
            (
                reference_high - c
            )
            / reference_high
            * 100
        )

        wick_ratio = (
            upper_wick_ratio
        )

    else:

        return {
            "state": "NO_TRIGGER",
            "direction": "NONE",
            "quality": 0.0,

            "body_ratio": round(
                body_ratio,
                3,
            ),

            "lower_wick_ratio": round(
                lower_wick_ratio,
                3,
            ),

            "upper_wick_ratio": round(
                upper_wick_ratio,
                3,
            ),

            "expansion_ratio": round(
                expansion_ratio,
                3,
            ),

            "local_volume_ratio": round(
                local_volume_ratio,
                3,
            ),
        }

    # ==================================
    # QUALITY
    # Ranking score only.
    # ==================================

    sweep_component = min(
        sweep_percent / 0.30,
        1.0,
    )

    reclaim_component = min(
        reclaim_percent / 0.20,
        1.0,
    )

    wick_component = min(
        wick_ratio / 0.50,
        1.0,
    )

    volume_component = min(
        max(
            local_volume_ratio - 1,
            0,
        )
        / 2,
        1.0,
    )

    opportunity_component = min(
        max(
            opportunity_score - 40,
            0,
        )
        / 30,
        1.0,
    )

    quality = (
        sweep_component * 0.20
        + reclaim_component * 0.25
        + wick_component * 0.20
        + volume_component * 0.15
        + opportunity_component * 0.20
    )

    return {
        "state": state,
        "direction": direction,

        "quality": round(
            quality,
            3,
        ),

        "opportunity_score": round(
            opportunity_score,
            2,
        ),

        "sweep_percent": round(
            sweep_percent,
            3,
        ),

        "reclaim_percent": round(
            reclaim_percent,
            3,
        ),

        "wick_ratio": round(
            wick_ratio,
            3,
        ),

        "body_ratio": round(
            body_ratio,
            3,
        ),

        "expansion_ratio": round(
            expansion_ratio,
            3,
        ),

        "local_volume_ratio": round(
            local_volume_ratio,
            3,
        ),

        "rvol": round(
            rvol,
            2,
        ),

        "reference_high": reference_high,
        "reference_low": reference_low,
    }
