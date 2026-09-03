from __future__ import annotations

from typing import Any, Dict, Optional


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


def analyze_movement_opportunity(
    *,
    stock: Dict[str, Any],
    market_breadth: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:
    """
    Score likelihood of meaningful
    intraday movement.

    IMPORTANT:
    This score intentionally does NOT
    predict bullish or bearish direction.

    Direction is handled separately.
    """

    breadth = (
        market_breadth
        or {}
    )

    score = 0.0
    reasons = []


    # ======================================
    # TIME-NORMALIZED RVOL
    # Maximum: 25
    # ======================================

    volume_context = stock.get(
        "volume_context",
        {},
    )

    normalized = volume_context.get(
        "time_normalized",
        {},
    )

    if normalized.get(
        "available",
        False,
    ):
        rvol = _safe_float(
            normalized.get(
                "rvol"
            )
        )

        volume_source = (
            "TIME_NORMALIZED"
        )

    else:
        rvol = _safe_float(
            stock.get(
                "volume_ratio"
            )
        )

        volume_source = (
            "ROLLING_FALLBACK"
        )

    if rvol >= 3.0:
        rvol_points = 25.0

    elif rvol >= 2.0:
        rvol_points = 20.0

    elif rvol >= 1.30:
        rvol_points = 12.0

    elif rvol >= 1.0:
        rvol_points = 5.0

    else:
        rvol_points = 0.0

    score += rvol_points

    if rvol_points > 0:
        reasons.append(
            f"RVOL {rvol:.2f}x"
        )


    # ======================================
    # RS ACCELERATION MAGNITUDE
    # Maximum: 20
    #
    # Direction is ignored here.
    # ======================================

    acceleration = stock.get(
        "rs_acceleration",
        {},
    )

    acceleration_quality = (
        _safe_float(
            acceleration.get(
                "quality"
            )
        )
        if acceleration.get(
            "available",
            False,
        )
        else 0.0
    )

    acceleration_points = (
        min(
            max(
                acceleration_quality,
                0.0,
            ),
            1.0,
        )
        * 20.0
    )

    score += (
        acceleration_points
    )

    if acceleration_points >= 8:
        reasons.append(
            "Strong RS acceleration"
        )


    # ======================================
    # RELATIVE-STRENGTH DISLOCATION
    # Maximum: 15
    #
    # Large positive OR negative separation
    # from NIFTY can indicate opportunity.
    # ======================================

    rs = stock.get(
        "relative_strength",
        {},
    )

    rs_strength = abs(
        _safe_float(
            rs.get(
                "strength"
            )
        )
    )

    rs_points = (
        min(
            rs_strength
            / 1.50,
            1.0,
        )
        * 15.0
    )

    score += rs_points

    if rs_points >= 8:
        reasons.append(
            "Large market-relative move"
        )


    # ======================================
    # COMPRESSION / EXPANSION
    # Maximum: 20
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

    compression_points = 0.0

    if compression_state in {
        "BULLISH_EXPANSION",
        "BEARISH_EXPANSION",
    }:

        compression_points = 20.0

        reasons.append(
            "Compression released"
        )

    elif (
        compression_state
        == "READY_TO_EXPAND"
    ):

        compression_points = 18.0

        reasons.append(
            "Ready to expand"
        )

    elif (
        compression_state
        == "COMPRESSION"
    ):

        compression_points = 7.0

    score += (
        compression_points
    )


    # ======================================
    # LIQUIDITY SWEEP
    # Maximum: 15
    # ======================================

    sweep = stock.get(
        "liquidity_sweep",
        {},
    )

    sweep_state = str(
        sweep.get(
            "state",
            "NONE",
        )
    ).upper()

    sweep_quality = _safe_float(
        sweep.get(
            "quality"
        )
    )

    sweep_points = 0.0

    if sweep.get(
        "strong",
        False,
    ):

        sweep_points = (
            10.0
            + min(
                max(
                    sweep_quality,
                    0.0,
                ),
                1.0,
            )
            * 5.0
        )

        reasons.append(
            "Strong liquidity sweep"
        )

    elif sweep_state in {
        "BULLISH_LIQUIDITY_SWEEP",
        "BEARISH_LIQUIDITY_SWEEP",
        "TWO_SIDED_SWEEP",
    }:

        sweep_points = (
            min(
                max(
                    sweep_quality,
                    0.0,
                ),
                1.0,
            )
            * 7.0
        )

    score += sweep_points


    # ======================================
    # MARKET PARTICIPATION
    # Maximum: 5
    #
    # Use magnitude, not direction.
    # ======================================

    net_breadth = abs(
        _safe_float(
            breadth.get(
                "net_breadth_percent"
            )
        )
    )

    breadth_points = (
        min(
            net_breadth
            / 50.0,
            1.0,
        )
        * 5.0
    )

    score += breadth_points


    # ======================================
    # FINAL CLASSIFICATION
    # ======================================

    score = min(
        max(
            score,
            0.0,
        ),
        100.0,
    )

    if score >= 70:
        state = (
            "EXTREME_OPPORTUNITY"
        )

    elif score >= 55:
        state = (
            "HIGH_OPPORTUNITY"
        )

    elif score >= 40:
        state = (
            "ELEVATED_OPPORTUNITY"
        )

    else:
        state = (
            "NORMAL"
        )


    # ======================================
    # SECONDARY DIRECTION HINT
    #
    # Not part of opportunity score.
    # ======================================

    bullish_votes = 0
    bearish_votes = 0

    for value in [
        str(
            stock.get(
                "direction",
                "NEUTRAL",
            )
        ).upper(),

        str(
            rs.get(
                "direction",
                "NEUTRAL",
            )
        ).upper(),

        str(
            acceleration.get(
                "direction",
                "NEUTRAL",
            )
        ).upper(),

        str(
            sweep.get(
                "direction",
                "NEUTRAL",
            )
        ).upper(),
    ]:

        if value == "BULLISH":
            bullish_votes += 1

        elif value == "BEARISH":
            bearish_votes += 1

    if (
        bullish_votes
        >= bearish_votes + 2
    ):

        direction_hint = (
            "BULLISH"
        )

    elif (
        bearish_votes
        >= bullish_votes + 2
    ):

        direction_hint = (
            "BEARISH"
        )

    else:

        direction_hint = (
            "UNCERTAIN"
        )

    direction_agreement = (
        max(
            bullish_votes,
            bearish_votes,
        )
        / max(
            bullish_votes
            + bearish_votes,
            1,
        )
    )

    return {
        "score": round(
            score,
            2,
        ),

        "state":
            state,

        "direction_hint":
            direction_hint,

        "direction_agreement": round(
            direction_agreement,
            3,
        ),

        "bullish_votes":
            bullish_votes,

        "bearish_votes":
            bearish_votes,

        "rvol": round(
            rvol,
            2,
        ),

        "volume_source":
            volume_source,

        "components": {
            "rvol":
                round(
                    rvol_points,
                    2,
                ),

            "rs_acceleration":
                round(
                    acceleration_points,
                    2,
                ),

            "relative_strength":
                round(
                    rs_points,
                    2,
                ),

            "compression":
                round(
                    compression_points,
                    2,
                ),

            "liquidity_sweep":
                round(
                    sweep_points,
                    2,
                ),

            "breadth":
                round(
                    breadth_points,
                    2,
                ),
        },

        "reasons":
            reasons,
    }
