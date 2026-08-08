from __future__ import annotations

from dataclasses import asdict
from typing import Any, Optional

from .breakout_readiness import (
    evaluate_breakout_readiness,
)
from .buyer_seller_pressure import (
    evaluate_buyer_seller_pressure,
)
from .candle_flow import (
    CandleFlowResult,
    evaluate_candle_flow,
)
from .decision_pipeline import (
    evaluate_pipeline,
)
from .location_engine import (
    evaluate_location,
)
from .market_structure import (
    evaluate_market_structure,
)
from .momentum import (
    evaluate_momentum,
)
from .participation import (
    evaluate_participation,
)
from .risk_engine import (
    evaluate_risk,
)
from .scanner import (
    get_usable_dataframe,
)
from .trend_strength import (
    evaluate_trend_strength,
)

from .confidence_engine import (
    evaluate_confidence,
)

def _neutral_candle_flow() -> CandleFlowResult:
    return CandleFlowResult(
        direction="MIXED",
        strength="WEAK",
        score=0,
        higher_highs=0,
        higher_lows=0,
        lower_highs=0,
        lower_lows=0,
        bullish_candles=0,
        bearish_candles=0,
        body_expansion=False,
        volume_building=False,
        momentum_accelerating=False,
        close_quality="NEUTRAL",
        wick_pressure="BALANCED",
        rsi_flow="UNKNOWN",
        macd_flow="UNKNOWN",
        vwap_flow="UNKNOWN",
        summary=(
            "Candle-flow history is unavailable "
            "for this scan."
        ),
    )


def build_pipeline_analysis(
    result: dict[str, Any],
    candles: Optional[
        list[dict[str, Any]]
    ] = None,
) -> dict[str, Any]:

    # ---------------------------------------------------------
    # RAW VALUES
    # ---------------------------------------------------------

    ema_fast = float(
        result.get("ema_fast", 0)
    )

    ema_slow = float(
        result.get("ema_slow", 0)
    )

    macd_value = float(
        result.get("macd", 0)
    )

    macd_signal = float(
        result.get("macd_signal", 0)
    )

    current_price = float(
        result.get("last_price", 0)
    )

    vwap_value = float(
        result.get("vwap", 0)
    )

    volume = float(
        result.get("volume", 0)
    )

    average_volume = float(
        result.get(
            "average_volume",
            0,
        )
    )

    adx = float(
        result.get("adx", 0)
    )

    plus_di = float(
        result.get("plus_di", 0)
    )

    minus_di = float(
        result.get("minus_di", 0)
    )

    rsi = float(
        result.get("rsi", 0)
    )

    # ---------------------------------------------------------
    # LATEST CANDLE
    # ---------------------------------------------------------

    latest_candle = (
        candles[-1]
        if candles
        else {}
    )

    open_price = float(
        latest_candle.get(
            "open",
            current_price,
        )
    )

    high_price = float(
        latest_candle.get(
            "high",
            current_price,
        )
    )

    low_price = float(
        latest_candle.get(
            "low",
            current_price,
        )
    )

    close_price = float(
        latest_candle.get(
            "close",
            current_price,
        )
    )

    # ---------------------------------------------------------
    # TRADE LEVELS
    # ---------------------------------------------------------

    entry = result.get(
        "entry_price"
    )

    stoploss = result.get(
        "stoploss"
    )

    target1 = result.get(
        "target1"
    )

    target2 = result.get(
        "target2"
    )

    action_status = str(
        result.get(
            "action_status",
            "AVOID",
        )
    ).upper()

    cpr_position = str(
        result.get(
            "pivot_position"
        )
        or "UNKNOWN"
    ).upper()

    # ---------------------------------------------------------
    # INDICATOR STATUS
    # ---------------------------------------------------------

    ema_status = (
        "BUY"
        if ema_fast > ema_slow
        else "SELL"
        if ema_fast < ema_slow
        else "NEUTRAL"
    )

    supertrend_status = (
        "BUY"
        if bool(
            result.get(
                "supertrend_direction",
                True,
            )
        )
        else "SELL"
    )

    macd_status = (
        "BUY"
        if macd_value > macd_signal
        else "SELL"
        if macd_value < macd_signal
        else "NEUTRAL"
    )

    vwap_status = (
        "ABOVE"
        if current_price > vwap_value
        else "BELOW"
        if current_price < vwap_value
        else "AT VWAP"
    )

    # ---------------------------------------------------------
    # 1. MARKET STRUCTURE
    # ---------------------------------------------------------

    market = evaluate_market_structure(
        ema_status=ema_status,
        supertrend_status=(
            supertrend_status
        ),
        vwap_status=vwap_status,
        cpr_position=cpr_position,
    )

    # ---------------------------------------------------------
    # 2. TREND STRENGTH
    # ---------------------------------------------------------

    trend = evaluate_trend_strength(
        adx=adx,
        plus_di=plus_di,
        minus_di=minus_di,
    )

    # ---------------------------------------------------------
    # 3. MOMENTUM
    # ---------------------------------------------------------

    momentum = evaluate_momentum(
        rsi=rsi,
        macd_status=macd_status,
    )

    # ---------------------------------------------------------
    # 4. PARTICIPATION
    # ---------------------------------------------------------

    participation = (
        evaluate_participation(
            volume=volume,
            average_volume=(
                average_volume
            ),
            vwap_status=(
                vwap_status
            ),
            price_direction=(
                market.bias
            ),
        )
    )

    # ---------------------------------------------------------
    # 5. BUYER / SELLER PRESSURE
    # ---------------------------------------------------------

    buyer_seller_pressure = (
        evaluate_buyer_seller_pressure(
            open_price=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            average_volume=(
                average_volume
            ),
            vwap=vwap_value,
            ema_status=ema_status,
            supertrend_status=(
                supertrend_status
            ),
            rsi=rsi,
            macd_status=(
                macd_status
            ),
        )
    )

    # ---------------------------------------------------------
    # 6. CANDLE FLOW
    # ---------------------------------------------------------

    candle_flow = (
        _neutral_candle_flow()
    )

    if candles and len(candles) >= 3:
        try:
            usable = (
                get_usable_dataframe(
                    candles
                )
            )

            lookback = min(
                6,
                len(usable),
            )

            recent = (
                usable.iloc[
                    -lookback:
                ]
            )

            recent_candles = (
                recent[
                    [
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                    ]
                ]
                .to_dict(
                    orient="records"
                )
            )

            rsi_values = (
                recent["rsi"]
                .astype(float)
                .tolist()
            )

            macd_histogram_values = (
                recent[
                    "macd_histogram"
                ]
                .astype(float)
                .tolist()
            )

            vwap_values = (
                recent["vwap"]
                .astype(float)
                .tolist()
            )

            candle_flow = (
                evaluate_candle_flow(
                    candles=(
                        recent_candles
                    ),
                    rsi_values=(
                        rsi_values
                    ),
                    macd_histogram_values=(
                        macd_histogram_values
                    ),
                    vwap_values=(
                        vwap_values
                    ),
                    lookback=lookback,
                )
            )

        except Exception:
            candle_flow = (
                _neutral_candle_flow()
            )

    # ---------------------------------------------------------
    # PROVISIONAL SIGNAL
    # ---------------------------------------------------------

    provisional_signal = (
        "BUY"
        if (
            market.bias
            == "BULLISH"
            and trend.direction
            == "BULLISH"
        )
        else "SELL"
        if (
            market.bias
            == "BEARISH"
            and trend.direction
            == "BEARISH"
        )
        else "WAIT"
    )

    # ---------------------------------------------------------
    # 7. LOCATION
    # ---------------------------------------------------------

    location = evaluate_location(
        current_price=(
            current_price
        ),
        signal=(
            provisional_signal
        ),
        cpr_position=(
            cpr_position
        ),

        entry=(
            float(entry)
            if entry is not None
            else None
        ),

        stoploss=(
            float(stoploss)
            if stoploss is not None
            else None
        ),

        target1=(
            float(target1)
            if target1 is not None
            else None
        ),

        target2=(
            float(target2)
            if target2 is not None
            else None
        ),
    )

    # ---------------------------------------------------------
    # 8. RISK
    # ---------------------------------------------------------

    risk = evaluate_risk(
        current_price=(
            current_price
        ),

        signal=(
            provisional_signal
        ),

        trend_strength=(
            trend.classification
        ),

        momentum_classification=(
            momentum.classification
        ),

        participation_confirmation=(
            participation.confirmation
        ),

        location_classification=(
            location.classification
        ),

        action_status=(
            action_status
        ),

        entry=(
            float(entry)
            if entry is not None
            else None
        ),

        stoploss=(
            float(stoploss)
            if stoploss is not None
            else None
        ),

        target2=(
            float(target2)
            if target2 is not None
            else None
        ),
    )

    # ---------------------------------------------------------
    # 9. FINAL DECISION
    # ---------------------------------------------------------

    decision = evaluate_pipeline(
        market=market,
        trend=trend,
        momentum=momentum,
        participation=(
            participation
        ),
        location=location,
        risk=risk,
    )

    # ---------------------------------------------------------
    # 10. BREAKOUT READINESS
    # ---------------------------------------------------------

    breakout_readiness = (
        evaluate_breakout_readiness(
            signal=(
                decision.signal
            ),

            current_price=(
                current_price
            ),

            entry=(
                float(entry)
                if entry is not None
                else None
            ),

            buyer_seller_pressure=(
                buyer_seller_pressure
            ),

            candle_flow=(
                candle_flow
            ),

            trend_strength=(
                trend.classification
            ),

            participation_confirmation=(
                participation.confirmation
            ),

            cpr_position=(
                cpr_position
            ),

            vwap_status=(
                vwap_status
            ),

            action_status=(
                decision.action
            ),
        )
    )
    # ---------------------------------------------------------
    # 11. MASTER CONFIDENCE ENGINE
    # ---------------------------------------------------------

    confidence = evaluate_confidence(
        signal=decision.signal,

        market_structure_score=(
            market.score
        ),

        trend_score=(
            trend.score
        ),

        momentum_score=(
            momentum.score
        ),

        participation_confirmation=(
            participation.confirmation
        ),

        buyer_score=(
            buyer_seller_pressure
            .buyers_score
        ),

        seller_score=(
            buyer_seller_pressure
            .sellers_score
        ),

        candle_flow_direction=(
            candle_flow.direction
        ),

        candle_flow_score=(
            candle_flow.score
        ),

        breakout_readiness_score=(
            breakout_readiness
            .readiness_score
        ),

        risk_level=(
            risk.level
        ),
    )
    # ---------------------------------------------------------
    # RESPONSE
    # ---------------------------------------------------------

    return {
        "decision": (
            asdict(decision)
        ),

        "market_structure": (
            asdict(market)
        ),

        "trend_strength": (
            asdict(trend)
        ),

        "momentum": (
            asdict(momentum)
        ),

        "participation": (
            asdict(participation)
        ),

        "buyer_seller_pressure": (
            asdict(
                buyer_seller_pressure
            )
        ),

        "candle_flow": (
            asdict(
                candle_flow
            )
        ),

        "location": (
            asdict(location)
        ),

        "risk": (
            asdict(risk)
        ),

        "breakout_readiness": (
            asdict(
                breakout_readiness
            )
        ),
                "confidence": (
            asdict(confidence)
        ),
    }