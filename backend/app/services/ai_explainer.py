from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AIExplanation:
    market_bias: str
    trend_analysis: str
    momentum_analysis: str
    volume_analysis: str
    risk_analysis: str
    recommendation: str
    overall_summary: str


def money(value: Optional[float]) -> str:
    if value is None:
        return "not available"

    return f"₹{value:,.2f}"


def build_ai_explanation(
    *,
    symbol: str,
    signal: str,
    confidence: int,
    ema_status: str,
    supertrend_status: str,
    adx: float,
    plus_di: float,
    minus_di: float,
    rsi: float,
    macd_status: str,
    vwap_status: str,
    volume_status: str,
    trend_strength: str,
    action_status: str,
    entry: Optional[float],
    stoploss: Optional[float],
    target1: Optional[float],
    target2: Optional[float],
    pattern: Optional[str] = None,
    pattern_direction: Optional[str] = None,
    pivot_position: Optional[str] = None,
) -> AIExplanation:
    normalized_signal = signal.upper()
    normalized_ema = ema_status.upper()
    normalized_supertrend = supertrend_status.upper()
    normalized_macd = macd_status.upper()
    normalized_vwap = vwap_status.upper()
    normalized_volume = volume_status.upper()
    normalized_strength = trend_strength.upper()
    normalized_action = action_status.upper()

    if normalized_signal == "BUY":
        market_bias = "Bullish"
    elif normalized_signal == "SELL":
        market_bias = "Bearish"
    else:
        market_bias = "Neutral"

    trend_parts: list[str] = []

    if (
        normalized_ema == "BUY"
        and normalized_supertrend == "BUY"
    ):
        trend_parts.append(
            "EMA 9 is above EMA 21 and SuperTrend is bullish, "
            "showing alignment in the upward trend."
        )
    elif (
        normalized_ema == "SELL"
        and normalized_supertrend == "SELL"
    ):
        trend_parts.append(
            "EMA 9 is below EMA 21 and SuperTrend is bearish, "
            "showing alignment in the downward trend."
        )
    else:
        trend_parts.append(
            "EMA and SuperTrend are not fully aligned, "
            "so the directional setup is mixed."
        )

    if adx >= 40:
        trend_parts.append(
            f"ADX at {adx:.1f} indicates a very strong trend."
        )
    elif adx >= 25:
        trend_parts.append(
            f"ADX at {adx:.1f} confirms a strong trend."
        )
    elif adx >= 20:
        trend_parts.append(
            f"ADX at {adx:.1f} shows a developing trend."
        )
    else:
        trend_parts.append(
            f"ADX at {adx:.1f} indicates a weak or sideways trend."
        )

    if plus_di > minus_di:
        trend_parts.append(
            f"+DI at {plus_di:.1f} is above -DI at {minus_di:.1f}, "
            "supporting bullish directional strength."
        )
    elif minus_di > plus_di:
        trend_parts.append(
            f"-DI at {minus_di:.1f} is above +DI at {plus_di:.1f}, "
            "supporting bearish directional strength."
        )
    else:
        trend_parts.append(
            "+DI and -DI are balanced, so directional strength is unclear."
        )

    if pivot_position:
        trend_parts.append(
            f"Price is currently positioned {pivot_position.lower()}."
        )

    trend_analysis = " ".join(trend_parts)

    momentum_parts: list[str] = []

    if rsi >= 70:
        momentum_parts.append(
            f"RSI at {rsi:.1f} is overbought, so bullish momentum is strong "
            "but the chance of a pullback is higher."
        )
    elif rsi >= 60:
        momentum_parts.append(
            f"RSI at {rsi:.1f} shows healthy bullish momentum "
            "without being deeply overbought."
        )
    elif rsi <= 30:
        momentum_parts.append(
            f"RSI at {rsi:.1f} is oversold, which may indicate selling exhaustion "
            "but still requires reversal confirmation."
        )
    elif rsi <= 40:
        momentum_parts.append(
            f"RSI at {rsi:.1f} shows weak momentum and continued selling pressure."
        )
    else:
        momentum_parts.append(
            f"RSI at {rsi:.1f} is neutral."
        )

    if normalized_macd == "BUY":
        momentum_parts.append(
            "MACD is bullish and supports positive momentum."
        )
    elif normalized_macd == "SELL":
        if normalized_signal == "BUY":
            momentum_parts.append(
                "MACD remains bearish, suggesting a short-term pullback "
                "inside the broader bullish setup."
            )
        elif normalized_signal == "SELL":
            momentum_parts.append(
                "MACD is bearish and confirms downside momentum."
            )
        else:
            momentum_parts.append(
                "MACD is bearish and limits confidence in an immediate long trade."
            )
    else:
        momentum_parts.append(
            "MACD is neutral and does not provide strong momentum confirmation."
        )

    if pattern:
        if pattern_direction == "BULLISH":
            momentum_parts.append(
                f"The detected {pattern.lower()} pattern adds bullish confirmation."
            )
        elif pattern_direction == "BEARISH":
            momentum_parts.append(
                f"The detected {pattern.lower()} pattern adds bearish confirmation."
            )
        else:
            momentum_parts.append(
                f"The detected {pattern.lower()} pattern is neutral."
            )

    momentum_analysis = " ".join(momentum_parts)

    volume_parts: list[str] = []

    if normalized_volume == "HIGH":
        volume_parts.append(
            "Volume is above its recent average, increasing the reliability "
            "of the current price move."
        )
    else:
        volume_parts.append(
            "Volume is near normal levels, so the setup does not yet have "
            "strong volume confirmation."
        )

    if normalized_vwap == "ABOVE":
        volume_parts.append(
            "Price is above VWAP, which supports intraday bullish control."
        )
    elif normalized_vwap == "BELOW":
        volume_parts.append(
            "Price is below VWAP, which supports intraday bearish control."
        )
    else:
        volume_parts.append(
            "Price is close to VWAP, indicating a balanced intraday market."
        )

    volume_analysis = " ".join(volume_parts)

    risk_parts: list[str] = []

    if normalized_strength == "WEAK":
        risk_parts.append(
            "Trend strength is weak, so false breakouts and sideways movement "
            "remain significant risks."
        )
    elif normalized_strength == "DEVELOPING":
        risk_parts.append(
            "Trend strength is developing, so confirmation is still important."
        )
    else:
        risk_parts.append(
            "Trend strength is strong, but execution discipline is still required."
        )

    if normalized_action in {
        "WAIT BREAKOUT",
        "WAIT BREAKDOWN",
    }:
        risk_parts.append(
            "The setup is not active yet and should only be considered "
            "after the trigger level is confirmed."
        )
    elif normalized_action == "EXTENDED":
        risk_parts.append(
            "Price is already extended beyond the preferred entry zone, "
            "which increases chasing risk."
        )
    elif normalized_action == "AVOID":
        risk_parts.append(
            "The setup does not currently meet the minimum execution conditions."
        )
    else:
        risk_parts.append(
            "The setup is active, but the stop-loss must be respected."
        )

    if confidence >= 95:
        risk_parts.append(
            "The raw rule score is extremely high, but this should not be treated "
            "as a guaranteed probability of success."
        )

    risk_analysis = " ".join(risk_parts)

    if normalized_signal == "BUY":
        if normalized_action == "WAIT BREAKOUT":
            recommendation = (
                f"Wait for a confirmed move above {money(entry)} before entering. "
                f"Use {money(stoploss)} as the stop-loss, "
                f"with targets at {money(target1)} and {money(target2)}."
            )
        elif normalized_action == "ACTIVE":
            recommendation = (
                f"The long setup is active near {money(entry)}. "
                f"Maintain the stop-loss at {money(stoploss)} and monitor "
                f"{money(target1)} and {money(target2)} as profit zones."
            )
        elif normalized_action == "EXTENDED":
            recommendation = (
                "Avoid chasing the current move. Wait for a pullback or a new setup."
            )
        else:
            recommendation = (
                "Keep the stock on the watchlist and wait for stronger confirmation."
            )

    elif normalized_signal == "SELL":
        if normalized_action == "WAIT BREAKDOWN":
            recommendation = (
                f"Wait for a confirmed move below {money(entry)} before entering short. "
                f"Use {money(stoploss)} as the stop-loss, "
                f"with targets at {money(target1)} and {money(target2)}."
            )
        elif normalized_action == "ACTIVE":
            recommendation = (
                f"The short setup is active near {money(entry)}. "
                f"Maintain the stop-loss at {money(stoploss)} and monitor "
                f"{money(target1)} and {money(target2)} as profit zones."
            )
        elif normalized_action == "EXTENDED":
            recommendation = (
                "Avoid entering after an extended decline. Wait for a fresh breakdown setup."
            )
        else:
            recommendation = (
                "Keep the stock under observation and wait for stronger bearish confirmation."
            )

    else:
        recommendation = (
            "No immediate trade is recommended. Wait until trend, momentum, "
            "and execution conditions align."
        )

    overall_summary = (
        f"{symbol.upper()} has a {market_bias.lower()} bias with a rule-based "
        f"confidence score of {confidence}. {trend_analysis} "
        f"{momentum_analysis} {recommendation}"
    )

    return AIExplanation(
        market_bias=market_bias,
        trend_analysis=trend_analysis,
        momentum_analysis=momentum_analysis,
        volume_analysis=volume_analysis,
        risk_analysis=risk_analysis,
        recommendation=recommendation,
        overall_summary=overall_summary,
    )