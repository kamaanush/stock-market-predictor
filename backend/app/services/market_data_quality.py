from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo


IST = ZoneInfo(
    "Asia/Kolkata"
)


def candle_timestamp(
    candle: dict[str, Any],
) -> int | None:
    raw = candle.get(
        "time"
    )

    if raw is None:
        return None

    try:
        if isinstance(
            raw,
            datetime,
        ):
            timestamp = (
                raw.timestamp()
            )

        elif isinstance(
            raw,
            str,
        ):
            timestamp = (
                datetime.fromisoformat(
                    raw.replace(
                        "Z",
                        "+00:00",
                    )
                ).timestamp()
            )

        else:
            timestamp = float(
                raw
            )

            if (
                timestamp
                > 10_000_000_000
            ):
                timestamp /= 1000.0

    except (
        TypeError,
        ValueError,
    ):
        return None

    return int(
        timestamp
    )


def nse_session_date(
    timestamp: int,
) -> date | None:
    dt = datetime.fromtimestamp(
        timestamp,
        tz=IST,
    )

    # Monday-Friday only.
    if dt.weekday() >= 5:
        return None

    minute_of_day = (
        dt.hour * 60
        + dt.minute
    )

    market_open = (
        9 * 60
        + 15
    )

    market_close = (
        15 * 60
        + 30
    )

    if not (
        market_open
        <= minute_of_day
        <= market_close
    ):
        return None

    return dt.date()


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


def valid_ohlc(
    candle: dict[str, Any],
) -> bool:
    open_price = _safe_float(
        candle.get(
            "open"
        )
    )

    high = _safe_float(
        candle.get(
            "high"
        )
    )

    low = _safe_float(
        candle.get(
            "low"
        )
    )

    close = _safe_float(
        candle.get(
            "close"
        )
    )

    if min(
        open_price,
        high,
        low,
        close,
    ) <= 0:
        return False

    if high < max(
        open_price,
        close,
        low,
    ):
        return False

    if low > min(
        open_price,
        close,
        high,
    ):
        return False

    return True


def latest_valid_session(
    candles: list[
        dict[str, Any]
    ],
) -> date | None:
    sessions = []

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

        if session is not None:
            sessions.append(
                session
            )

    if not sessions:
        return None

    return max(
        sessions
    )


def filter_nse_session(
    candles: list[
        dict[str, Any]
    ],
    *,
    session_date: date | None = None,
) -> list[
    dict[str, Any]
]:
    """
    Keep only sane NSE cash-market candles
    belonging to one trading session.
    """

    if not candles:
        return []

    target_session = (
        session_date
        or latest_valid_session(
            candles
        )
    )

    if target_session is None:
        return []

    output = []

    for candle in candles:
        timestamp = (
            candle_timestamp(
                candle
            )
        )

        if timestamp is None:
            continue

        candle_session = (
            nse_session_date(
                timestamp
            )
        )

        if (
            candle_session
            != target_session
        ):
            continue

        if not valid_ohlc(
            candle
        ):
            continue

        normalized = dict(
            candle
        )

        normalized[
            "time"
        ] = timestamp

        output.append(
            normalized
        )

    output.sort(
        key=lambda item: int(
            item["time"]
        )
    )

    return output
