from __future__ import annotations

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


def analyze_setup_confluence(
    *,
    stock: dict[str, Any],
    market_breadth: dict[
        str,
        Any,
    ] | None = None,
) -> dict[str, Any]:
    """
    Combine independent scanner features.

    This is a ranking/context layer,
    not a trade execution signal.
    """

    breadth = (
        market_breadth
        or {}
    )

    bullish_points = 0.0
    bearish_points = 0.0

    bullish_reasons = []
    bearish_reasons = []

    contradictions = []


    # ======================================
    # MARKET RELATIVE STRENGTH
    # ======================================

    rs = stock.get(
        "relative_strength",
        {},
    )

    if rs.get(
        "available",
        False,
    ):

        rs_direction = str(
            rs.get(
                "direction",
                "NEUTRAL",
            )
        ).upper()

        strength = abs(
            _safe_float(
                rs.get(
                    "strength"
                )
            )
        )

        weight = min(
            18.0,
            8.0
            + strength * 4.0,
        )

        if (
            rs_direction
            == "BULLISH"
        ):

            bullish_points += (
                weight
            )

            bullish_reasons.append(
                "NIFTY relative strength"
            )

        elif (
            rs_direction
            == "BEARISH"
        ):

            bearish_points += (
                weight
            )

            bearish_reasons.append(
                "NIFTY relative weakness"
            )


    # ======================================
    # RS ACCELERATION
    # ======================================

    acceleration = stock.get(
        "rs_acceleration",
        {},
    )

    if acceleration.get(
        "available",
        False,
    ):

        accel_direction = str(
            acceleration.get(
                "direction",
                "NEUTRAL",
            )
        ).upper()

        quality = _safe_float(
            acceleration.get(
                "quality"
            )
        )

        weight = (
            quality
            * 15.0
        )

        if (
            accel_direction
            == "BULLISH"
        ):

            bullish_points += (
                weight
            )

            bullish_reasons.append(
                "RS accelerating"
            )

        elif (
            accel_direction
            == "BEARISH"
        ):

            bearish_points += (
                weight
            )

            bearish_reasons.append(
                "RS deteriorating"
            )


    # ======================================
    # LEADERSHIP
    # ======================================

    leadership = stock.get(
        "leadership",
        {},
    )

    leadership_state = str(
        leadership.get(
            "state",
            "NONE",
        )
    ).upper()

    if leadership_state.startswith(
        "BULLISH"
    ):

        bullish_points += 12.0

        bullish_reasons.append(
            leadership_state
        )

    elif leadership_state.startswith(
        "BEARISH"
    ):

        bearish_points += 12.0

        bearish_reasons.append(
            leadership_state
        )


    # ======================================
    # TIME-NORMALIZED RVOL
    # ======================================

    volume_context = stock.get(
        "volume_context",
        {},
    )

    time_volume = volume_context.get(
        "time_normalized",
        {},
    )

    if time_volume.get(
        "available",
        False,
    ):

        rvol = _safe_float(
            time_volume.get(
                "rvol"
            )
        )

    else:

        rvol = _safe_float(
            stock.get(
                "volume_ratio"
            )
        )

    participation_points = 0.0

    if rvol >= 3.0:
        participation_points = 12.0

    elif rvol >= 2.0:
        participation_points = 9.0

    elif rvol >= 1.30:
        participation_points = 5.0


    # ======================================
    # COMPRESSION / EXPANSION
    # ======================================

    compression = stock.get(
        "compression_expansion",
        {},
    )

    compression_state = str(
        compression.get(
            "state",
            "NONE",
        )
    ).upper()

    if (
        compression_state
        == "BULLISH_EXPANSION"
    ):

        bullish_points += (
            16.0
            + participation_points
        )

        bullish_reasons.append(
            "Bullish compression expansion"
        )

    elif (
        compression_state
        == "BEARISH_EXPANSION"
    ):

        bearish_points += (
            16.0
            + participation_points
        )

        bearish_reasons.append(
            "Bearish compression expansion"
        )

    elif (
        compression_state
        == "READY_TO_EXPAND"
    ):

        # Participation is useful here,
        # but direction remains unknown.
        pass


    # ======================================
    # LIQUIDITY SWEEP
    # ======================================

    sweep = stock.get(
        "liquidity_sweep",
        {},
    )

    if sweep.get(
        "strong",
        False,
    ):

        sweep_direction = str(
            sweep.get(
                "direction",
                "NEUTRAL",
            )
        ).upper()

        quality = _safe_float(
            sweep.get(
                "quality"
            )
        )

        weight = (
            10.0
            + quality * 8.0
        )

        if (
            sweep_direction
            == "BULLISH"
        ):

            bullish_points += (
                weight
            )

            bullish_reasons.append(
                "Strong bullish liquidity sweep"
            )

        elif (
            sweep_direction
            == "BEARISH"
        ):

            bearish_points += (
                weight
            )

            bearish_reasons.append(
                "Strong bearish liquidity sweep"
            )


    # ======================================
    # PRICE DIRECTION
    # ======================================

    direction = str(
        stock.get(
            "direction",
            "NEUTRAL",
        )
    ).upper()

    if direction == "BULLISH":

        bullish_points += 8.0

        bullish_reasons.append(
            "Price momentum bullish"
        )

    elif direction == "BEARISH":

        bearish_points += 8.0

        bearish_reasons.append(
            "Price momentum bearish"
        )


    # ======================================
    # MARKET BREADTH
    # ======================================

    breadth_regime = str(
        breadth.get(
            "regime",
            "UNKNOWN",
        )
    ).upper()

    if (
        breadth_regime
        == "STRONG_BULLISH"
    ):

        bullish_points += 8.0

        bullish_reasons.append(
            "Broad bullish market"
        )

    elif breadth_regime == "BULLISH":

        bullish_points += 4.0

    elif (
        breadth_regime
        == "STRONG_BEARISH"
    ):

        bearish_points += 8.0

        bearish_reasons.append(
            "Broad bearish market"
        )

    elif breadth_regime == "BEARISH":

        bearish_points += 4.0


    # ======================================
    # CONTRADICTIONS
    # ======================================

    if (
        bullish_points >= 20
        and bearish_points >= 20
    ):

        contradictions.append(
            "Strong signals exist "
            "on both sides"
        )

    dominant = max(
        bullish_points,
        bearish_points,
    )

    opposing = min(
        bullish_points,
        bearish_points,
    )

    net_points = (
        bullish_points
        - bearish_points
    )


    # ======================================
    # CLASSIFICATION
    # ======================================

    if (
        dominant < 15
    ):

        setup = "NO_CONFLUENCE"

        direction_result = (
            "NEUTRAL"
        )

    elif (
        bullish_points >= 35
        and bullish_points
        >= bearish_points + 15
    ):

        setup = (
            "STRONG_BULLISH_CONFLUENCE"
        )

        direction_result = (
            "BULLISH"
        )

    elif (
        bearish_points >= 35
        and bearish_points
        >= bullish_points + 15
    ):

        setup = (
            "STRONG_BEARISH_CONFLUENCE"
        )

        direction_result = (
            "BEARISH"
        )

    elif (
        bullish_points
        >= bearish_points + 10
    ):

        setup = (
            "BULLISH_CONFLUENCE"
        )

        direction_result = (
            "BULLISH"
        )

    elif (
        bearish_points
        >= bullish_points + 10
    ):

        setup = (
            "BEARISH_CONFLUENCE"
        )

        direction_result = (
            "BEARISH"
        )

    else:

        setup = "CONFLICTED"

        direction_result = (
            "NEUTRAL"
        )


    # ======================================
    # QUALITY
    # ======================================

    evidence_total = (
        bullish_points
        + bearish_points
    )

    if evidence_total > 0:

        agreement = (
            dominant
            / evidence_total
        )

    else:

        agreement = 0.0

    quality = min(
        dominant / 70.0,
        1.0,
    )

    quality *= agreement

    return {
        "setup":
            setup,

        "direction":
            direction_result,

        "quality": round(
            quality,
            3,
        ),

        "bullish_points": round(
            bullish_points,
            2,
        ),

        "bearish_points": round(
            bearish_points,
            2,
        ),

        "net_points": round(
            net_points,
            2,
        ),

        "rvol": round(
            rvol,
            2,
        ),

        "bullish_reasons":
            bullish_reasons,

        "bearish_reasons":
            bearish_reasons,

        "contradictions":
            contradictions,
    }
