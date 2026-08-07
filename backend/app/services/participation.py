from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParticipationResult:
    classification: str
    direction: str
    score: int
    volume_ratio: float
    volume_status: str
    vwap_status: str
    confirmation: bool
    summary: str


def clamp(
    value: int,
    minimum: int = -100,
    maximum: int = 100,
) -> int:
    return max(
        minimum,
        min(maximum, value),
    )


def evaluate_participation(
    *,
    volume: float,
    average_volume: float,
    vwap_status: str,
    price_direction: str,
) -> ParticipationResult:
    volume_value = max(
        0.0,
        float(volume),
    )

    average_value = max(
        0.0,
        float(average_volume),
    )

    vwap = vwap_status.upper()
    direction_input = price_direction.upper()

    if average_value > 0:
        volume_ratio = (
            volume_value / average_value
        )
    else:
        volume_ratio = 0.0

    score = 0
    reasons: list[str] = []

    if volume_ratio >= 2.0:
        classification = "VERY HIGH"
        volume_status = "SURGE"
        base_score = 35

        reasons.append(
            f"Volume is {volume_ratio:.2f} times "
            "the recent average"
        )

    elif volume_ratio >= 1.5:
        classification = "HIGH"
        volume_status = "HIGH"
        base_score = 25

        reasons.append(
            f"Volume is {volume_ratio:.2f} times "
            "the recent average"
        )

    elif volume_ratio >= 1.2:
        classification = "ABOVE AVERAGE"
        volume_status = "ELEVATED"
        base_score = 15

        reasons.append(
            f"Volume is {volume_ratio:.2f} times "
            "the recent average"
        )

    elif volume_ratio >= 0.8:
        classification = "NORMAL"
        volume_status = "NORMAL"
        base_score = 5

        reasons.append(
            "Volume is close to its recent average"
        )

    else:
        classification = "LOW"
        volume_status = "LOW"
        base_score = 0

        reasons.append(
            "Volume is below its recent average"
        )

    bullish_alignment = (
        direction_input == "BULLISH"
        and vwap == "ABOVE"
    )

    bearish_alignment = (
        direction_input == "BEARISH"
        and vwap == "BELOW"
    )

    if bullish_alignment:
        direction = "BULLISH"

        if base_score > 0:
            score += base_score
            reasons.append(
                "Price direction and VWAP confirm "
                "bullish participation"
            )
        else:
            reasons.append(
                "Bullish price position lacks "
                "volume confirmation"
            )

    elif bearish_alignment:
        direction = "BEARISH"

        if base_score > 0:
            score -= base_score
            reasons.append(
                "Price direction and VWAP confirm "
                "bearish participation"
            )
        else:
            reasons.append(
                "Bearish price position lacks "
                "volume confirmation"
            )

    else:
        direction = "MIXED"

        if vwap == "ABOVE":
            score += min(
                base_score,
                8,
            )

            reasons.append(
                "Price is above VWAP, but directional "
                "alignment is incomplete"
            )

        elif vwap == "BELOW":
            score -= min(
                base_score,
                8,
            )

            reasons.append(
                "Price is below VWAP, but directional "
                "alignment is incomplete"
            )

        else:
            reasons.append(
                "Price is close to VWAP and participation "
                "direction is unclear"
            )

    confirmation = (
        volume_ratio >= 1.2
        and (
            bullish_alignment
            or bearish_alignment
        )
    )

    if confirmation:
        reasons.append(
            "Volume confirms the directional move"
        )
    else:
        reasons.append(
            "The move does not yet have strong "
            "volume confirmation"
        )

    score = clamp(score)

    summary = (
        f"Participation is {classification.lower()} "
        f"with {direction.lower()} direction. "
        f"Evidence: {' + '.join(reasons)}"
    )

    return ParticipationResult(
        classification=classification,
        direction=direction,
        score=score,
        volume_ratio=round(
            volume_ratio,
            2,
        ),
        volume_status=volume_status,
        vwap_status=vwap,
        confirmation=confirmation,
        summary=summary,
    )