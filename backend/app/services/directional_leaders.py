from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def _num(
    value: Any,
    default: Optional[float] = None,
) -> Optional[float]:
    try:
        number = float(value)

        if number != number:
            return default

        return number

    except (TypeError, ValueError):
        return default


def _text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return str(value).strip().upper()


def _first_number(
    *values: Any,
) -> Optional[float]:
    for value in values:
        number = _num(value)

        if number is not None:
            return number

    return None


def _dict(
    value: Any,
) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def _extract_row(
    stock: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    symbol = _text(
        stock.get("symbol")
    )

    if not symbol:
        return None

    edge = _dict(
        stock.get(
            "experimental_edge"
        )
    )

    relative_strength = _dict(
        edge.get(
            "relative_strength"
        )
    )

    if not relative_strength:
        relative_strength = _dict(
            stock.get(
                "relative_strength"
            )
        )

    velocity = _dict(
        edge.get(
            "opportunity_velocity"
        )
    )

    opportunity_score = _first_number(
        edge.get(
            "opportunity_score"
        ),
        stock.get(
            "opportunity_score"
        ),
    )

    if opportunity_score is None:
        return None

    change_1m = _first_number(
        edge.get(
            "change_1m_percent"
        ),
        stock.get(
            "change_1m_percent"
        ),
    )

    change_5m = _first_number(
        edge.get(
            "change_5m_percent"
        ),
        stock.get(
            "change_5m_percent"
        ),
    )

    rs_1m = _first_number(
        relative_strength.get(
            "rs_1m_pct"
        ),
        edge.get(
            "rs_1m_pct"
        ),
        stock.get(
            "rs_1m_pct"
        ),
    )

    rs_3m = _first_number(
        relative_strength.get(
            "rs_3m_pct"
        ),
        edge.get(
            "rs_3m_pct"
        ),
        stock.get(
            "rs_3m_pct"
        ),
    )

    rs_5m = _first_number(
        relative_strength.get(
            "rs_5m_pct"
        ),
        edge.get(
            "rs_5m_pct"
        ),
        stock.get(
            "rs_5m_pct"
        ),
    )

    rs_strength = _first_number(
        relative_strength.get(
            "strength"
        ),
        edge.get(
            "rs_strength"
        ),
    )

    rs_direction = _text(
        relative_strength.get(
            "direction"
        )
        or edge.get(
            "rs_direction"
        )
    )

    persistence = _text(
        relative_strength.get(
            "persistence"
        )
        or edge.get(
            "rs_persistence"
        )
    )

    rvol = _first_number(
        edge.get("rvol"),
        edge.get(
            "time_rvol"
        ),
        stock.get("rvol"),
        stock.get(
            "time_rvol"
        ),
    )

    opportunity_delta_1m = _first_number(
        velocity.get(
            "delta_1m"
        ),
        edge.get(
            "opportunity_delta_1m"
        ),
    )

    opportunity_delta_5m = _first_number(
        velocity.get(
            "delta_5m"
        ),
        edge.get(
            "opportunity_delta_5m"
        ),
    )

    return {
        "symbol":
            symbol,

        "ltp":
            _first_number(
                stock.get("ltp"),
                edge.get("ltp"),
            ),

        "volume":
            _first_number(
                stock.get("volume"),
                edge.get("volume"),
            ),

        "opportunity_score":
            opportunity_score,

        "opportunity_state":
            _text(
                edge.get(
                    "opportunity_state"
                )
                or stock.get(
                    "opportunity_state"
                )
            ),

        "change_1m_percent":
            change_1m,

        "change_5m_percent":
            change_5m,

        "rs_1m_pct":
            rs_1m,

        "rs_3m_pct":
            rs_3m,

        "rs_5m_pct":
            rs_5m,

        "rs_strength":
            rs_strength,

        "rs_direction":
            rs_direction,

        "rs_persistence":
            persistence,

        "rvol":
            rvol,

        "opportunity_delta_1m":
            opportunity_delta_1m,

        "opportunity_delta_5m":
            opportunity_delta_5m,
    }


def _bullish_analysis(
    row: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    opportunity = _num(
        row.get(
            "opportunity_score"
        ),
        0.0,
    ) or 0.0

    if opportunity < 40:
        return None

    change_1m = _num(
        row.get(
            "change_1m_percent"
        )
    )

    change_5m = _num(
        row.get(
            "change_5m_percent"
        )
    )

    rs_5m = _num(
        row.get(
            "rs_5m_pct"
        )
    )

    rs_direction = _text(
        row.get(
            "rs_direction"
        )
    )

    persistence = _text(
        row.get(
            "rs_persistence"
        )
    )

    rvol = _num(
        row.get("rvol")
    )

    # Core requirement:
    # stock itself is rising AND it is
    # outperforming NIFTY.
    price_core = (
        change_5m is not None
        and change_5m > 0
    )

    rs_core = (
        (
            rs_5m is not None
            and rs_5m > 0
        )
        or (
            "OUTPERFORM"
            in rs_direction
        )
    )

    if not (
        price_core
        and rs_core
    ):
        return None

    reasons: List[str] = []
    confirmations = 0

    if (
        change_1m is not None
        and change_1m > 0
    ):
        confirmations += 1
        reasons.append(
            "1m price rising"
        )

    if (
        change_5m is not None
        and change_5m > 0
    ):
        confirmations += 1
        reasons.append(
            "5m price rising"
        )

    if (
        rs_5m is not None
        and rs_5m > 0
    ):
        confirmations += 1
        reasons.append(
            "Positive 5m RS vs NIFTY"
        )

    if (
        "OUTPERFORM"
        in rs_direction
    ):
        confirmations += 1
        reasons.append(
            "Outperforming NIFTY"
        )

    if (
        "PERSISTENT"
        in persistence
        and "OUTPERFORM"
        in persistence
    ):
        confirmations += 1
        reasons.append(
            "Persistent outperformance"
        )

    if (
        rvol is not None
        and rvol >= 1.25
    ):
        confirmations += 1

        if rvol >= 2.0:
            reasons.append(
                "Strong RVOL participation"
            )
        else:
            reasons.append(
                "RVOL participation confirmed"
            )

    if confirmations >= 5:
        tier = "STRONG"
    elif confirmations >= 4:
        tier = "CONFIRMED"
    else:
        tier = "DEVELOPING"

    result = dict(row)

    result.update(
        {
            "leader_direction":
                "BULLISH",

            "confirmation_count":
                confirmations,

            "confirmation_total":
                6,

            "leader_tier":
                tier,

            "leader_reasons":
                reasons,
        }
    )

    return result


def _bearish_analysis(
    row: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    opportunity = _num(
        row.get(
            "opportunity_score"
        ),
        0.0,
    ) or 0.0

    if opportunity < 40:
        return None

    change_1m = _num(
        row.get(
            "change_1m_percent"
        )
    )

    change_5m = _num(
        row.get(
            "change_5m_percent"
        )
    )

    rs_5m = _num(
        row.get(
            "rs_5m_pct"
        )
    )

    rs_direction = _text(
        row.get(
            "rs_direction"
        )
    )

    persistence = _text(
        row.get(
            "rs_persistence"
        )
    )

    rvol = _num(
        row.get("rvol")
    )

    price_core = (
        change_5m is not None
        and change_5m < 0
    )

    rs_core = (
        (
            rs_5m is not None
            and rs_5m < 0
        )
        or (
            "UNDERPERFORM"
            in rs_direction
        )
    )

    if not (
        price_core
        and rs_core
    ):
        return None

    reasons: List[str] = []
    confirmations = 0

    if (
        change_1m is not None
        and change_1m < 0
    ):
        confirmations += 1
        reasons.append(
            "1m price falling"
        )

    if (
        change_5m is not None
        and change_5m < 0
    ):
        confirmations += 1
        reasons.append(
            "5m price falling"
        )

    if (
        rs_5m is not None
        and rs_5m < 0
    ):
        confirmations += 1
        reasons.append(
            "Negative 5m RS vs NIFTY"
        )

    if (
        "UNDERPERFORM"
        in rs_direction
    ):
        confirmations += 1
        reasons.append(
            "Underperforming NIFTY"
        )

    if (
        "PERSISTENT"
        in persistence
        and "UNDERPERFORM"
        in persistence
    ):
        confirmations += 1
        reasons.append(
            "Persistent underperformance"
        )

    if (
        rvol is not None
        and rvol >= 1.25
    ):
        confirmations += 1

        if rvol >= 2.0:
            reasons.append(
                "Strong RVOL participation"
            )
        else:
            reasons.append(
                "RVOL participation confirmed"
            )

    if confirmations >= 5:
        tier = "STRONG"
    elif confirmations >= 4:
        tier = "CONFIRMED"
    else:
        tier = "DEVELOPING"

    result = dict(row)

    result.update(
        {
            "leader_direction":
                "BEARISH",

            "confirmation_count":
                confirmations,

            "confirmation_total":
                6,

            "leader_tier":
                tier,

            "leader_reasons":
                reasons,
        }
    )

    return result


def _rank_key(
    row: Dict[str, Any],
) -> Tuple[
    float,
    float,
    float,
    float,
    float,
]:
    confirmations = _num(
        row.get(
            "confirmation_count"
        ),
        0.0,
    ) or 0.0

    opportunity_delta = _num(
        row.get(
            "opportunity_delta_1m"
        ),
        0.0,
    ) or 0.0

    opportunity = _num(
        row.get(
            "opportunity_score"
        ),
        0.0,
    ) or 0.0

    rs_5m = abs(
        _num(
            row.get(
                "rs_5m_pct"
            ),
            0.0,
        )
        or 0.0
    )

    rvol = _num(
        row.get("rvol"),
        0.0,
    ) or 0.0

    return (
        confirmations,
        opportunity_delta,
        opportunity,
        rs_5m,
        rvol,
    )


def attach_directional_leaders(
    *,
    snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    result = dict(
        snapshot
    )

    stocks = list(
        result.get(
            "results",
            [],
        )
        or []
    )

    bullish: List[
        Dict[str, Any]
    ] = []

    bearish: List[
        Dict[str, Any]
    ] = []

    for stock in stocks:
        if not isinstance(
            stock,
            dict,
        ):
            continue

        row = _extract_row(
            stock
        )

        if row is None:
            continue

        bullish_row = (
            _bullish_analysis(
                row
            )
        )

        if bullish_row:
            bullish.append(
                bullish_row
            )

        bearish_row = (
            _bearish_analysis(
                row
            )
        )

        if bearish_row:
            bearish.append(
                bearish_row
            )

    bullish.sort(
        key=_rank_key,
        reverse=True,
    )

    bearish.sort(
        key=_rank_key,
        reverse=True,
    )

    summary_raw = result.get(
        "experimental_edge_summary",
        {},
    )

    summary = (
        dict(summary_raw)
        if isinstance(
            summary_raw,
            dict,
        )
        else {}
    )

    summary[
        "bullish_leaders"
    ] = bullish[:20]

    summary[
        "bearish_leaders"
    ] = bearish[:20]

    summary[
        "bullish_leader_count"
    ] = len(
        bullish
    )

    summary[
        "bearish_leader_count"
    ] = len(
        bearish
    )

    summary[
        "directional_leader_timestamp"
    ] = datetime.now(
        timezone.utc
    ).isoformat()

    result[
        "experimental_edge_summary"
    ] = summary

    return result
