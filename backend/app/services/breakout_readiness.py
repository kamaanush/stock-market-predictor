from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .buyer_seller_pressure import (
    BuyerSellerPressureResult,
)
from .candle_flow import (
    CandleFlowResult,
)


@dataclass(frozen=True)
class BreakoutReadinessResult:
    direction: str
    status: str
    readiness_score: int

    distance_to_trigger_percent: Optional[float]

    buyers_confirming: bool
    candle_flow_confirming: bool
    volume_confirming: bool
    trend_confirming: bool
    vwap_confirming: bool
    location_confirming: bool

    trigger_price: Optional[float]

    summary: str


def clamp(
    value: int,
    minimum: int = 0,
    maximum: int = 100,
) -> int:
    return max(
        minimum,
        min(maximum, value),
    )


def distance_percent(
    current_price: float,
    trigger_price: Optional[float],
) -> Optional[float]:
    if (
        trigger_price is None
        or current_price <= 0
    ):
        return None

    return abs(
        current_price
        - float(trigger_price)
    ) / current_price * 100


def evaluate_breakout_readiness(
    *,
    signal: str,
    current_price: float,
    entry: Optional[float],

    buyer_seller_pressure: (
        BuyerSellerPressureResult
    ),

    candle_flow: CandleFlowResult,

    trend_strength: str,

    participation_confirmation: bool,

    cpr_position: str,

    vwap_status: str,

    action_status: str,
) -> BreakoutReadinessResult:

    normalized_signal = (
        signal.upper()
    )

    normalized_trend = (
        trend_strength.upper()
    )

    normalized_cpr = (
        cpr_position.upper()
        if cpr_position
        else "UNKNOWN"
    )

    normalized_vwap = (
        vwap_status.upper()
    )

    normalized_action = (
        action_status.upper()
    )

    price = float(
        current_price
    )

    score = 0
    reasons: list[str] = []

    # -------------------------------------------------
    # DIRECTION
    # -------------------------------------------------

    if normalized_signal == "BUY":
        direction = "BULLISH"

    elif normalized_signal == "SELL":
        direction = "BEARISH"

    else:
        direction = "NEUTRAL"

    # -------------------------------------------------
    # DISTANCE TO TRIGGER - MAX 25
    # -------------------------------------------------

    trigger_distance = distance_percent(
        price,
        entry,
    )

    if trigger_distance is None:
        reasons.append(
            "Breakout trigger level is unavailable"
        )

    elif trigger_distance <= 0.10:
        score += 25

        reasons.append(
            "Price is extremely close "
            "to the trigger level"
        )

    elif trigger_distance <= 0.25:
        score += 20

        reasons.append(
            "Price is very close "
            "to the trigger level"
        )

    elif trigger_distance <= 0.50:
        score += 12

        reasons.append(
            "Price is approaching "
            "the trigger level"
        )

    elif trigger_distance <= 1.00:
        score += 5

        reasons.append(
            "Price is within range "
            "of the trigger"
        )

    else:
        reasons.append(
            "Price remains relatively far "
            "from the trigger"
        )

    # -------------------------------------------------
    # BUYER / SELLER PRESSURE - MAX 20
    # -------------------------------------------------

    buyers_confirming = False

    if direction == "BULLISH":
        buyers_confirming = (
            buyer_seller_pressure.buyers_score
            >= 65
        )

        if (
            buyer_seller_pressure.buyers_score
            >= 80
        ):
            score += 20

            reasons.append(
                "Buyer dominance is very strong"
            )

        elif (
            buyer_seller_pressure.buyers_score
            >= 65
        ):
            score += 14

            reasons.append(
                "Buyers are dominating"
            )

        elif (
            buyer_seller_pressure.buyers_score
            >= 55
        ):
            score += 7

            reasons.append(
                "Buying pressure is moderately positive"
            )

        else:
            reasons.append(
                "Buyer pressure is insufficient"
            )

    elif direction == "BEARISH":
        buyers_confirming = (
            buyer_seller_pressure.sellers_score
            >= 65
        )

        if (
            buyer_seller_pressure.sellers_score
            >= 80
        ):
            score += 20

            reasons.append(
                "Seller dominance is very strong"
            )

        elif (
            buyer_seller_pressure.sellers_score
            >= 65
        ):
            score += 14

            reasons.append(
                "Sellers are dominating"
            )

        elif (
            buyer_seller_pressure.sellers_score
            >= 55
        ):
            score += 7

            reasons.append(
                "Selling pressure is moderately strong"
            )

        else:
            reasons.append(
                "Seller pressure is insufficient"
            )

    # -------------------------------------------------
    # CANDLE FLOW - MAX 20
    # -------------------------------------------------

    candle_flow_confirming = False

    if direction == "BULLISH":
        candle_flow_confirming = (
            candle_flow.direction
            == "BULLISH"
        )

        if (
            candle_flow.direction
            == "BULLISH"
            and candle_flow.score >= 70
        ):
            score += 20

            reasons.append(
                "Candle flow strongly confirms "
                "bullish continuation"
            )

        elif (
            candle_flow.direction
            == "BULLISH"
            and candle_flow.score >= 40
        ):
            score += 12

            reasons.append(
                "Candle flow supports "
                "bullish continuation"
            )

    elif direction == "BEARISH":
        candle_flow_confirming = (
            candle_flow.direction
            == "BEARISH"
        )

        if (
            candle_flow.direction
            == "BEARISH"
            and candle_flow.score <= -70
        ):
            score += 20

            reasons.append(
                "Candle flow strongly confirms "
                "bearish continuation"
            )

        elif (
            candle_flow.direction
            == "BEARISH"
            and candle_flow.score <= -40
        ):
            score += 12

            reasons.append(
                "Candle flow supports "
                "bearish continuation"
            )

    # -------------------------------------------------
    # VOLUME - MAX 10
    # -------------------------------------------------

    volume_confirming = (
        participation_confirmation
        or candle_flow.volume_building
    )

    if (
        participation_confirmation
        and candle_flow.volume_building
    ):
        score += 10

        reasons.append(
            "Volume confirmation and "
            "volume expansion are both present"
        )

    elif volume_confirming:
        score += 6

        reasons.append(
            "Volume conditions are improving"
        )

    else:
        reasons.append(
            "Volume confirmation is still weak"
        )

    # -------------------------------------------------
    # TREND STRENGTH - MAX 10
    # -------------------------------------------------

    trend_confirming = (
        normalized_trend
        in {
            "VERY STRONG",
            "STRONG",
        }
    )

    if normalized_trend == "VERY STRONG":
        score += 10

        reasons.append(
            "Trend strength is very strong"
        )

    elif normalized_trend == "STRONG":
        score += 8

        reasons.append(
            "Trend strength is strong"
        )

    elif normalized_trend == "DEVELOPING":
        score += 3

        reasons.append(
            "Trend is still developing"
        )

    else:
        reasons.append(
            "Trend strength is weak"
        )

    # -------------------------------------------------
    # VWAP - MAX 8
    # -------------------------------------------------

    if direction == "BULLISH":
        vwap_confirming = (
            normalized_vwap == "ABOVE"
        )

    elif direction == "BEARISH":
        vwap_confirming = (
            normalized_vwap == "BELOW"
        )

    else:
        vwap_confirming = False

    if vwap_confirming:
        score += 8

        reasons.append(
            "VWAP supports the breakout direction"
        )

    else:
        reasons.append(
            "VWAP does not fully confirm "
            "the breakout direction"
        )

    # -------------------------------------------------
    # CPR / LOCATION - MAX 7
    # -------------------------------------------------

    if direction == "BULLISH":
        location_confirming = (
            normalized_cpr
            == "ABOVE CPR"
        )

    elif direction == "BEARISH":
        location_confirming = (
            normalized_cpr
            == "BELOW CPR"
        )

    else:
        location_confirming = False

    if location_confirming:
        score += 7

        reasons.append(
            "CPR location supports "
            "the breakout direction"
        )

    # -------------------------------------------------
    # ACTION STATUS
    # -------------------------------------------------

    if normalized_action in {
        "WAIT BREAKOUT",
        "WAIT BREAKDOWN",
    }:
        reasons.append(
            "The setup is waiting "
            "for trigger confirmation"
        )

    elif normalized_action == "ACTIVE":
        score += 5

        reasons.append(
            "The breakout trigger "
            "has already activated"
        )

    # -------------------------------------------------
    # FINAL SCORE
    # -------------------------------------------------

    score = clamp(
        score
    )

    # -------------------------------------------------
    # STATUS
    # -------------------------------------------------

    if direction == "NEUTRAL":
        status = "NO SETUP"

    elif normalized_action == "ACTIVE":
        if score >= 70:
            status = "BREAKOUT CONFIRMED"
        else:
            status = "ACTIVE - WEAK CONFIRMATION"

    elif score >= 85:
        status = "VERY HIGH READINESS"

    elif score >= 70:
        status = "HIGH READINESS"

    elif score >= 55:
        status = "WATCH BREAKOUT"

    elif score >= 40:
        status = "DEVELOPING"

    else:
        status = "LOW READINESS"

    # -------------------------------------------------
    # SUMMARY
    # -------------------------------------------------

    summary = (
        f"{direction.lower()} breakout readiness "
        f"is {status.lower()} with a score of "
        f"{score}/100. "
        f"Evidence: {' + '.join(reasons)}"
    )

    return BreakoutReadinessResult(
        direction=direction,

        status=status,

        readiness_score=score,

        distance_to_trigger_percent=(
            round(
                trigger_distance,
                3,
            )
            if trigger_distance
            is not None
            else None
        ),

        buyers_confirming=(
            buyers_confirming
        ),

        candle_flow_confirming=(
            candle_flow_confirming
        ),

        volume_confirming=(
            volume_confirming
        ),

        trend_confirming=(
            trend_confirming
        ),

        vwap_confirming=(
            vwap_confirming
        ),

        location_confirming=(
            location_confirming
        ),

        trigger_price=(
            float(entry)
            if entry is not None
            else None
        ),

        summary=summary,
    )