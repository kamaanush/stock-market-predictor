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


def analyze_trade_direction(
    *,
    stock: dict[str, Any],
    opportunity: dict[str, Any],
    market_breadth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Stage 2 Direction Engine.

    Stage 1 answers:
        Is the stock likely to move?

    Stage 2 answers:
        Is there enough evidence to choose
        bullish or bearish direction?

    It is intentionally conservative.
    """

    opportunity_score = _safe_float(
        opportunity.get(
            "score"
        )
    )

    if opportunity_score < 40:

        return {
            "state":
                "SKIP_LOW_OPPORTUNITY",

            "direction":
                "UNCERTAIN",

            "bullish_points": 0.0,
            "bearish_points": 0.0,

            "margin": 0.0,
            "agreement": 0.0,

            "reasons": [],
        }

    bullish = 0.0
    bearish = 0.0

    bullish_reasons = []
    bearish_reasons = []

    # =====================================
    # RELATIVE STRENGTH
    # =====================================

    rs = stock.get(
        "relative_strength",
        {},
    )

    if rs.get(
        "available",
        False,
    ):

        direction = str(
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
            2.0,
            0.8
            + strength / 1.5,
        )

        if direction == "BULLISH":

            bullish += weight

            bullish_reasons.append(
                "Relative strength bullish"
            )

        elif direction == "BEARISH":

            bearish += weight

            bearish_reasons.append(
                "Relative strength bearish"
            )

    # =====================================
    # RS ACCELERATION
    # =====================================

    acceleration = stock.get(
        "rs_acceleration",
        {},
    )

    if acceleration.get(
        "available",
        False,
    ):

        direction = str(
            acceleration.get(
                "direction",
                "NEUTRAL",
            )
        ).upper()

        quality = min(
            max(
                _safe_float(
                    acceleration.get(
                        "quality"
                    )
                ),
                0.0,
            ),
            1.0,
        )

        weight = (
            quality
            * 2.0
        )

        if direction == "BULLISH":

            bullish += weight

            bullish_reasons.append(
                "RS acceleration bullish"
            )

        elif direction == "BEARISH":

            bearish += weight

            bearish_reasons.append(
                "RS acceleration bearish"
            )

    # =====================================
    # PRICE MOMENTUM
    # =====================================

    price_direction = str(
        stock.get(
            "direction",
            "NEUTRAL",
        )
    ).upper()

    if price_direction == "BULLISH":

        bullish += 1.0

        bullish_reasons.append(
            "Price momentum bullish"
        )

    elif price_direction == "BEARISH":

        bearish += 1.0

        bearish_reasons.append(
            "Price momentum bearish"
        )

    # =====================================
    # EARLY LEADERSHIP
    # =====================================

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

        bullish += 1.5

        bullish_reasons.append(
            "Bullish leadership"
        )

    elif leadership_state.startswith(
        "BEARISH"
    ):

        bearish += 1.5

        bearish_reasons.append(
            "Bearish leadership"
        )

    # =====================================
    # COMPRESSION EXPANSION
    # =====================================

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

        bullish += 2.5

        bullish_reasons.append(
            "Bullish expansion"
        )

    elif (
        compression_state
        == "BEARISH_EXPANSION"
    ):

        bearish += 2.5

        bearish_reasons.append(
            "Bearish expansion"
        )

    # READY_TO_EXPAND intentionally gets
    # no direction points.

    # =====================================
    # LIQUIDITY SWEEP
    # =====================================

    sweep = stock.get(
        "liquidity_sweep",
        {},
    )

    sweep_direction = str(
        sweep.get(
            "direction",
            "NEUTRAL",
        )
    ).upper()

    sweep_state = str(
        sweep.get(
            "state",
            "NONE",
        )
    ).upper()

    if sweep.get(
        "strong",
        False,
    ):

        sweep_weight = 2.5

    elif sweep_state in {
        "BULLISH_LIQUIDITY_SWEEP",
        "BEARISH_LIQUIDITY_SWEEP",
    }:

        sweep_weight = 0.75

    else:

        sweep_weight = 0.0

    if sweep_direction == "BULLISH":

        bullish += sweep_weight

        if sweep_weight > 0:
            bullish_reasons.append(
                "Bullish liquidity sweep"
            )

    elif sweep_direction == "BEARISH":

        bearish += sweep_weight

        if sweep_weight > 0:
            bearish_reasons.append(
                "Bearish liquidity sweep"
            )

    # =====================================
    # BREAKOUT DIRECTION
    # =====================================

    breakout = _safe_float(
        stock.get(
            "breakout_percent"
        )
    )

    if breakout >= 0.05:

        bullish += 1.0

        bullish_reasons.append(
            "Upside breakout"
        )

    elif breakout <= -0.05:

        bearish += 1.0

        bearish_reasons.append(
            "Downside breakout"
        )

    # =====================================
    # MARKET BREADTH
    # Small confirmation only.
    # =====================================

    breadth = (
        market_breadth
        or {}
    )

    breadth_regime = str(
        breadth.get(
            "regime",
            "BALANCED",
        )
    ).upper()

    if breadth_regime == "STRONG_BULLISH":

        bullish += 0.75

    elif breadth_regime == "BULLISH":

        bullish += 0.35

    elif breadth_regime == "STRONG_BEARISH":

        bearish += 0.75

    elif breadth_regime == "BEARISH":

        bearish += 0.35

    # =====================================
    # FINAL DECISION
    # =====================================

    dominant = max(
        bullish,
        bearish,
    )

    opposing = min(
        bullish,
        bearish,
    )

    total = (
        bullish
        + bearish
    )

    margin = (
        dominant
        - opposing
    )

    agreement = (
        dominant / total
        if total > 0
        else 0.0
    )

    direction = "UNCERTAIN"
    state = "UNCERTAIN"

    if (
        bullish > bearish
        and dominant >= 3.0
        and margin >= 1.5
        and agreement >= 0.68
    ):

        direction = "BULLISH"

    elif (
        bearish > bullish
        and dominant >= 3.0
        and margin >= 1.5
        and agreement >= 0.68
    ):

        direction = "BEARISH"

    if direction != "UNCERTAIN":

        if (
            dominant >= 5.0
            and agreement >= 0.80
        ):

            state = (
                "HIGH_CONVICTION_"
                + direction
            )

        else:

            state = (
                "CONFIRMED_"
                + direction
            )

    reasons = (
        bullish_reasons
        if direction == "BULLISH"
        else bearish_reasons
        if direction == "BEARISH"
        else []
    )

    return {
        "state":
            state,

        "direction":
            direction,

        # This is agreement,
        # NOT probability.
        "agreement": round(
            agreement,
            3,
        ),

        "bullish_points": round(
            bullish,
            2,
        ),

        "bearish_points": round(
            bearish,
            2,
        ),

        "margin": round(
            margin,
            2,
        ),

        "opportunity_score": round(
            opportunity_score,
            2,
        ),

        "reasons":
            reasons,

        "bullish_reasons":
            bullish_reasons,

        "bearish_reasons":
            bearish_reasons,
    }
