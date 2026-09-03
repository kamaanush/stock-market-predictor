from __future__ import annotations

from typing import Any


def _safe_float(
    value: Any,
) -> float:
    try:
        return float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0.0


def analyze_market_breadth(
    results: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:
    """
    Cross-sectional NSE intraday breadth.

    This is NOT a trade signal.

    It answers:

        How many stocks are advancing?
        How many are declining?
        Is participation broad or narrow?
        Does the market have bullish or
        bearish internal pressure?
    """

    ready = [
        item
        for item in results
        if item.get(
            "status"
        ) == "READY"
    ]

    total = len(
        ready
    )

    if total == 0:
        return {
            "available": False,
            "total": 0,
            "advancers": 0,
            "decliners": 0,
            "unchanged": 0,
            "advance_percent": 0.0,
            "decline_percent": 0.0,
            "net_breadth_percent": 0.0,
            "breadth_ratio": 0.0,
            "regime": "UNKNOWN",
            "participation": "UNKNOWN",
        }

    # Ignore tiny noise around zero.
    threshold = 0.05

    advancers = 0
    decliners = 0
    unchanged = 0

    strong_advancers = 0
    strong_decliners = 0

    rs_bullish = 0
    rs_bearish = 0

    for item in ready:

        change = _safe_float(
            item.get(
                "change_5m_percent"
            )
        )

        if change > threshold:
            advancers += 1

        elif change < -threshold:
            decliners += 1

        else:
            unchanged += 1

        if change >= 0.50:
            strong_advancers += 1

        elif change <= -0.50:
            strong_decliners += 1

        rs = item.get(
            "relative_strength",
            {},
        )

        rs_direction = str(
            rs.get(
                "direction",
                "NEUTRAL",
            )
        )

        if rs_direction == "BULLISH":
            rs_bullish += 1

        elif rs_direction == "BEARISH":
            rs_bearish += 1

    advance_percent = (
        advancers
        / total
        * 100.0
    )

    decline_percent = (
        decliners
        / total
        * 100.0
    )

    net_breadth_percent = (
        (
            advancers
            - decliners
        )
        / total
        * 100.0
    )

    if decliners > 0:
        breadth_ratio = (
            advancers
            / decliners
        )
    elif advancers > 0:
        breadth_ratio = float(
            advancers
        )
    else:
        breadth_ratio = 0.0

    # -----------------------------------------
    # MARKET REGIME
    # -----------------------------------------

    if (
        advance_percent >= 70
        and net_breadth_percent >= 45
    ):
        regime = (
            "STRONG_BULLISH"
        )

    elif (
        advance_percent >= 58
        and net_breadth_percent >= 20
    ):
        regime = "BULLISH"

    elif (
        decline_percent >= 70
        and net_breadth_percent <= -45
    ):
        regime = (
            "STRONG_BEARISH"
        )

    elif (
        decline_percent >= 58
        and net_breadth_percent <= -20
    ):
        regime = "BEARISH"

    else:
        regime = "BALANCED"

    # -----------------------------------------
    # PARTICIPATION QUALITY
    # -----------------------------------------

    directional_percent = (
        (
            advancers
            + decliners
        )
        / total
        * 100.0
    )

    dominant_percent = max(
        advance_percent,
        decline_percent,
    )

    if (
        dominant_percent >= 65
        and directional_percent >= 75
    ):
        participation = "BROAD"

    elif dominant_percent >= 52:
        participation = "MODERATE"

    else:
        participation = "NARROW"

    rs_net = (
        rs_bullish
        - rs_bearish
    )

    return {
        "available": True,

        "total":
            total,

        "advancers":
            advancers,

        "decliners":
            decliners,

        "unchanged":
            unchanged,

        "advance_percent": round(
            advance_percent,
            2,
        ),

        "decline_percent": round(
            decline_percent,
            2,
        ),

        "net_breadth_percent": round(
            net_breadth_percent,
            2,
        ),

        "breadth_ratio": round(
            breadth_ratio,
            2,
        ),

        "strong_advancers":
            strong_advancers,

        "strong_decliners":
            strong_decliners,

        "rs_bullish":
            rs_bullish,

        "rs_bearish":
            rs_bearish,

        "rs_net":
            rs_net,

        "regime":
            regime,

        "participation":
            participation,
    }
