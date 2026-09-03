from __future__ import annotations

from bisect import bisect_right
from datetime import datetime

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from ..models import CandleHistory
from .candle_history import (
    load_candles,
)
from .time_normalized_rvol import (
    analyze_time_normalized_rvol,
)

from .market_data_quality import (
    IST,
    filter_nse_session,
    latest_valid_session,
)


def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        if value is None:
            return default

        return float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return default


def _resample_1m_to_5m(
    candles: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    if not candles:
        return []

    buckets: dict[
        int,
        list[
            dict[str, Any]
        ],
    ] = {}

    for candle in candles:
        try:
            timestamp = int(
                float(
                    candle.get(
                        "time"
                    )
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        bucket = (
            timestamp
            - timestamp % 300
        )

        buckets.setdefault(
            bucket,
            [],
        ).append(
            candle
        )

    output = []

    for bucket in sorted(
        buckets
    ):
        rows = sorted(
            buckets[
                bucket
            ],
            key=lambda item: int(
                float(
                    item.get(
                        "time",
                        0,
                    )
                )
            ),
        )

        if not rows:
            continue

        output.append(
            {
                "time": bucket,

                "open": _safe_float(
                    rows[0].get(
                        "open"
                    )
                ),

                "high": max(
                    _safe_float(
                        row.get(
                            "high"
                        )
                    )
                    for row in rows
                ),

                "low": min(
                    _safe_float(
                        row.get(
                            "low"
                        )
                    )
                    for row in rows
                ),

                "close": _safe_float(
                    rows[-1].get(
                        "close"
                    )
                ),

                "volume": sum(
                    _safe_float(
                        row.get(
                            "volume"
                        )
                    )
                    for row in rows
                ),
            }
        )

    return output


class ReplayCandleEngine:

    def __init__(
        self,
        data: dict[
            str,
            dict[
                str,
                list[
                    dict[str, Any]
                ],
            ],
        ],
        rvol_map: dict[
            str,
            dict[str, Any],
        ] | None = None,
    ) -> None:

        self._data = data

        self._rvol_map = (
            rvol_map
            or {}
        )


    def time_normalized_rvol(
        self,
        symbol: str,
    ) -> dict[str, Any]:

        normalized = (
            str(symbol)
            .strip()
            .upper()
        )

        return dict(
            self._rvol_map.get(
                normalized,
                {
                    "available": False,
                    "rvol": 0.0,
                    "classification":
                        "INSUFFICIENT_HISTORY",
                    "samples": 0,
                },
            )
        )



    def candles(
        self,
        symbol: str,
        interval: str,
        limit: int | None = None,
    ) -> list[
        dict[str, Any]
    ]:

        normalized = (
            str(
                symbol
            )
            .strip()
            .upper()
        )

        rows = list(
            self._data
            .get(
                normalized,
                {},
            )
            .get(
                interval,
                [],
            )
        )

        if limit is not None:
            rows = rows[
                -limit:
            ]

        return rows


async def stored_1m_symbols(
    session: AsyncSession,
    *,
    limit: int = 500,
) -> list[str]:

    statement = (
        select(
            CandleHistory.symbol
        )
        .where(
            CandleHistory.interval
            == "1m"
        )
        .distinct()
        .limit(
            max(
                int(limit),
                1,
            )
        )
    )

    result = await session.execute(
        statement
    )

    return [
        str(
            symbol
        ).strip().upper()
        for symbol
        in result.scalars()
        if symbol
    ]


async def build_replay_inputs(
    session: AsyncSession,
    *,
    symbols: list[str] | None = None,
    symbol_limit: int = 500,
    candle_limit: int = 500,
    benchmark_symbol: str = "NIFTY 50",
) -> tuple[
    list[dict[str, Any]],
    ReplayCandleEngine,
]:

    benchmark_symbol = (
        benchmark_symbol
        .strip()
        .upper()
    )

    # -------------------------------------------------
    # LOAD BENCHMARK
    # -------------------------------------------------

    benchmark_raw = await load_candles(
        session,
        symbol=benchmark_symbol,
        interval="1m",
        limit=max(
            candle_limit,
            3000,
        ),
    )

    replay_session = (
        latest_valid_session(
            benchmark_raw
        )
    )

    if replay_session is None:
        print(
            "[REPLAY] No valid NIFTY session"
        )

        return (
            [],
            ReplayCandleEngine({}),
        )

    benchmark_session = (
        filter_nse_session(
            benchmark_raw,
            session_date=replay_session,
        )
    )

    if len(
        benchmark_session
    ) < 6:
        print(
            "[REPLAY] Insufficient "
            "NIFTY candles"
        )

        return (
            [],
            ReplayCandleEngine({}),
        )

    # -------------------------------------------------
    # LOAD SAME-SESSION STOCK DATA
    # -------------------------------------------------

    if symbols is None:
        symbols = await stored_1m_symbols(
            session,
            limit=symbol_limit,
        )

    candidate_data: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    candidate_history: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for symbol in symbols:

        normalized = (
            str(symbol)
            .strip()
            .upper()
        )

        if (
            not normalized
            or normalized
            == benchmark_symbol
        ):
            continue

        raw = await load_candles(
            session,
            symbol=normalized,
            interval="1m",
            limit=max(
                candle_limit,
                3000,
            ),
        )

        candles = filter_nse_session(
            raw,
            session_date=replay_session,
        )

        if len(candles) < 6:
            continue

        candidate_data[
            normalized
        ] = candles

        candidate_history[
            normalized
        ] = raw

    if not candidate_data:
        print(
            "[REPLAY] No stocks for session",
            replay_session,
        )

        return (
            [],
            ReplayCandleEngine({}),
        )

    # -------------------------------------------------
    # COMMON REPLAY CUTOFF
    #
    # Warmup requests occur at different times.
    #
    # Find the LATEST NIFTY minute for which at
    # least 50% of available stocks have a candle
    # no more than 3 minutes old.
    #
    # This produces one cross-sectional snapshot
    # without using future candles.
    # -------------------------------------------------

    max_lag_seconds = (
        3 * 60
    )

    benchmark_times = [
        int(
            float(
                candle["time"]
            )
        )
        for candle in benchmark_session
    ]

    candidate_times = {
        symbol: [
            int(
                float(
                    candle["time"]
                )
            )
            for candle in candles
        ]
        for (
            symbol,
            candles,
        )
        in candidate_data.items()
    }

    candidate_count = len(
        candidate_data
    )

    minimum_coverage = min(
        candidate_count,
        max(
            5,
            int(
                candidate_count
                * 0.50
            ),
        ),
    )

    replay_time = None
    replay_coverage = 0

    for target_time in reversed(
        benchmark_times
    ):

        coverage = 0

        for times in (
            candidate_times.values()
        ):

            index = (
                bisect_right(
                    times,
                    target_time,
                )
                - 1
            )

            if index < 0:
                continue

            lag = (
                target_time
                - times[index]
            )

            if (
                0
                <= lag
                <= max_lag_seconds
            ):
                coverage += 1

        if (
            coverage
            >= minimum_coverage
        ):
            replay_time = (
                target_time
            )

            replay_coverage = (
                coverage
            )

            break

    if replay_time is None:
        print(
            "[REPLAY] Could not find "
            "common market cutoff"
        )

        return (
            [],
            ReplayCandleEngine({}),
        )

    # -------------------------------------------------
    # CRITICAL:
    # Remove every candle AFTER replay_time.
    #
    # This prevents future-data leakage.
    # -------------------------------------------------

    benchmark_candles = [
        candle
        for candle in benchmark_session
        if int(
            float(
                candle["time"]
            )
        )
        <= replay_time
    ]

    data: dict[
        str,
        dict[
            str,
            list[dict[str, Any]],
        ],
    ] = {
        benchmark_symbol: {
            "1m":
                benchmark_candles,

            "5m":
                _resample_1m_to_5m(
                    benchmark_candles
                ),
        }
    }

    ticks: list[
        dict[str, Any]
    ] = []

    stale_symbol_count = 0

    rvol_map: dict[
        str,
        dict[str, Any],
    ] = {}

    for (
        symbol,
        original_candles,
    ) in candidate_data.items():

        candles = [
            candle
            for candle
            in original_candles
            if int(
                float(
                    candle["time"]
                )
            )
            <= replay_time
        ]

        if len(candles) < 6:
            continue

        stock_latest_time = int(
            float(
                candles[-1][
                    "time"
                ]
            )
        )

        lag_seconds = (
            replay_time
            - stock_latest_time
        )

        if (
            lag_seconds < 0
            or lag_seconds
            > max_lag_seconds
        ):
            stale_symbol_count += 1
            continue

        five_minute = (
            _resample_1m_to_5m(
                candles
            )
        )

        data[
            symbol
        ] = {
            "1m": candles,
            "5m": five_minute,
        }

        latest = (
            candles[-1]
        )

        rvol_map[
            symbol
        ] = (
            analyze_time_normalized_rvol(
                candles=(
                    candidate_history[
                        symbol
                    ]
                ),
                target_timestamp=(
                    stock_latest_time
                ),
            )
        )

        ticks.append(
            {
                "symbol":
                    symbol,

                "ltp":
                    _safe_float(
                        latest.get(
                            "close"
                        )
                    ),

                "volume":
                    _safe_float(
                        latest.get(
                            "volume"
                        )
                    ),

                "exchange_timestamp":
                    latest.get(
                        "time"
                    ),

                "source":
                    "REPLAY",
            }
        )

    cutoff_display = (
        datetime.fromtimestamp(
            replay_time,
            tz=IST,
        )
        .strftime(
            "%Y-%m-%d %H:%M"
        )
    )

    print(
        "[REPLAY]",
        "session:",
        replay_session,
        "cutoff:",
        cutoff_display,
        "coverage:",
        (
            f"{replay_coverage}/"
            f"{candidate_count}"
        ),
        "stocks:",
        len(ticks),
        "stale skipped:",
        stale_symbol_count,
    )

    return (
        ticks,
        ReplayCandleEngine(
            data,
            rvol_map=rvol_map,
        ),
    )
