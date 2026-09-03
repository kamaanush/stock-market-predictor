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


def _median_positive(
    values: list[float],
) -> float:

    clean = [
        value
        for value in values
        if value > 0
    ]

    if not clean:
        return 0.0

    return float(
        median(clean)
    )


def _range_percent(
    candle: dict[str, Any],
) -> float:

    high = _safe_float(
        candle.get("high")
    )

    low = _safe_float(
        candle.get("low")
    )

    close = _safe_float(
        candle.get("close")
    )

    if close <= 0:
        return 0.0

    return (
        (high - low)
        / close
        * 100.0
    )


def analyze_compression_expansion(
    candles: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:
    """
    Detect:

    1. shrinking candle ranges
    2. volume dry-up
    3. price compression
    4. directional expansion

    Intended for 1-minute intraday candles.

    This is a setup detector,
    not a BUY/SELL signal.
    """

    if len(candles) < 13:

        return {
            "available": False,
            "state":
                "INSUFFICIENT_DATA",
            "score": 0.0,
        }

    candles = candles[-13:]

    earlier = candles[
        0:6
    ]

    compression = candles[
        6:12
    ]

    latest = candles[
        -1
    ]

    # ----------------------------------
    # RANGE COMPRESSION
    # ----------------------------------

    earlier_ranges = [
        _range_percent(candle)
        for candle in earlier
    ]

    recent_ranges = [
        _range_percent(candle)
        for candle in compression
    ]

    earlier_range = (
        _median_positive(
            earlier_ranges
        )
    )

    recent_range = (
        _median_positive(
            recent_ranges
        )
    )

    if (
        earlier_range <= 0
        or recent_range <= 0
    ):

        return {
            "available": False,
            "state":
                "INVALID_RANGE",
            "score": 0.0,
        }

    compression_ratio = (
        recent_range
        / earlier_range
    )

    # ----------------------------------
    # VOLUME DRY-UP
    # ----------------------------------

    earlier_volume = (
        _median_positive(
            [
                _safe_float(
                    candle.get(
                        "volume"
                    )
                )
                for candle
                in earlier
            ]
        )
    )

    recent_volume = (
        _median_positive(
            [
                _safe_float(
                    candle.get(
                        "volume"
                    )
                )
                for candle
                in compression
            ]
        )
    )

    if earlier_volume > 0:

        volume_dryup_ratio = (
            recent_volume
            / earlier_volume
        )

    else:

        volume_dryup_ratio = 1.0

    # ----------------------------------
    # COMPRESSION BOX
    # ----------------------------------

    compression_high = max(
        _safe_float(
            candle.get(
                "high"
            )
        )
        for candle
        in compression
    )

    compression_low = min(
        _safe_float(
            candle.get(
                "low"
            )
        )
        for candle
        in compression
    )

    box_mid = (
        compression_high
        + compression_low
    ) / 2.0

    if box_mid > 0:

        box_width_percent = (
            (
                compression_high
                - compression_low
            )
            / box_mid
            * 100.0
        )

    else:

        box_width_percent = 0.0

    # ----------------------------------
    # LATEST EXPANSION BAR
    # ----------------------------------

    latest_open = (
        _safe_float(
            latest.get(
                "open"
            )
        )
    )

    latest_close = (
        _safe_float(
            latest.get(
                "close"
            )
        )
    )

    latest_high = (
        _safe_float(
            latest.get(
                "high"
            )
        )
    )

    latest_low = (
        _safe_float(
            latest.get(
                "low"
            )
        )
    )

    latest_volume = (
        _safe_float(
            latest.get(
                "volume"
            )
        )
    )

    latest_range = (
        _range_percent(
            latest
        )
    )

    range_expansion = (
        latest_range
        / recent_range
        if recent_range > 0
        else 0.0
    )

    volume_expansion = (
        latest_volume
        / recent_volume
        if recent_volume > 0
        else 0.0
    )

    bullish_break = (
        latest_close
        > compression_high
    )

    bearish_break = (
        latest_close
        < compression_low
    )

    bullish_body = (
        latest_close
        > latest_open
    )

    bearish_body = (
        latest_close
        < latest_open
    )

    # ----------------------------------
    # QUALITIES
    # ----------------------------------

    compression_quality = max(
        0.0,
        min(
            (
                1.0
                - compression_ratio
            )
            / 0.50,
            1.0,
        ),
    )

    dryup_quality = max(
        0.0,
        min(
            (
                1.0
                - volume_dryup_ratio
            )
            / 0.50,
            1.0,
        ),
    )

    expansion_quality = min(
        max(
            (
                range_expansion
                - 1.0
            )
            / 1.5,
            0.0,
        ),
        1.0,
    )

    volume_expansion_quality = min(
        max(
            (
                volume_expansion
                - 1.0
            )
            / 2.0,
            0.0,
        ),
        1.0,
    )

    setup_quality = (
        compression_quality
        * 0.60
        + dryup_quality
        * 0.40
    )

    breakout_quality = (
        setup_quality
        * 0.45
        + expansion_quality
        * 0.30
        + volume_expansion_quality
        * 0.25
    )

    # ----------------------------------
    # CLASSIFICATION
    # ----------------------------------

    state = "NONE"
    direction = "NEUTRAL"

    if (
        compression_ratio <= 0.75
        and volume_dryup_ratio <= 0.80
        and bullish_break
        and bullish_body
        and range_expansion >= 1.40
        and volume_expansion >= 1.20
    ):

        state = (
            "BULLISH_EXPANSION"
        )

        direction = "BULLISH"

        score = (
            breakout_quality
            * 100.0
        )

    elif (
        compression_ratio <= 0.75
        and volume_dryup_ratio <= 0.80
        and bearish_break
        and bearish_body
        and range_expansion >= 1.40
        and volume_expansion >= 1.20
    ):

        state = (
            "BEARISH_EXPANSION"
        )

        direction = "BEARISH"

        score = (
            breakout_quality
            * 100.0
        )

    elif (
        compression_ratio <= 0.70
        and volume_dryup_ratio <= 0.75
    ):

        state = (
            "READY_TO_EXPAND"
        )

        score = (
            setup_quality
            * 100.0
        )

    elif (
        compression_ratio <= 0.80
    ):

        state = "COMPRESSION"

        score = (
            setup_quality
            * 70.0
        )

    else:

        score = 0.0

    return {
        "available": True,

        "state":
            state,

        "direction":
            direction,

        "score": round(
            score,
            2,
        ),

        "compression_ratio": round(
            compression_ratio,
            3,
        ),

        "volume_dryup_ratio": round(
            volume_dryup_ratio,
            3,
        ),

        "range_expansion": round(
            range_expansion,
            3,
        ),

        "volume_expansion": round(
            volume_expansion,
            3,
        ),

        "compression_high": round(
            compression_high,
            2,
        ),

        "compression_low": round(
            compression_low,
            2,
        ),

        "box_width_percent": round(
            box_width_percent,
            3,
        ),

        "latest_close": round(
            latest_close,
            2,
        ),
    }
