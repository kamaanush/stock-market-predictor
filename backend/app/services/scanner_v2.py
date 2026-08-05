from __future__ import annotations

from typing import Any

from ..schemas import ScannerV2Out
from .ai_explainer import build_ai_explanation
from .decision_engine import evaluate_decision


def build_scanner_v2_response(
    result: dict[str, Any],
    interval: str,
) -> ScannerV2Out:
    ema_fast = float(
        result.get("ema_fast", 0)
    )

    ema_slow = float(
        result.get("ema_slow", 0)
    )

    rsi = float(
        result.get("rsi", 0)
    )

    macd_value = float(
        result.get("macd", 0)
    )

    macd_signal = float(
        result.get("macd_signal", 0)
    )

    last_price = float(
        result.get("last_price", 0)
    )

    vwap_value = float(
        result.get("vwap", 0)
    )

    volume_value = float(
        result.get("volume", 0)
    )

    average_volume = float(
        result.get("average_volume", 0)
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

    atr = float(
        result.get("atr", 0)
    )

    supertrend_value = float(
        result.get("supertrend", 0)
    )

    pattern = result.get("pattern")

    pattern_direction = result.get(
        "pattern_direction"
    )

    pattern_confidence = result.get(
        "pattern_confidence"
    )

    pivot_position = result.get(
        "pivot_position"
    )

    action_status = str(
        result.get(
            "action_status",
            "AVOID",
        )
    )

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
        if last_price > vwap_value
        else "BELOW"
        if last_price < vwap_value
        else "AT VWAP"
    )

    high_volume = (
        average_volume > 0
        and volume_value
        >= average_volume * 1.2
    )

    volume_status = (
        "HIGH"
        if high_volume
        else "NORMAL"
    )

    decision = evaluate_decision(
        ema_status=ema_status,
        supertrend_status=supertrend_status,
        adx=adx,
        plus_di=plus_di,
        minus_di=minus_di,
        rsi=rsi,
        macd_status=macd_status,
        vwap_status=vwap_status,
        volume_status=volume_status,
        pivot_position=pivot_position,
        pattern_direction=pattern_direction,
        action_status=action_status,
    )

    entry = result.get("entry_price")
    stoploss = result.get("stoploss")
    target1 = result.get("target1")
    target2 = result.get("target2")

    risk_reward = None

    if (
        entry is not None
        and stoploss is not None
        and target2 is not None
    ):
        risk = abs(
            float(entry)
            - float(stoploss)
        )

        reward = abs(
            float(target2)
            - float(entry)
        )

        if risk > 0:
            risk_reward = (
                f"1:{round(reward / risk, 2)}"
            )

    if decision.confidence >= 90:
        probability_label = "VERY HIGH"

    elif decision.confidence >= 80:
        probability_label = "HIGH"

    elif decision.confidence >= 70:
        probability_label = "MODERATE"

    else:
        probability_label = "LOW"

    ai_explanation = build_ai_explanation(
        symbol=str(result["symbol"]),
        signal=decision.signal,
        confidence=decision.confidence,
        ema_status=ema_status,
        supertrend_status=supertrend_status,
        adx=adx,
        plus_di=plus_di,
        minus_di=minus_di,
        rsi=rsi,
        macd_status=macd_status,
        vwap_status=vwap_status,
        volume_status=volume_status,
        trend_strength=decision.trend_strength,
        action_status=decision.action_status,
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
        pattern=(
            str(pattern)
            if pattern is not None
            else None
        ),
        pattern_direction=(
            str(pattern_direction)
            if pattern_direction is not None
            else None
        ),
        pivot_position=(
            str(pivot_position)
            if pivot_position is not None
            else None
        ),
    )

    return ScannerV2Out(
        symbol=str(
            result["symbol"]
        ),

        signal=decision.signal,

        score=decision.confidence,

        grade=decision.grade,

        trend=str(
            result.get(
                "trend",
                "SIDEWAYS",
            )
        ),

        reason=str(
            result.get(
                "reason",
                "",
            )
        ),

        technical_analysis={
            "ema": ema_status,
            "ema_fast": ema_fast,
            "ema_slow": ema_slow,

            "supertrend": supertrend_status,
            "supertrend_value": (
                supertrend_value
            ),

            "adx": adx,
            "plus_di": plus_di,
            "minus_di": minus_di,

            "trend_strength": (
                decision.trend_strength
            ),

            "rsi": rsi,

            "macd": macd_status,
            "macd_value": macd_value,
            "macd_signal": macd_signal,

            "vwap": vwap_status,
            "vwap_value": vwap_value,

            "volume": volume_status,
            "volume_value": volume_value,
            "average_volume": (
                average_volume
            ),

            "atr": atr,

            "pattern": pattern,

            "pattern_direction": (
                pattern_direction
            ),

            "pattern_confidence": (
                pattern_confidence
            ),
        },
        
                cpr={
            "pivot": float(
                result.get("pivot", 0)
            ),
            "top_central": float(
                result.get("cpr_top", 0)
            ),
            "bottom_central": float(
                result.get("cpr_bottom", 0)
            ),
            "width": float(
                result.get("cpr_width", 0)
            ),
            "width_percent": float(
                result.get(
                    "cpr_width_percent",
                    0,
                )
            ),
            "classification": str(
                result.get(
                    "cpr_classification",
                    "UNKNOWN",
                )
            ),
            "position": str(
                 result.get("pivot_position")
                     or "UNKNOWN"
            ),
        },

        trade_plan={
            "entry": entry,
            "stoploss": stoploss,
            "target1": target1,
            "target2": target2,
            "risk_reward": risk_reward,
        },

        analysis={
            "engine": (
                "DECISION_ENGINE_V1"
            ),

            "confidence": (
                decision.confidence
            ),

            "probability_label": (
                probability_label
            ),

            "risk_label": (
                decision.risk_level
            ),

            "summary": (
                decision.summary
            ),
        },

        ai_analysis={
            "engine": (
                "DETERMINISTIC_EXPLAINER_V1"
            ),

            "market_bias": (
                ai_explanation.market_bias
            ),

            "trend_analysis": (
                ai_explanation.trend_analysis
            ),

            "momentum_analysis": (
                ai_explanation.momentum_analysis
            ),

            "volume_analysis": (
                ai_explanation.volume_analysis
            ),

            "risk_analysis": (
                ai_explanation.risk_analysis
            ),

            "recommendation": (
                ai_explanation.recommendation
            ),

            "overall_summary": (
                ai_explanation.overall_summary
            ),
        },

        execution={
            "status": (
                decision.action_status
            ),

            "timeframe": interval,

            "last_price": last_price,
        },
    )