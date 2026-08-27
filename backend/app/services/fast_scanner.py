from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        if value is None:
            return default

        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def _percent_change(
    current: float,
    previous: float,
) -> float:
    if previous <= 0:
        return 0.0

    return (
        (current - previous)
        / previous
        * 100
    )


def _volume_ratio(
    candles: list[dict[str, Any]],
) -> float:
    if len(candles) < 3:
        return 0.0

    current = _safe_float(
        candles[-1].get("volume")
    )

    previous = candles[
        max(
            0,
            len(candles) - 11,
        ):
        -1
    ]

    volumes = [
        _safe_float(
            item.get("volume")
        )
        for item in previous
    ]

    positive = [
        value
        for value in volumes
        if value > 0
    ]

    if not positive:
        return 0.0

    average = (
        sum(positive)
        / len(positive)
    )

    if average <= 0:
        return 0.0

    return current / average


def _breakout_percent(
    candles: list[dict[str, Any]],
    price: float,
) -> float:
    if len(candles) < 3:
        return 0.0

    previous = candles[
        max(
            0,
            len(candles) - 6,
        ):
        -1
    ]

    if not previous:
        return 0.0

    previous_high = max(
        _safe_float(
            item.get("high")
        )
        for item in previous
    )

    previous_low = min(
        _safe_float(
            item.get("low")
        )
        for item in previous
    )

    if (
        previous_high > 0
        and price > previous_high
    ):
        return _percent_change(
            price,
            previous_high,
        )

    if (
        previous_low > 0
        and price < previous_low
    ):
        return _percent_change(
            price,
            previous_low,
        )

    return 0.0


def analyze_fast_stock(
    *,
    tick: dict[str, Any],
    candle_engine: Any,
) -> dict[str, Any]:
    symbol = str(
        tick.get(
            "symbol",
            "",
        )
    ).strip().upper()

    price = _safe_float(
        tick.get("ltp")
    )

    one_minute = (
        candle_engine.candles(
            symbol,
            "1m",
            limit=12,
        )
    )

    five_minute = (
        candle_engine.candles(
            symbol,
            "5m",
            limit=4,
        )
    )

    change_1m = 0.0
    change_5m = 0.0

    if one_minute:
        latest_1m = (
            one_minute[-1]
        )

        change_1m = (
            _percent_change(
                _safe_float(
                    latest_1m.get(
                        "close"
                    )
                ),
                _safe_float(
                    latest_1m.get(
                        "open"
                    )
                ),
            )
        )

    if five_minute:
        latest_5m = (
            five_minute[-1]
        )

        change_5m = (
            _percent_change(
                _safe_float(
                    latest_5m.get(
                        "close"
                    )
                ),
                _safe_float(
                    latest_5m.get(
                        "open"
                    )
                ),
            )
        )

    volume_ratio = (
        _volume_ratio(
            one_minute
        )
    )

    breakout_percent = (
        _breakout_percent(
            one_minute,
            price,
        )
    )

    direction_value = (
        change_5m * 0.55
        + change_1m * 0.30
        + breakout_percent * 0.15
    )

    if direction_value >= 0.08:
        direction = "BULLISH"

    elif direction_value <= -0.08:
        direction = "BEARISH"

    else:
        direction = "NEUTRAL"

    momentum_5m_score = min(
        abs(change_5m)
        * 15.0,
        35.0,
    )

    momentum_1m_score = min(
        abs(change_1m)
        * 20.0,
        20.0,
    )

    volume_score = min(
        max(
            volume_ratio - 1.0,
            0.0,
        )
        * 12.5,
        25.0,
    )

    breakout_score = min(
        abs(
            breakout_percent
        )
        * 20.0,
        20.0,
    )

    fast_score = min(
        100.0,
        momentum_5m_score
        + momentum_1m_score
        + volume_score
        + breakout_score,
    )

    reasons: list[str] = []

    if abs(change_5m) >= 0.30:
        reasons.append(
            (
                "5m momentum "
                f"{change_5m:+.2f}%"
            )
        )

    if volume_ratio >= 1.5:
        reasons.append(
            (
                "volume "
                f"{volume_ratio:.1f}x"
            )
        )

    if breakout_percent > 0:
        reasons.append(
            "upside breakout"
        )

    elif breakout_percent < 0:
        reasons.append(
            "downside breakout"
        )

    if not reasons:
        reasons.append(
            "normal activity"
        )

    ready = (
        len(one_minute)
        >= 2
    )

    return {
        "symbol": symbol,

        "token": str(
            tick.get(
                "token",
                "",
            )
        ).strip(),

        "ltp": round(
            price,
            2,
        ),

        "direction":
            direction,

        "fast_score": round(
            fast_score,
            2,
        ),

        "change_1m_percent":
            round(
                change_1m,
                3,
            ),

        "change_5m_percent":
            round(
                change_5m,
                3,
            ),

        "volume_ratio":
            round(
                volume_ratio,
                2,
            ),

        "breakout_percent":
            round(
                breakout_percent,
                3,
            ),

        "cumulative_volume":
            _safe_float(
                tick.get(
                    "volume"
                )
            ),

        "status": (
            "READY"
            if ready
            else "WARMING_UP"
        ),

        "reason":
            ", ".join(
                reasons
            ),
    }


def build_fast_scan_snapshot(
    *,
    ticks: list[dict[str, Any]],
    candle_engine: Any,
) -> dict[str, Any]:
    results: list[
        dict[str, Any]
    ] = []

    for tick in ticks:
        try:
            result = (
                analyze_fast_stock(
                    tick=tick,
                    candle_engine=(
                        candle_engine
                    ),
                )
            )

            if result["symbol"]:
                results.append(
                    result
                )

        except Exception as exc:
            symbol = str(
                tick.get(
                    "symbol",
                    "UNKNOWN",
                )
            )

            print(
                "[FAST SCANNER]",
                symbol,
                exc,
            )

    results.sort(
        key=lambda item: (
            item["fast_score"]
        ),
        reverse=True,
    )

    ready = [
        item
        for item in results
        if (
            item["status"]
            == "READY"
        )
    ]

    bullish = sum(
        1
        for item in ready
        if (
            item["direction"]
            == "BULLISH"
        )
    )

    bearish = sum(
        1
        for item in ready
        if (
            item["direction"]
            == "BEARISH"
        )
    )

    neutral = (
        len(ready)
        - bullish
        - bearish
    )

    return {
        "generated_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),

        "live_count":
            len(results),

        "scored_count":
            len(ready),

        "warming_up_count":
            (
                len(results)
                - len(ready)
            ),

        "bullish_count":
            bullish,

        "bearish_count":
            bearish,

        "neutral_count":
            neutral,

        "results":
            results,
    }
