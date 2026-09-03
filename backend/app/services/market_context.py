from __future__ import annotations

from typing import Any


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


def percent_change(
    current: float,
    previous: float,
) -> float:
    if previous <= 0:
        return 0.0

    return (
        (current - previous)
        / previous
        * 100.0
    )


def _window_return(
    candles: list[dict[str, Any]],
    bars: int,
) -> float:
    """
    Return close-to-close % change across the requested number
    of completed/available bars.
    """
    if len(candles) < 2:
        return 0.0

    usable_bars = min(
        max(int(bars), 1),
        len(candles) - 1,
    )

    previous_close = safe_float(
        candles[
            -(usable_bars + 1)
        ].get("close")
    )

    current_close = safe_float(
        candles[-1].get("close")
    )

    return percent_change(
        current_close,
        previous_close,
    )


def _minute_timestamp(
    candle: dict[str, Any],
) -> int | None:
    """
    Normalize a candle timestamp to its
    1-minute bucket.
    """

    raw = candle.get(
        "time"
    )

    if raw is None:
        return None

    try:
        if isinstance(
            raw,
            str,
        ):
            from datetime import datetime

            timestamp = (
                datetime.fromisoformat(
                    raw.replace(
                        "Z",
                        "+00:00",
                    )
                ).timestamp()
            )

        else:
            timestamp = float(
                raw
            )

            if (
                timestamp
                > 10_000_000_000
            ):
                timestamp /= 1000.0

    except (
        TypeError,
        ValueError,
    ):
        return None

    return (
        int(timestamp)
        // 60
        * 60
    )


def _aligned_close_pairs(
    stock_candles: list[
        dict[str, Any]
    ],
    benchmark_candles: list[
        dict[str, Any]
    ],
) -> tuple[
    list[
        tuple[
            int,
            float,
            float,
        ]
    ],
    float,
]:
    """
    Match stock and NIFTY candles using
    the exact same minute timestamps.
    """

    stock_map: dict[
        int,
        float,
    ] = {}

    benchmark_map: dict[
        int,
        float,
    ] = {}

    for candle in stock_candles:
        timestamp = (
            _minute_timestamp(
                candle
            )
        )

        close = safe_float(
            candle.get(
                "close"
            )
        )

        if (
            timestamp is not None
            and close > 0
        ):
            stock_map[
                timestamp
            ] = close

    for candle in benchmark_candles:
        timestamp = (
            _minute_timestamp(
                candle
            )
        )

        close = safe_float(
            candle.get(
                "close"
            )
        )

        if (
            timestamp is not None
            and close > 0
        ):
            benchmark_map[
                timestamp
            ] = close

    common = sorted(
        set(
            stock_map
        )
        & set(
            benchmark_map
        )
    )

    pairs = [
        (
            timestamp,
            stock_map[
                timestamp
            ],
            benchmark_map[
                timestamp
            ],
        )
        for timestamp in common
    ]

    if not common:
        return (
            pairs,
            999.0,
        )

    latest_stock = max(
        stock_map,
        default=common[-1],
    )

    latest_benchmark = max(
        benchmark_map,
        default=common[-1],
    )

    latest_common = (
        common[-1]
    )

    alignment_lag = max(
        (
            latest_stock
            - latest_common
        )
        / 60.0,
        (
            latest_benchmark
            - latest_common
        )
        / 60.0,
    )

    return (
        pairs,
        alignment_lag,
    )


def _latest_contiguous_pairs(
    pairs: list[
        tuple[
            int,
            float,
            float,
        ]
    ],
) -> list[
    tuple[
        int,
        float,
        float,
    ]
]:
    """
    Keep only the newest uninterrupted
    sequence of true 1-minute aligned bars.

    Example:
        15:18
        15:19
        15:20
        15:21
        15:22

    A gap such as 15:18 -> 15:21 breaks
    the sequence instead of treating it
    like one 1-minute move.
    """

    if not pairs:
        return []

    contiguous = [
        pairs[-1]
    ]

    for index in range(
        len(pairs) - 2,
        -1,
        -1,
    ):
        newer_time = (
            contiguous[-1][0]
        )

        older_time = (
            pairs[index][0]
        )

        if (
            newer_time
            - older_time
            != 60
        ):
            break

        contiguous.append(
            pairs[index]
        )

    contiguous.reverse()

    return contiguous



def _pair_return(
    pairs: list[
        tuple[
            int,
            float,
            float,
        ]
    ],
    bars: int,
) -> tuple[
    float,
    float,
]:
    """
    Calculate stock and benchmark returns
    across exactly the same aligned bars.
    """

    if len(pairs) < 2:
        return (
            0.0,
            0.0,
        )

    usable_bars = min(
        max(
            int(bars),
            1,
        ),
        len(pairs) - 1,
    )

    previous = pairs[
        -(usable_bars + 1)
    ]

    current = pairs[-1]

    stock_return = (
        percent_change(
            current[1],
            previous[1],
        )
    )

    benchmark_return = (
        percent_change(
            current[2],
            previous[2],
        )
    )

    return (
        stock_return,
        benchmark_return,
    )


def analyze_relative_strength(
    *,
    stock_candles: list[
        dict[str, Any]
    ],
    benchmark_candles: list[
        dict[str, Any]
    ] | None,
) -> dict[str, Any]:
    """
    Stock strength relative to NIFTY 50.

    Stock and benchmark candles are first
    aligned by their 1-minute timestamps.

    This is NOT RSI.
    """

    benchmark = (
        benchmark_candles
        or []
    )

    pairs, alignment_lag = (
        _aligned_close_pairs(
            stock_candles,
            benchmark,
        )
    )

    pairs = (
        _latest_contiguous_pairs(
            pairs
        )
    )

    # We need enough common candles and
    # reasonably fresh overlap.
    if (
        len(pairs) < 6
        or alignment_lag > 2.0
    ):
        return {
            "available": False,
            "rs_1m_pct": 0.0,
            "rs_3m_pct": 0.0,
            "rs_5m_pct": 0.0,
            "stock_5m_pct": 0.0,
            "benchmark_5m_pct": 0.0,
            "persistence": "UNKNOWN",
            "direction": "NEUTRAL",
            "strength": 0.0,
            "aligned_points": len(
                pairs
            ),
            "alignment_lag_minutes": round(
                alignment_lag,
                2,
            ),
        }

    (
        stock_1m,
        benchmark_1m,
    ) = _pair_return(
        pairs,
        1,
    )

    (
        stock_3m,
        benchmark_3m,
    ) = _pair_return(
        pairs,
        3,
    )

    (
        stock_5m,
        benchmark_5m,
    ) = _pair_return(
        pairs,
        5,
    )

    rs_1m = (
        stock_1m
        - benchmark_1m
    )

    rs_3m = (
        stock_3m
        - benchmark_3m
    )

    rs_5m = (
        stock_5m
        - benchmark_5m
    )

    positive_count = sum(
        value > 0.03
        for value in (
            rs_1m,
            rs_3m,
            rs_5m,
        )
    )

    negative_count = sum(
        value < -0.03
        for value in (
            rs_1m,
            rs_3m,
            rs_5m,
        )
    )

    if positive_count == 3:
        persistence = (
            "PERSISTENT OUTPERFORMANCE"
        )
        direction = "BULLISH"

    elif negative_count == 3:
        persistence = (
            "PERSISTENT UNDERPERFORMANCE"
        )
        direction = "BEARISH"

    elif positive_count >= 2:
        persistence = "IMPROVING"
        direction = "BULLISH"

    elif negative_count >= 2:
        persistence = "WEAKENING"
        direction = "BEARISH"

    else:
        persistence = "MIXED"
        direction = "NEUTRAL"

    strength = (
        rs_1m * 0.20
        + rs_3m * 0.30
        + rs_5m * 0.50
    )

    return {
        "available": True,

        "rs_1m_pct": round(
            rs_1m,
            4,
        ),

        "rs_3m_pct": round(
            rs_3m,
            4,
        ),

        "rs_5m_pct": round(
            rs_5m,
            4,
        ),

        "stock_5m_pct": round(
            stock_5m,
            4,
        ),

        "benchmark_5m_pct": round(
            benchmark_5m,
            4,
        ),

        "persistence":
            persistence,

        "direction":
            direction,

        "strength": round(
            strength,
            4,
        ),

        "aligned_points": len(
            pairs
        ),

        "alignment_lag_minutes": round(
            alignment_lag,
            2,
        ),

        "latest_aligned_time":
            pairs[-1][0],
    }


def analyze_rs_acceleration(
    *,
    stock_candles: list[
        dict[str, Any]
    ],
    benchmark_candles: list[
        dict[str, Any]
    ] | None,
    lookback: int = 6,
) -> dict[str, Any]:
    """
    Measure genuine stock-vs-NIFTY
    relative-strength acceleration.

    Requirements:
    - timestamps aligned
    - consecutive 1-minute candles
    - RS slope moving in the same direction
    - acceleration itself must confirm
      the direction

    This remains a ranking feature,
    not a trade signal.
    """

    benchmark = (
        benchmark_candles
        or []
    )

    pairs, alignment_lag = (
        _aligned_close_pairs(
            stock_candles,
            benchmark,
        )
    )

    pairs = (
        _latest_contiguous_pairs(
            pairs
        )
    )

    minimum_points = 6

    if (
        len(pairs)
        < minimum_points
        or alignment_lag > 2.0
    ):
        return {
            "available": False,
            "classification": "UNKNOWN",
            "direction": "NEUTRAL",
            "rs_change_3m": 0.0,
            "recent_slope": 0.0,
            "previous_slope": 0.0,
            "acceleration": 0.0,
            "consistency": 0.0,
            "quality": 0.0,
            "latest_rs": 0.0,
            "contiguous_points": len(
                pairs
            ),
        }

    pairs = pairs[
        -max(
            minimum_points,
            int(lookback),
        ):
    ]

    base_stock = (
        pairs[0][1]
    )

    base_benchmark = (
        pairs[0][2]
    )

    rs_curve = []

    for (
        timestamp,
        stock_close,
        benchmark_close,
    ) in pairs:

        stock_return = (
            percent_change(
                stock_close,
                base_stock,
            )
        )

        benchmark_return = (
            percent_change(
                benchmark_close,
                base_benchmark,
            )
        )

        rs_curve.append(
            {
                "time": timestamp,

                "rs": (
                    stock_return
                    - benchmark_return
                ),
            }
        )

    slopes = [
        (
            rs_curve[index]["rs"]
            - rs_curve[
                index - 1
            ]["rs"]
        )
        for index
        in range(
            1,
            len(rs_curve),
        )
    ]

    # Smooth the slope rather than using
    # one noisy final candle.
    previous_window = (
        slopes[-4:-2]
    )

    recent_window = (
        slopes[-2:]
    )

    previous_slope = (
        sum(
            previous_window
        )
        / len(
            previous_window
        )
    )

    recent_slope = (
        sum(
            recent_window
        )
        / len(
            recent_window
        )
    )

    acceleration = (
        recent_slope
        - previous_slope
    )

    rs_change_3m = (
        rs_curve[-1]["rs"]
        - rs_curve[-4]["rs"]
    )

    recent_slopes = (
        slopes[-3:]
    )

    bullish_steps = sum(
        value > 0.01
        for value
        in recent_slopes
    )

    bearish_steps = sum(
        value < -0.01
        for value
        in recent_slopes
    )

    bullish_consistency = (
        bullish_steps
        / len(
            recent_slopes
        )
    )

    bearish_consistency = (
        bearish_steps
        / len(
            recent_slopes
        )
    )

    classification = "MIXED"
    direction = "NEUTRAL"

    consistency = max(
        bullish_consistency,
        bearish_consistency,
    )

    if (
        rs_change_3m >= 0.10
        and recent_slope >= 0.025
        and acceleration >= 0.015
        and bullish_steps >= 2
    ):
        classification = (
            "BULLISH_ACCELERATION"
        )

        direction = "BULLISH"

        consistency = (
            bullish_consistency
        )

    elif (
        rs_change_3m <= -0.10
        and recent_slope <= -0.025
        and acceleration <= -0.015
        and bearish_steps >= 2
    ):
        classification = (
            "BEARISH_ACCELERATION"
        )

        direction = "BEARISH"

        consistency = (
            bearish_consistency
        )

    change_quality = min(
        abs(
            rs_change_3m
        )
        / 0.40,
        1.0,
    )

    slope_quality = min(
        abs(
            recent_slope
        )
        / 0.15,
        1.0,
    )

    acceleration_quality = min(
        abs(
            acceleration
        )
        / 0.10,
        1.0,
    )

    quality = (
        change_quality
        * 0.40
        + slope_quality
        * 0.25
        + acceleration_quality
        * 0.20
        + consistency
        * 0.15
    )

    if classification == "MIXED":
        quality *= 0.20

    return {
        "available": True,

        "classification":
            classification,

        "direction":
            direction,

        "rs_change_3m": round(
            rs_change_3m,
            4,
        ),

        "recent_slope": round(
            recent_slope,
            4,
        ),

        "previous_slope": round(
            previous_slope,
            4,
        ),

        "acceleration": round(
            acceleration,
            4,
        ),

        "consistency": round(
            consistency,
            4,
        ),

        "quality": round(
            max(
                0.0,
                min(
                    quality,
                    1.0,
                ),
            ),
            4,
        ),

        "latest_rs": round(
            rs_curve[-1]["rs"],
            4,
        ),

        "contiguous_points":
            len(pairs),
    }



def analyze_effort_vs_result(
    *,
    candles: list[dict[str, Any]],
    volume_ratio: float,
) -> dict[str, Any]:
    """
    Cheap pre-scan 'effort vs result' model.

    Effort:
      relative volume

    Result:
      current candle range versus recent average range,
      plus body/close quality.

    This allows the fast scanner to distinguish:

      HIGH VOLUME + BIG CLEAN MOVE
        -> participation / expansion

      HIGH VOLUME + SMALL RESULT
        -> possible absorption

      LARGE RANGE + POOR CLOSE / WICK
        -> possible rejection

    The deep buyer_seller_pressure/candle_flow services should still
    perform the final interpretation later in the pipeline.
    """
    if len(candles) < 3:
        return {
            "available": False,
            "range_ratio": 0.0,
            "body_ratio": 0.0,
            "close_location": 0.5,
            "classification": "UNKNOWN",
            "direction": "NEUTRAL",
            "quality": 0.0,
        }

    current = candles[-1]

    open_value = safe_float(
        current.get("open")
    )
    high_value = safe_float(
        current.get("high")
    )
    low_value = safe_float(
        current.get("low")
    )
    close_value = safe_float(
        current.get("close")
    )

    current_range = max(
        high_value - low_value,
        0.0,
    )

    recent = candles[
        max(
            0,
            len(candles) - 11,
        ):
        -1
    ]

    recent_ranges = [
        max(
            safe_float(
                candle.get("high")
            )
            - safe_float(
                candle.get("low")
            ),
            0.0,
        )
        for candle in recent
    ]

    positive_ranges = [
        value
        for value in recent_ranges
        if value > 0
    ]

    average_range = (
        sum(positive_ranges)
        / len(positive_ranges)
        if positive_ranges
        else 0.0
    )

    range_ratio = (
        current_range / average_range
        if average_range > 0
        else 0.0
    )

    body = abs(
        close_value - open_value
    )

    body_ratio = (
        body / current_range
        if current_range > 0
        else 0.0
    )

    close_location = (
        (close_value - low_value)
        / current_range
        if current_range > 0
        else 0.5
    )

    if close_value > open_value:
        candle_direction = "BULLISH"
    elif close_value < open_value:
        candle_direction = "BEARISH"
    else:
        candle_direction = "NEUTRAL"

    classification = "NORMAL"
    quality = 0.0

    # High activity but price is not travelling much:
    # one side may be absorbing the other side's effort.
    if (
        volume_ratio >= 1.8
        and range_ratio <= 0.80
    ):
        classification = (
            "POSSIBLE ABSORPTION"
        )
        quality = -0.5

    # Large activity + large spread + strong body:
    # price is efficiently translating participation into movement.
    elif (
        volume_ratio >= 1.5
        and range_ratio >= 1.35
        and body_ratio >= 0.55
    ):
        classification = (
            "EFFICIENT EXPANSION"
        )
        quality = min(
            1.0,
            (
                (min(volume_ratio, 3.0) / 3.0)
                * 0.40
                + (min(range_ratio, 2.5) / 2.5)
                * 0.40
                + body_ratio * 0.20
            ),
        )

    # Big range but poor body / poor close placement:
    # possible rejection rather than clean continuation.
    elif (
        range_ratio >= 1.35
        and body_ratio <= 0.35
    ):
        classification = (
            "POSSIBLE REJECTION"
        )
        quality = -0.25

    else:
        quality = min(
            0.6,
            (
                min(
                    max(
                        range_ratio - 0.8,
                        0.0,
                    ),
                    1.2,
                )
                / 1.2
            )
            * 0.6,
        )

    # Directional close-quality adjustment.
    if (
        candle_direction == "BULLISH"
        and close_location >= 0.80
    ):
        quality += 0.15

    elif (
        candle_direction == "BEARISH"
        and close_location <= 0.20
    ):
        quality += 0.15

    quality = max(
        -1.0,
        min(
            quality,
            1.0,
        ),
    )

    return {
        "available": True,
        "range_ratio": round(
            range_ratio,
            4,
        ),
        "body_ratio": round(
            body_ratio,
            4,
        ),
        "close_location": round(
            close_location,
            4,
        ),
        "classification": classification,
        "direction": candle_direction,
        "quality": round(
            quality,
            4,
        ),
    }
