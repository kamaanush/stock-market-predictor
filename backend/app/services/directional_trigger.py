from __future__ import annotations

from statistics import median
from typing import Any


def _number(
    value: Any,
) -> float:
    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return 0.0


def analyze_directional_trigger(
    *,
    candles: list[dict[str, Any]],
    opportunity: dict[str, Any],
    lookback: int = 8,
) -> dict[str, Any]:

    opportunity_score = _number(
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
        _number(candle["high"])
        for candle in history
    )

    reference_low = min(
        _number(candle["low"])
        for candle in history
    )

    previous_ranges = [
        _number(candle["high"])
        - _number(candle["low"])
        for candle in history
        if (
            _number(candle["high"])
            >
            _number(candle["low"])
        )
    ]

    if not previous_ranges:

        return {
            "state": "INVALID_RANGE",
            "direction": "NONE",
            "quality": 0.0,
        }

    baseline_range = median(
        previous_ranges
    )

    previous_volumes = [
        _number(
            candle.get(
                "volume",
                0.0,
            )
        )
        for candle in history
        if _number(
            candle.get(
                "volume",
                0.0,
            )
        ) > 0
    ]

    baseline_volume = (
        median(previous_volumes)
        if previous_volumes
        else 0.0
    )

    open_price = _number(
        current["open"]
    )

    high = _number(
        current["high"]
    )

    low = _number(
        current["low"]
    )

    close = _number(
        current["close"]
    )

    volume = _number(
        current.get(
            "volume",
            0.0,
        )
    )

    current_range = (
        high - low
    )

    if current_range <= 0:

        return {
            "state": "ZERO_RANGE",
            "direction": "NONE",
            "quality": 0.0,
        }

    body = abs(
        close - open_price
    )

    body_ratio = (
        body / current_range
    )

    close_location = (
        (close - low)
        / current_range
    )

    expansion_ratio = (
        current_range
        / baseline_range
        if baseline_range > 0
        else 0.0
    )

    local_volume_ratio = (
        volume / baseline_volume
        if baseline_volume > 0
        else 0.0
    )

    rvol = _number(
        opportunity.get(
            "rvol"
        )
    )

    volume_confirmed = (
        local_volume_ratio >= 1.15
        or rvol >= 1.80
    )

    bullish_breakout = (
        close > reference_high
        and close > open_price
        and body_ratio >= 0.50
        and close_location >= 0.72
        and expansion_ratio >= 1.05
        and volume_confirmed
    )

    bearish_breakout = (
        close < reference_low
        and close < open_price
        and body_ratio >= 0.50
        and close_location <= 0.28
        and expansion_ratio >= 1.05
        and volume_confirmed
    )

    direction = "NONE"
    state = "NO_TRIGGER"
    breakout_percent = 0.0

    if bullish_breakout:

        direction = "BULLISH"

        state = (
            "CONFIRMED_BULLISH_BREAKOUT"
        )

        breakout_percent = (
            (
                close
                - reference_high
            )
            / reference_high
            * 100
        )

    elif bearish_breakout:

        direction = "BEARISH"

        state = (
            "CONFIRMED_BEARISH_BREAKOUT"
        )

        breakout_percent = (
            (
                reference_low
                - close
            )
            / reference_low
            * 100
        )

    if direction == "NONE":

        return {
            "state": state,
            "direction": direction,
            "quality": 0.0,

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
        }

    breakout_component = min(
        breakout_percent / 0.30,
        1.0,
    )

    body_component = min(
        body_ratio,
        1.0,
    )

    expansion_component = min(
        max(
            expansion_ratio - 1.0,
            0.0,
        ),
        1.0,
    )

    volume_component = min(
        max(
            local_volume_ratio - 1.0,
            0.0,
        )
        / 2.0,
        1.0,
    )

    opportunity_component = min(
        max(
            opportunity_score - 40,
            0.0,
        )
        / 30.0,
        1.0,
    )

    quality = (
        breakout_component * 0.25
        + body_component * 0.20
        + expansion_component * 0.20
        + volume_component * 0.15
        + opportunity_component * 0.20
    )

    return {
        "state":
            state,

        "direction":
            direction,

        # Ranking quality only.
        # NOT probability.
        "quality": round(
            quality,
            3,
        ),

        "opportunity_score":
            round(
                opportunity_score,
                2,
            ),

        "breakout_percent":
            round(
                breakout_percent,
                3,
            ),

        "body_ratio":
            round(
                body_ratio,
                3,
            ),

        "close_location":
            round(
                close_location,
                3,
            ),

        "expansion_ratio":
            round(
                expansion_ratio,
                3,
            ),

        "local_volume_ratio":
            round(
                local_volume_ratio,
                3,
            ),

        "rvol":
            round(
                rvol,
                2,
            ),

        "reference_high":
            reference_high,

        "reference_low":
            reference_low,
    }
