from __future__ import annotations

from datetime import datetime
from statistics import median
from typing import Any

from .market_data_quality import (
    IST,
    candle_timestamp,
    nse_session_date,
)


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


def analyze_time_normalized_rvol(
    *,
    candles: list[
        dict[str, Any]
    ],
    target_timestamp: int | None = None,
    max_sessions: int = 5,
    minute_tolerance: int = 1,
    minimum_samples: int = 2,
) -> dict[str, Any]:
    """
    Compare current 1-minute volume with
    the same clock-minute volume from
    previous NSE trading sessions.

    Example:

        Today 15:22 volume = 120,000

        Prior 15:22:
            42,000
            45,000
            38,000
            50,000

        baseline ~43,500
        RVOL     ~2.76x
    """

    if not candles:
        return {
            "available": False,
            "rvol": 0.0,
            "classification":
                "INSUFFICIENT_HISTORY",
            "samples": 0,
        }

    valid = []

    for candle in candles:

        timestamp = (
            candle_timestamp(
                candle
            )
        )

        if timestamp is None:
            continue

        session = (
            nse_session_date(
                timestamp
            )
        )

        if session is None:
            continue

        valid.append(
            (
                timestamp,
                candle,
                session,
            )
        )

    if not valid:
        return {
            "available": False,
            "rvol": 0.0,
            "classification":
                "INSUFFICIENT_HISTORY",
            "samples": 0,
        }

    valid.sort(
        key=lambda item:
            item[0]
    )

    if target_timestamp is None:
        target_timestamp = (
            valid[-1][0]
        )

    target_dt = (
        datetime.fromtimestamp(
            target_timestamp,
            tz=IST,
        )
    )

    target_session = (
        target_dt.date()
    )

    target_minute = (
        target_dt.hour * 60
        + target_dt.minute
    )

    # -------------------------------------------------
    # CURRENT BAR
    # -------------------------------------------------

    current_candidate = None

    for (
        timestamp,
        candle,
        session,
    ) in reversed(
        valid
    ):

        if session != target_session:
            continue

        candle_dt = (
            datetime.fromtimestamp(
                timestamp,
                tz=IST,
            )
        )

        minute = (
            candle_dt.hour * 60
            + candle_dt.minute
        )

        if (
            abs(
                minute
                - target_minute
            )
            <= minute_tolerance
        ):

            current_candidate = (
                timestamp,
                candle,
            )

            break

    if current_candidate is None:
        return {
            "available": False,
            "rvol": 0.0,
            "classification":
                "NO_CURRENT_VOLUME",
            "samples": 0,
        }

    current_volume = (
        _safe_float(
            current_candidate[
                1
            ].get(
                "volume"
            )
        )
    )

    # -------------------------------------------------
    # PRIOR SESSION BASELINES
    # -------------------------------------------------

    per_session: dict[
        Any,
        tuple[
            int,
            float,
        ],
    ] = {}

    for (
        timestamp,
        candle,
        session,
    ) in valid:

        if (
            session
            >= target_session
        ):
            continue

        candle_dt = (
            datetime.fromtimestamp(
                timestamp,
                tz=IST,
            )
        )

        minute = (
            candle_dt.hour * 60
            + candle_dt.minute
        )

        distance = abs(
            minute
            - target_minute
        )

        if (
            distance
            > minute_tolerance
        ):
            continue

        volume = _safe_float(
            candle.get(
                "volume"
            )
        )

        if volume <= 0:
            continue

        existing = (
            per_session.get(
                session
            )
        )

        # Prefer the exact clock minute.
        if (
            existing is None
            or distance
            < existing[0]
        ):
            per_session[
                session
            ] = (
                distance,
                volume,
            )

    sessions = sorted(
        per_session,
        reverse=True,
    )[
        :max_sessions
    ]

    historical_volumes = [
        per_session[
            session
        ][1]
        for session
        in sessions
    ]

    if (
        len(
            historical_volumes
        )
        < minimum_samples
    ):
        return {
            "available": False,

            "rvol": 0.0,

            "classification":
                "INSUFFICIENT_HISTORY",

            "samples":
                len(
                    historical_volumes
                ),

            "current_volume":
                current_volume,

            "target_minute":
                target_dt.strftime(
                    "%H:%M"
                ),
        }

    baseline = float(
        median(
            historical_volumes
        )
    )

    if baseline <= 0:
        return {
            "available": False,
            "rvol": 0.0,
            "classification":
                "INVALID_BASELINE",
            "samples":
                len(
                    historical_volumes
                ),
        }

    rvol = (
        current_volume
        / baseline
    )

    if rvol >= 3.0:
        classification = (
            "EXTREME"
        )

    elif rvol >= 2.0:
        classification = (
            "HIGH"
        )

    elif rvol >= 1.30:
        classification = (
            "ABOVE_NORMAL"
        )

    elif rvol <= 0.50:
        classification = (
            "LOW"
        )

    else:
        classification = (
            "NORMAL"
        )

    return {
        "available": True,

        "rvol": round(
            rvol,
            3,
        ),

        "classification":
            classification,

        "current_volume":
            round(
                current_volume,
            ),

        "baseline_volume":
            round(
                baseline,
            ),

        "samples":
            len(
                historical_volumes
            ),

        "target_minute":
            target_dt.strftime(
                "%H:%M"
            ),

        "historical_volumes": [
            round(
                value
            )
            for value
            in historical_volumes
        ],
    }
