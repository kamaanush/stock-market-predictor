from datetime import datetime, timezone
from typing import Any, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import CandleHistory


def _to_datetime(
    value: Union[
        int,
        float,
        str,
        datetime,
    ],
) -> datetime:

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(
                tzinfo=timezone.utc
            )

        return value

    if isinstance(value, str):
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed

    timestamp = float(value)

    if timestamp > 10_000_000_000:
        timestamp /= 1000

    return datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    )


def candle_to_dict(
    candle: CandleHistory,
) -> dict[str, float]:

    return {
        "time": int(
            candle.timestamp.timestamp()
        ),
        "open": float(
            candle.open
        ),
        "high": float(
            candle.high
        ),
        "low": float(
            candle.low
        ),
        "close": float(
            candle.close
        ),
        "volume": float(
            candle.volume
            or 0.0
        ),
    }


async def load_candles(
    session: AsyncSession,
    *,
    symbol: str,
    interval: str,
    limit: Optional[int] = None
) -> list[
    dict[str, float]
]:

    statement = (
        select(
            CandleHistory
        )
        .where(
            CandleHistory.symbol
            == symbol.upper(),
            CandleHistory.interval
            == interval,
        )
        .order_by(
            CandleHistory.timestamp.asc()
        )
    )

    result = await session.execute(
        statement
    )

    rows = list(
        result.scalars()
    )

    if limit is not None:
        rows = rows[
            -limit:
        ]

    return [
        candle_to_dict(
            row
        )
        for row in rows
    ]


async def save_candles(
    session: AsyncSession,
    *,
    symbol: str,
    interval: str,
    candles: list[
        dict[str, Any]
    ],
) -> int:

    if not candles:
        return 0

    normalized_symbol = (
        symbol
        .strip()
        .upper()
    )

    saved = 0

    for source in candles:

        timestamp = _to_datetime(
            source["time"]
        )

        statement = (
            select(
                CandleHistory
            )
            .where(
                CandleHistory.symbol
                == normalized_symbol,
                CandleHistory.interval
                == interval,
                CandleHistory.timestamp
                == timestamp,
            )
        )

        result = await session.execute(
            statement
        )

        existing = (
            result.scalar_one_or_none()
        )

        if existing is None:

            session.add(
                CandleHistory(
                    symbol=
                        normalized_symbol,

                    interval=
                        interval,

                    timestamp=
                        timestamp,

                    open=float(
                        source["open"]
                    ),

                    high=float(
                        source["high"]
                    ),

                    low=float(
                        source["low"]
                    ),

                    close=float(
                        source["close"]
                    ),

                    volume=float(
                        source.get(
                            "volume",
                            0.0,
                        )
                        or 0.0
                    ),
                )
            )

            saved += 1

        else:

            existing.open = float(
                source["open"]
            )

            existing.high = float(
                source["high"]
            )

            existing.low = float(
                source["low"]
            )

            existing.close = float(
                source["close"]
            )

            existing.volume = float(
                source.get(
                    "volume",
                    0.0,
                )
                or 0.0
            )

    await session.commit()

    return saved


async def latest_candle_time(
    session: AsyncSession,
    *,
    symbol: str,
    interval: str,
) -> Optional[datetime]:

    statement = (
        select(
            CandleHistory.timestamp
        )
        .where(
            CandleHistory.symbol
            == symbol.strip().upper(),
            CandleHistory.interval
            == interval,
        )
        .order_by(
            CandleHistory.timestamp.desc()
        )
        .limit(1)
    )

    result = await session.execute(
        statement
    )

    latest = (
        result.scalar_one_or_none()
    )

    if latest is None:
        return None

    if latest.tzinfo is None:
        latest = latest.replace(
            tzinfo=timezone.utc
        )

    return latest