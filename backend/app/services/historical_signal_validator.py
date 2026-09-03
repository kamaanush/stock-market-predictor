from __future__ import annotations

import asyncio
import csv

from datetime import datetime, timedelta

from bisect import bisect_right
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

from sqlalchemy import select

from app.database import SessionLocal
from app.models import CandleHistory

from .candle_history import (
    candle_to_dict,
)

from .fast_scanner import (
    build_fast_scan_snapshot,
)

from .market_data_quality import (
    IST,
    candle_timestamp,
    nse_session_date,
)

from .compression_expansion import (
    analyze_compression_expansion,
)

from .liquidity_sweep import (
    analyze_liquidity_sweep,
)

from .movement_opportunity import (
    analyze_movement_opportunity,
)

from .reclaim_reversal_trigger import (
    analyze_reclaim_reversal_trigger,
)

from .setup_confluence import (
    analyze_setup_confluence,
)

from .time_normalized_rvol import (
    analyze_time_normalized_rvol,
)


class ValidationCandleEngine:

    def __init__(
        self,
        data: Dict[
            str,
            Dict[
                str,
                List[Dict[str, Any]],
            ],
        ],
        rvol_map: Dict[
            str,
            Dict[str, Any],
        ],
    ) -> None:

        self._data = data
        self._rvol_map = rvol_map

    def candles(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:

        rows = (
            self._data
            .get(
                symbol.upper(),
                {},
            )
            .get(
                interval,
                [],
            )
        )

        return rows[
            -limit:
        ]

    def time_normalized_rvol(
        self,
        symbol: str,
    ) -> Dict[str, Any]:

        return dict(
            self._rvol_map.get(
                symbol.upper(),
                {
                    "available": False,
                    "rvol": 0.0,
                    "classification":
                        "INSUFFICIENT_HISTORY",
                    "samples": 0,
                },
            )
        )


def _row_to_candle(
    row: CandleHistory,
) -> Dict[str, Any]:
    """
    Use the canonical CandleHistory
    conversion.

    SQLite strips timezone information.
    candle_to_dict() correctly restores
    UTC before converting to epoch time.

    Keeping replay and validation on the
    same conversion path prevents session
    timestamp drift.
    """

    return candle_to_dict(
        row
    )


def _resample_5m(
    candles: List[
        Dict[str, Any]
    ],
) -> List[Dict[str, Any]]:

    buckets: Dict[
        int,
        Dict[str, Any],
    ] = {}

    for candle in candles:

        timestamp = int(
            candle["time"]
        )

        bucket = (
            timestamp
            - timestamp % 300
        )

        existing = (
            buckets.get(
                bucket
            )
        )

        if existing is None:

            buckets[bucket] = {
                "time": bucket,

                "open":
                    candle["open"],

                "high":
                    candle["high"],

                "low":
                    candle["low"],

                "close":
                    candle["close"],

                "volume":
                    candle.get(
                        "volume",
                        0.0,
                    ),
            }

        else:

            existing["high"] = max(
                existing["high"],
                candle["high"],
            )

            existing["low"] = min(
                existing["low"],
                candle["low"],
            )

            existing["close"] = (
                candle["close"]
            )

            existing["volume"] += (
                candle.get(
                    "volume",
                    0.0,
                )
            )

    return [
        buckets[key]
        for key in sorted(
            buckets
        )
    ]


def _percent_change(
    future: float,
    entry: float,
) -> float:

    if entry <= 0:
        return 0.0

    return (
        (
            future
            - entry
        )
        / entry
        * 100.0
    )


def _directional_return(
    future: float,
    entry: float,
    direction: str,
) -> float:

    raw = _percent_change(
        future,
        entry,
    )

    if direction == "BEARISH":
        return -raw

    return raw


def _forward_metrics(
    candles: List[
        Dict[str, Any]
    ],
    *,
    entry_time: int,
    entry_price: float,
    direction: str,
) -> Dict[str, Any]:
    """
    Forward outcome measurement.

    Uses the first available candle
    at or shortly after the requested
    5m / 10m horizon.

    Maximum tolerance = 2 minutes.
    """

    times = [
        int(
            candle["time"]
        )
        for candle
        in candles
    ]

    def future_candle(
        seconds_forward: int,
    ):

        target = (
            entry_time
            + seconds_forward
        )

        index = bisect_right(
            times,
            target - 1,
        )

        if index >= len(candles):
            return None

        candle = candles[
            index
        ]

        candle_time = int(
            candle["time"]
        )

        if (
            candle_time
            - target
            > 120
        ):
            return None

        return candle


    candle_5 = future_candle(
        300
    )

    candle_10 = future_candle(
        600
    )

    return_5 = None
    return_10 = None

    if candle_5 is not None:

        return_5 = (
            _directional_return(
                float(
                    candle_5[
                        "close"
                    ]
                ),
                entry_price,
                direction,
            )
        )

    if candle_10 is not None:

        return_10 = (
            _directional_return(
                float(
                    candle_10[
                        "close"
                    ]
                ),
                entry_price,
                direction,
            )
        )

    future_window = [
        candle
        for candle
        in candles
        if (
            int(
                candle["time"]
            )
            > entry_time
            and int(
                candle["time"]
            )
            <= entry_time + 720
        )
    ]

    mfe_10 = None
    mae_10 = None

    if future_window:

        highest = max(
            float(
                candle["high"]
            )
            for candle
            in future_window
        )

        lowest = min(
            float(
                candle["low"]
            )
            for candle
            in future_window
        )

        if direction == "BULLISH":

            mfe_10 = (
                _percent_change(
                    highest,
                    entry_price,
                )
            )

            mae_10 = (
                _percent_change(
                    lowest,
                    entry_price,
                )
            )

        else:

            mfe_10 = (
                _percent_change(
                    entry_price,
                    lowest,
                )
            )

            mae_10 = -(
                _percent_change(
                    highest,
                    entry_price,
                )
            )

    absolute_5m = (
        abs(return_5)
        if return_5
        is not None
        else None
    )

    absolute_10m = (
        abs(return_10)
        if return_10
        is not None
        else None
    )

    max_excursion_10m = None

    if future_window:

        highest = max(
            float(
                candle["high"]
            )
            for candle
            in future_window
        )

        lowest = min(
            float(
                candle["low"]
            )
            for candle
            in future_window
        )

        upward_move = abs(
            _percent_change(
                highest,
                entry_price,
            )
        )

        downward_move = abs(
            _percent_change(
                lowest,
                entry_price,
            )
        )

        max_excursion_10m = max(
            upward_move,
            downward_move,
        )

    return {
        "return_5m":
            return_5,

        "return_10m":
            return_10,

        "absolute_5m":
            absolute_5m,

        "absolute_10m":
            absolute_10m,

        "max_excursion_10m":
            max_excursion_10m,

        "mfe_10m":
            mfe_10,

        "mae_10m":
            mae_10,
    }


async def load_history():

    async with SessionLocal() as session:

        result = await session.execute(
            select(
                CandleHistory
            )
            .where(
                CandleHistory.interval
                == "1m"
            )
            .order_by(
                CandleHistory.timestamp
            )
        )

        rows = list(
            result.scalars()
        )

    grouped = defaultdict(
        list
    )

    for row in rows:

        candle = (
            _row_to_candle(
                row
            )
        )

        grouped[
            row.symbol
            .strip()
            .upper()
        ].append(
            candle
        )

    return grouped


def _latest_session(
    grouped,
):

    nifty = grouped.get(
        "NIFTY 50",
        [],
    )

    if not nifty:
        raise RuntimeError(
            "NIFTY 50 history missing"
        )

    session = None

    for candle in reversed(
        nifty
    ):

        session = (
            nse_session_date(
                candle["time"]
            )
        )

        if session is not None:
            break

    if session is None:
        raise RuntimeError(
            "Could not determine "
            "latest NSE session"
        )

    return session


async def run_validation():

    grouped = await load_history()

    history_times = {
        symbol: [
            int(
                candle["time"]
            )
            for candle
            in candles
        ]
        for symbol, candles
        in grouped.items()
    }

    target_session = (
        _latest_session(
            grouped
        )
    )

    session_data = {}

    session_times = {}

    for symbol, candles in (
        grouped.items()
    ):

        rows = [
            candle
            for candle in candles
            if (
                nse_session_date(
                    candle["time"]
                )
                == target_session
            )
        ]

        if rows:

            session_data[
                symbol
            ] = rows

            session_times[
                symbol
            ] = [
                int(
                    candle["time"]
                )
                for candle
                in rows
            ]

    nifty = session_data.get(
        "NIFTY 50",
        [],
    )

    if not nifty:
        raise RuntimeError(
            "No NIFTY candles "
            "for target session"
        )

    # -----------------------------------
    # BUILD AN EXPLICIT NSE REPLAY CLOCK
    #
    # Do NOT depend on NIFTY having a
    # candle exactly at every 5-minute
    # timestamp.
    #
    # Replay:
    #     09:45
    #     09:50
    #     ...
    #     15:15
    # -----------------------------------

    latest_nifty_time = max(
        int(
            candle["time"]
        )
        for candle in nifty
    )

    replay_start = datetime(
        target_session.year,
        target_session.month,
        target_session.day,
        9,
        45,
        tzinfo=IST,
    )

    replay_end = datetime(
        target_session.year,
        target_session.month,
        target_session.day,
        15,
        15,
        tzinfo=IST,
    )

    latest_nifty_dt = (
        datetime.fromtimestamp(
            latest_nifty_time,
            tz=IST,
        )
    )

    if latest_nifty_dt < replay_end:
        replay_end = latest_nifty_dt

    cutoffs = []

    cursor = replay_start

    while cursor <= replay_end:

        cutoffs.append(
            int(
                cursor.timestamp()
            )
        )

        cursor += timedelta(
            minutes=5
        )

    print()
    print(
        "Validation session:",
        target_session,
    )

    print(
        "NIFTY stored range:",
        datetime.fromtimestamp(
            int(
                nifty[0]["time"]
            ),
            tz=IST,
        ).strftime(
            "%H:%M"
        ),
        "->",
        latest_nifty_dt.strftime(
            "%H:%M"
        ),
    )

    print(
        "Replay checkpoints:",
        len(cutoffs),
    )

    if cutoffs:

        print(
            "Replay range:",
            datetime.fromtimestamp(
                cutoffs[0],
                tz=IST,
            ).strftime(
                "%H:%M"
            ),
            "->",
            datetime.fromtimestamp(
                cutoffs[-1],
                tz=IST,
            ).strftime(
                "%H:%M"
            ),
        )

    print()

    observations = []

    # A scanner condition persisting for
    # several consecutive 5-minute scans
    # is ONE trading event, not several
    # independent signals.
    #
    # Same symbol + same direction can only
    # create a new validation event after
    # 20 minutes.
    last_signal_time = {}

    signal_cooldown_seconds = (
        20 * 60
    )

    # Reset rotation state because
    # historical validation starts
    # a fresh replay sequence.
    if hasattr(
        build_fast_scan_snapshot,
        "_rotation_tracker",
    ):
        delattr(
            build_fast_scan_snapshot,
            "_rotation_tracker",
        )

    for cutoff in cutoffs:

        cutoff_dt = (
            __import__(
                "datetime"
            )
            .datetime
            .fromtimestamp(
                cutoff,
                tz=IST,
            )
        )

        print(
            "Testing:",
            cutoff_dt.strftime(
                "%H:%M"
            ),
        )

        data = {}

        ticks = []

        rvol_map = {}

        # -------------------------------
        # NIFTY benchmark
        # -------------------------------

        nifty_times = (
            session_times[
                "NIFTY 50"
            ]
        )

        nifty_index = (
            bisect_right(
                nifty_times,
                cutoff,
            )
        )

        nifty_upto = (
            session_data[
                "NIFTY 50"
            ][
                :nifty_index
            ]
        )

        if len(
            nifty_upto
        ) < 20:
            continue

        nifty_latest_time = int(
            nifty_upto[-1][
                "time"
            ]
        )

        nifty_lag = (
            cutoff
            - nifty_latest_time
        )

        if (
            nifty_lag < 0
            or nifty_lag > 120
        ):
            continue

        data[
            "NIFTY 50"
        ] = {
            "1m":
                nifty_upto[-500:],

            "5m":
                _resample_5m(
                    nifty_upto[-500:]
                ),
        }

        # -------------------------------
        # STOCKS
        # -------------------------------

        for (
            symbol,
            candles,
        ) in session_data.items():

            if symbol == "NIFTY 50":
                continue

            times = (
                session_times[
                    symbol
                ]
            )

            index = (
                bisect_right(
                    times,
                    cutoff,
                )
            )

            upto = candles[
                :index
            ]

            if len(upto) < 20:
                continue

            latest = (
                upto[-1]
            )

            latest_time = int(
                latest["time"]
            )

            lag = (
                cutoff
                - latest_time
            )

            if (
                lag < 0
                or lag > 120
            ):
                continue

            data[
                symbol
            ] = {
                "1m":
                    upto[-500:],

                "5m":
                    _resample_5m(
                        upto[-500:]
                    ),
            }

            # --------------------------------
            # Time-normalized RVOL
            # only uses history available
            # up to this cutoff.
            # --------------------------------

            all_history = grouped[
                symbol
            ]

            history_index = (
                bisect_right(
                    history_times[
                        symbol
                    ],
                    cutoff,
                )
            )

            rvol_map[
                symbol
            ] = (
                analyze_time_normalized_rvol(
                    candles=all_history[
                        :history_index
                    ],
                    target_timestamp=(
                        latest_time
                    ),
                )
            )

            ticks.append(
                {
                    "symbol":
                        symbol,

                    "ltp":
                        float(
                            latest[
                                "close"
                            ]
                        ),
                }
            )

        engine = (
            ValidationCandleEngine(
                data,
                rvol_map,
            )
        )

        snapshot = (
            build_fast_scan_snapshot(
                ticks=ticks,
                candle_engine=engine,
            )
        )

        breadth = snapshot.get(
            "market_breadth",
            {},
        )

        directional_setups = 0

        for stock in snapshot.get(
            "results",
            [],
        ):

            if (
                stock.get(
                    "status"
                )
                != "READY"
            ):
                continue

            confluence = (
                analyze_setup_confluence(
                    stock=stock,
                    market_breadth=(
                        breadth
                    ),
                )
            )


            validation_candles = (
                engine.candles(
                    str(
                        stock[
                            "symbol"
                        ]
                    ),
                    "1m",
                    limit=20,
                )
            )

            validation_compression = (
                analyze_compression_expansion(
                    validation_candles
                )
            )

            validation_sweep = (
                analyze_liquidity_sweep(
                    validation_candles
                )
            )

            stock_for_opportunity = dict(
                stock
            )

            stock_for_opportunity[
                "compression_expansion"
            ] = validation_compression

            stock_for_opportunity[
                "liquidity_sweep"
            ] = validation_sweep

            movement_opportunity = (
                analyze_movement_opportunity(
                    stock=(
                        stock_for_opportunity
                    ),
                    market_breadth=(
                        breadth
                    ),
                )
            )


            directional_trigger = (
                analyze_reclaim_reversal_trigger(
                    candles=(
                        validation_candles
                    ),
                    opportunity=(
                        movement_opportunity
                    ),
                )
            )

            setup = confluence[
                "setup"
            ]

            # --------------------------------
            # For the first real validation,
            # focus only on STRONG setups.
            # --------------------------------

            if (
                movement_opportunity.get(
                    "score",
                    0.0,
                )
                < 40.0
            ):
                continue

            if (
                directional_trigger.get(
                    "direction"
                )
                not in {
                    "BULLISH",
                    "BEARISH",
                }
            ):
                continue

            directional_setups += 1

            direction = (
                directional_trigger[
                    "direction"
                ]
            )

            symbol = str(
                stock[
                    "symbol"
                ]
            )

            event_key = (
                symbol,
                direction,
            )

            previous_signal_time = (
                last_signal_time.get(
                    event_key
                )
            )

            if (
                previous_signal_time
                is not None
                and cutoff
                - previous_signal_time
                < signal_cooldown_seconds
            ):
                continue

            symbol_times = (
                session_times[
                    symbol
                ]
            )

            index = bisect_right(
                symbol_times,
                cutoff,
            )

            if index <= 0:
                continue

            entry_candle = (
                session_data[
                    symbol
                ][
                    index - 1
                ]
            )

            entry_time = int(
                entry_candle[
                    "time"
                ]
            )

            entry_price = float(
                entry_candle[
                    "close"
                ]
            )

            metrics = (
                _forward_metrics(
                    session_data[
                        symbol
                    ],
                    entry_time=(
                        entry_time
                    ),
                    entry_price=(
                        entry_price
                    ),
                    direction=(
                        direction
                    ),
                )
            )

            if (
                metrics[
                    "return_10m"
                ]
                is None
            ):
                continue

            last_signal_time[
                event_key
            ] = cutoff

            observations.append(
                {
                    "session":
                        str(
                            target_session
                        ),

                    "cutoff":
                        cutoff_dt.strftime(
                            "%H:%M"
                        ),

                    "symbol":
                        symbol,

                    "setup":
                        setup,

                    "direction":
                        direction,

                    "quality":
                        confluence[
                            "quality"
                        ],

                    "entry_price":
                        entry_price,

                    "return_5m":
                        metrics[
                            "return_5m"
                        ],

                    "return_10m":
                        metrics[
                            "return_10m"
                        ],

                    "absolute_5m":
                        metrics[
                            "absolute_5m"
                        ],

                    "absolute_10m":
                        metrics[
                            "absolute_10m"
                        ],

                    "max_excursion_10m":
                        metrics[
                            "max_excursion_10m"
                        ],

                    "mfe_10m":
                        metrics[
                            "mfe_10m"
                        ],

                    "mae_10m":
                        metrics[
                            "mae_10m"
                        ],

                    "rvol":
                        confluence[
                            "rvol"
                        ],

                    "breadth_regime":
                        breadth.get(
                            "regime",
                            "UNKNOWN",
                        ),

                    "fast_score":
                        stock.get(
                            "fast_score",
                            0.0,
                        ),

                    "rs_strength":
                        stock.get(
                            "relative_strength",
                            {},
                        ).get(
                            "strength",
                            0.0,
                        ),

                    "rs_direction":
                        stock.get(
                            "relative_strength",
                            {},
                        ).get(
                            "direction",
                            "NEUTRAL",
                        ),

                    "rs_acceleration":
                        stock.get(
                            "rs_acceleration",
                            {},
                        ).get(
                            "acceleration",
                            0.0,
                        ),

                    "rs_acceleration_quality":
                        stock.get(
                            "rs_acceleration",
                            {},
                        ).get(
                            "quality",
                            0.0,
                        ),

                    "compression_state":
                        validation_compression.get(
                            "state",
                            "NONE",
                        ),

                    "liquidity_sweep":
                        validation_sweep.get(
                            "state",
                            "NONE",
                        ),

                    "strong_sweep":
                        validation_sweep.get(
                            "strong",
                            False,
                        ),

                    "opportunity_score":
                        movement_opportunity.get(
                            "score",
                            0.0,
                        ),

                    "opportunity_state":
                        movement_opportunity.get(
                            "state",
                            "NORMAL",
                        ),

                    "direction_hint":
                        movement_opportunity.get(
                            "direction_hint",
                            "UNCERTAIN",
                        ),

                    "direction_agreement":
                        movement_opportunity.get(
                            "direction_agreement",
                            0.0,
                        ),


                    "trigger_state":
                        directional_trigger.get(
                            "state",
                            "NO_TRIGGER",
                        ),

                    "trigger_direction":
                        directional_trigger.get(
                            "direction",
                            "NONE",
                        ),

                    "trigger_quality":
                        directional_trigger.get(
                            "quality",
                            0.0,
                        ),

                    "trigger_breakout_percent":
                        directional_trigger.get(
                            "breakout_percent",
                            0.0,
                        ),

                    "trigger_body_ratio":
                        directional_trigger.get(
                            "body_ratio",
                            0.0,
                        ),

                    "trigger_expansion_ratio":
                        directional_trigger.get(
                            "expansion_ratio",
                            0.0,
                        ),

                    "trigger_volume_ratio":
                        directional_trigger.get(
                            "local_volume_ratio",
                            0.0,
                        ),

                    "volume_source":
                        stock.get(
                            "volume_context",
                            {},
                        ).get(
                            "source",
                            "UNKNOWN",
                        ),
                }
            )

    return (
        target_session,
        observations,
    )


def print_summary(
    observations,
):

    print()
    print(
        "=" * 100
    )

    print(
        "HISTORICAL SIGNAL VALIDATION"
    )

    print(
        "=" * 100
    )

    print(
        "Signals:",
        len(observations),
    )

    print()

    by_setup = defaultdict(
        list
    )

    for row in observations:

        by_setup[
            row["setup"]
        ].append(
            row
        )

    for (
        setup,
        rows,
    ) in sorted(
        by_setup.items()
    ):

        returns_5 = [
            row["return_5m"]
            for row in rows
            if (
                row[
                    "return_5m"
                ]
                is not None
            )
        ]

        returns_10 = [
            row["return_10m"]
            for row in rows
            if (
                row[
                    "return_10m"
                ]
                is not None
            )
        ]

        mfe = [
            row["mfe_10m"]
            for row in rows
            if (
                row[
                    "mfe_10m"
                ]
                is not None
            )
        ]

        mae = [
            row["mae_10m"]
            for row in rows
            if (
                row[
                    "mae_10m"
                ]
                is not None
            )
        ]

        wins_5 = sum(
            value > 0
            for value
            in returns_5
        )

        wins_10 = sum(
            value > 0
            for value
            in returns_10
        )

        continuation_10 = sum(
            value >= 0.20
            for value
            in returns_10
        )

        print(
            setup
        )

        print(
            "  signals:",
            len(rows),
        )

        if returns_5:

            print(
                "  5m win rate:",
                f"{wins_5 / len(returns_5) * 100:.1f}%",
            )

            print(
                "  avg 5m return:",
                f"{mean(returns_5):+.3f}%",
            )

        if returns_10:

            print(
                "  10m win rate:",
                f"{wins_10 / len(returns_10) * 100:.1f}%",
            )

            print(
                "  avg 10m return:",
                f"{mean(returns_10):+.3f}%",
            )

            print(
                "  >= +0.20% continuation:",
                f"{continuation_10 / len(returns_10) * 100:.1f}%",
            )

        if mfe:

            print(
                "  avg MFE 10m:",
                f"{mean(mfe):+.3f}%",
            )

        if mae:

            print(
                "  avg MAE 10m:",
                f"{mean(mae):+.3f}%",
            )

        print()


def save_csv(
    session,
    observations,
):

    output_dir = Path(
        "logs"
    )

    output_dir.mkdir(
        exist_ok=True
    )

    path = (
        output_dir
        / (
            "signal_validation_"
            + str(session)
            + ".csv"
        )
    )

    if not observations:
        return path

    with path.open(
        "w",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=list(
                observations[
                    0
                ].keys()
            ),
        )

        writer.writeheader()

        writer.writerows(
            observations
        )

    return path


async def main():

    session, observations = (
        await run_validation()
    )

    print_summary(
        observations
    )

    path = save_csv(
        session,
        observations,
    )

    print(
        "CSV:",
        path,
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )
