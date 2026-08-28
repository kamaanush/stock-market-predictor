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


def analyze_relative_strength(
    *,
    stock_candles: list[dict[str, Any]],
    benchmark_candles: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """
    Market-relative strength.

    IMPORTANT:
    This is NOT RSI.

    It compares a stock's return with the benchmark's return over
    the same 1m, 3m and 5m windows.

    Example:
      stock 5m = +0.80%
      NIFTY 5m = +0.20%
      RS 5m    = +0.60%

    Positive = stock outperforming NIFTY.
    Negative = stock underperforming NIFTY.
    """
    benchmark = benchmark_candles or []

    if (
        len(stock_candles) < 2
        or len(benchmark) < 2
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
        }

    stock_1m = _window_return(
        stock_candles,
        1,
    )
    stock_3m = _window_return(
        stock_candles,
        3,
    )
    stock_5m = _window_return(
        stock_candles,
        5,
    )

    benchmark_1m = _window_return(
        benchmark,
        1,
    )
    benchmark_3m = _window_return(
        benchmark,
        3,
    )
    benchmark_5m = _window_return(
        benchmark,
        5,
    )

    rs_1m = stock_1m - benchmark_1m
    rs_3m = stock_3m - benchmark_3m
    rs_5m = stock_5m - benchmark_5m

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
        persistence = (
            "IMPROVING"
        )
        direction = "BULLISH"

    elif negative_count >= 2:
        persistence = (
            "WEAKENING"
        )
        direction = "BEARISH"

    else:
        persistence = "MIXED"
        direction = "NEUTRAL"

    # Weighted toward the longer 5-minute comparison, but still
    # detects recent acceleration/deceleration.
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
        "persistence": persistence,
        "direction": direction,
        "strength": round(
            strength,
            4,
        ),
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
