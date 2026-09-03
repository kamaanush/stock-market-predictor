from __future__ import annotations

import asyncio
import csv

from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, median

from sqlalchemy import select

from app.database import SessionLocal
from app.models import CandleHistory

from .candle_history import candle_to_dict
from .market_data_quality import IST


PATH = Path(
    "logs/signal_validation_multi_day.csv"
)

STOP_BUFFER_PERCENT = 0.02

HORIZONS = [
    5,
    10,
    15,
]

TARGET_R_VALUES = [
    None,   # structure stop + time exit
    1.0,
    1.5,
    2.0,
]

COSTS = [
    0.04,
    0.06,
]


def num(value):

    try:
        if value in (
            None,
            "",
            "None",
        ):
            return None

        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None


def context_direction(row):

    setup = str(
        row.get(
            "setup",
            "",
        )
    ).upper()

    if "BULLISH" in setup:
        return "BULLISH"

    if "BEARISH" in setup:
        return "BEARISH"

    return "NONE"


def is_opposed(row):

    trigger = str(
        row.get(
            "trigger_direction",
            "NONE",
        )
    ).upper()

    context = (
        context_direction(
            row
        )
    )

    return (
        trigger
        in {
            "BULLISH",
            "BEARISH",
        }
        and context
        in {
            "BULLISH",
            "BEARISH",
        }
        and trigger != context
    )


def directional_return(
    *,
    entry,
    exit_price,
    direction,
):

    if entry <= 0:
        return 0.0

    if direction == "BULLISH":

        return (
            (
                exit_price
                - entry
            )
            / entry
            * 100
        )

    return (
        (
            entry
            - exit_price
        )
        / entry
        * 100
    )


def percentile(
    values,
    p,
):

    if not values:
        return 0.0

    ordered = sorted(values)

    index = int(
        round(
            (
                len(ordered) - 1
            )
            * p
        )
    )

    return ordered[
        index
    ]


async def load_history(
    symbols,
):

    grouped = defaultdict(
        list
    )

    async with SessionLocal() as session:

        statement = (
            select(
                CandleHistory
            )
            .where(
                CandleHistory.interval
                == "1m",

                CandleHistory.symbol.in_(
                    symbols
                ),
            )
            .order_by(
                CandleHistory.symbol,
                CandleHistory.timestamp,
            )
        )

        result = await session.execute(
            statement
        )

        rows = list(
            result.scalars()
        )

    for row in rows:

        grouped[
            row.symbol.upper()
        ].append(
            candle_to_dict(
                row
            )
        )

    return grouped


def signal_timestamp(
    row,
):

    session = str(
        row.get(
            "validation_session",
            ""
        )
    )

    cutoff = str(
        row.get(
            "cutoff",
            ""
        )
    )

    dt = datetime.strptime(
        f"{session} {cutoff}",
        "%Y-%m-%d %H:%M",
    )

    dt = dt.replace(
        tzinfo=IST
    )

    return int(
        dt.timestamp()
    )


def same_session(
    timestamp,
    expected_date,
):

    return (
        datetime.fromtimestamp(
            timestamp,
            tz=IST,
        ).date().isoformat()
        == expected_date
    )


def prepare_trade(
    *,
    row,
    candles,
):

    if not candles:
        return None, "NO_HISTORY"

    cutoff = signal_timestamp(
        row
    )

    times = [
        int(
            candle["time"]
        )
        for candle
        in candles
    ]

    trigger_index = (
        bisect_right(
            times,
            cutoff,
        )
        - 1
    )

    if trigger_index < 0:

        return None, "NO_TRIGGER_CANDLE"

    trigger = candles[
        trigger_index
    ]

    trigger_lag = (
        cutoff
        - int(
            trigger["time"]
        )
    )

    if (
        trigger_lag < 0
        or trigger_lag > 120
    ):

        return None, "STALE_TRIGGER"

    entry_index = (
        trigger_index + 1
    )

    if entry_index >= len(candles):

        return None, "NO_ENTRY_CANDLE"

    entry_candle = candles[
        entry_index
    ]

    expected_session = str(
        row[
            "validation_session"
        ]
    )

    if not same_session(
        int(
            entry_candle["time"]
        ),
        expected_session,
    ):

        return None, "NEXT_SESSION_ENTRY"

    if (
        int(
            entry_candle["time"]
        )
        - int(
            trigger["time"]
        )
        > 120
    ):

        return None, "ENTRY_GAP"

    direction = str(
        row[
            "trigger_direction"
        ]
    ).upper()

    entry = float(
        entry_candle["open"]
    )

    trigger_high = float(
        trigger["high"]
    )

    trigger_low = float(
        trigger["low"]
    )

    # ==================================
    # NATURAL RECLAIM INVALIDATION
    #
    # Bullish reclaim:
    #     below sweep low
    #
    # Bearish reclaim:
    #     above sweep high
    # ==================================

    if direction == "BULLISH":

        stop = (
            trigger_low
            * (
                1
                - STOP_BUFFER_PERCENT
                / 100
            )
        )

        # Setup already invalidated before
        # we can realistically enter.
        if entry <= stop:

            return (
                None,
                "INVALID_BEFORE_ENTRY",
            )

    else:

        stop = (
            trigger_high
            * (
                1
                + STOP_BUFFER_PERCENT
                / 100
            )
        )

        if entry >= stop:

            return (
                None,
                "INVALID_BEFORE_ENTRY",
            )

    stop_distance = (
        abs(
            entry - stop
        )
        / entry
        * 100
    )

    if stop_distance <= 0:

        return None, "INVALID_STOP"

    return {
        "row":
            row,

        "candles":
            candles,

        "entry_index":
            entry_index,

        "entry_time":
            int(
                entry_candle[
                    "time"
                ]
            ),

        "entry":
            entry,

        "stop":
            stop,

        "stop_distance":
            stop_distance,

        "direction":
            direction,
    }, "READY"


def simulate(
    trade,
    *,
    horizon_minutes,
    target_r,
    cost,
):

    entry = trade[
        "entry"
    ]

    stop = trade[
        "stop"
    ]

    direction = trade[
        "direction"
    ]

    stop_distance = trade[
        "stop_distance"
    ]

    candles = trade[
        "candles"
    ]

    entry_index = trade[
        "entry_index"
    ]

    entry_time = trade[
        "entry_time"
    ]

    target = None

    if target_r is not None:

        target_distance = (
            stop_distance
            * target_r
        )

        if direction == "BULLISH":

            target = (
                entry
                * (
                    1
                    + target_distance
                    / 100
                )
            )

        else:

            target = (
                entry
                * (
                    1
                    - target_distance
                    / 100
                )
            )

    horizon_end = (
        entry_time
        + horizon_minutes * 60
    )

    last_candle = None

    exit_price = None
    exit_type = None

    for candle in candles[
        entry_index:
    ]:

        timestamp = int(
            candle["time"]
        )

        if timestamp > horizon_end:
            break

        if not same_session(
            timestamp,
            trade[
                "row"
            ][
                "validation_session"
            ],
        ):
            break

        last_candle = candle

        o = float(
            candle["open"]
        )

        h = float(
            candle["high"]
        )

        l = float(
            candle["low"]
        )

        if direction == "BULLISH":

            # Gap through structural stop.
            if o <= stop:

                exit_price = o
                exit_type = "GAP_STOP"
                break

            stop_hit = (
                l <= stop
            )

            target_hit = (
                target is not None
                and h >= target
            )

        else:

            if o >= stop:

                exit_price = o
                exit_type = "GAP_STOP"
                break

            stop_hit = (
                h >= stop
            )

            target_hit = (
                target is not None
                and l <= target
            )

        # We still do not know tick ordering
        # inside one 1-minute candle.
        #
        # Use conservative stop-first.
        if (
            stop_hit
            and target_hit
        ):

            exit_price = stop
            exit_type = (
                "AMBIGUOUS_STOP_FIRST"
            )

            break

        if stop_hit:

            exit_price = stop
            exit_type = "STRUCTURE_STOP"
            break

        if target_hit:

            exit_price = target
            exit_type = "TARGET"
            break

    if exit_price is None:

        if last_candle is None:
            return None

        exit_price = float(
            last_candle[
                "close"
            ]
        )

        exit_type = "TIME_EXIT"

    gross = directional_return(
        entry=entry,
        exit_price=exit_price,
        direction=direction,
    )

    net = (
        gross
        - cost
    )

    return {
        "net":
            net,

        "gross":
            gross,

        "exit_type":
            exit_type,

        "stop_distance":
            stop_distance,

        "day":
            trade[
                "row"
            ][
                "validation_session"
            ],

        "symbol":
            trade[
                "row"
            ][
                "symbol"
            ],
    }


def summarize(
    results,
):

    values = [
        item["net"]
        for item in results
    ]

    if not values:
        return None

    winners = [
        value
        for value in values
        if value > 0
    ]

    losers = [
        value
        for value in values
        if value < 0
    ]

    gross_profit = sum(
        winners
    )

    gross_loss = abs(
        sum(
            losers
        )
    )

    pf = (
        gross_profit
        / gross_loss
        if gross_loss > 0
        else float("inf")
    )

    by_day = defaultdict(
        list
    )

    exits = Counter()

    stops = []

    for item in results:

        by_day[
            item["day"]
        ].append(
            item["net"]
        )

        exits[
            item[
                "exit_type"
            ]
        ] += 1

        stops.append(
            item[
                "stop_distance"
            ]
        )

    positive_days = sum(
        mean(values) > 0
        for values
        in by_day.values()
    )

    return {
        "n":
            len(values),

        "win":
            len(winners)
            / len(values)
            * 100,

        "avg":
            mean(values),

        "median":
            median(values),

        "pf":
            pf,

        "positive_days":
            positive_days,

        "days":
            len(by_day),

        "stop_avg":
            mean(stops),

        "stop_med":
            median(stops),

        "stop_p90":
            percentile(
                stops,
                0.90,
            ),

        "stops":
            exits[
                "STRUCTURE_STOP"
            ],

        "gap_stops":
            exits[
                "GAP_STOP"
            ],

        "ambiguous":
            exits[
                "AMBIGUOUS_STOP_FIRST"
            ],

        "targets":
            exits[
                "TARGET"
            ],

        "time_exits":
            exits[
                "TIME_EXIT"
            ],
    }


async def main():

    with PATH.open() as handle:

        rows = list(
            csv.DictReader(
                handle
            )
        )

    rows = [
        row
        for row in rows
        if is_opposed(
            row
        )
    ]

    symbols = sorted(
        {
            str(
                row["symbol"]
            ).upper()
            for row in rows
        }
    )

    print()
    print(
        "Loading history for",
        len(symbols),
        "symbols..."
    )

    history = await load_history(
        symbols
    )

    trades = []

    rejected = Counter()

    for row in rows:

        symbol = str(
            row["symbol"]
        ).upper()

        trade, reason = (
            prepare_trade(
                row=row,
                candles=history.get(
                    symbol,
                    [],
                ),
            )
        )

        if trade is None:

            rejected[
                reason
            ] += 1

            continue

        trades.append(
            trade
        )

    print()
    print(
        "=" * 145
    )

    print(
        "PATH-AWARE OPPOSED RECLAIM"
    )

    print(
        "=" * 145
    )

    print(
        "Raw signals:",
        len(rows),
    )

    print(
        "Executable signals:",
        len(trades),
    )

    print(
        "Rejected:",
        dict(
            rejected
        ),
    )

    stop_distances = [
        trade[
            "stop_distance"
        ]
        for trade in trades
    ]

    if stop_distances:

        print()
        print(
            "STRUCTURAL STOP DISTANCE"
        )

        print(
            "Average:",
            f"{mean(stop_distances):.3f}%"
        )

        print(
            "Median:",
            f"{median(stop_distances):.3f}%"
        )

        print(
            "P90:",
            f"{percentile(stop_distances, 0.90):.3f}%"
        )

    for cost in COSTS:

        print()
        print(
            "=" * 145
        )

        print(
            f"COST = {cost:.2f}%"
        )

        print(
            "=" * 145
        )

        output = []

        for horizon in HORIZONS:

            for target_r in (
                TARGET_R_VALUES
            ):

                results = []

                for trade in trades:

                    result = simulate(
                        trade,
                        horizon_minutes=(
                            horizon
                        ),
                        target_r=target_r,
                        cost=cost,
                    )

                    if result is not None:
                        results.append(
                            result
                        )

                summary = summarize(
                    results
                )

                if not summary:
                    continue

                output.append(
                    (
                        summary["avg"],
                        horizon,
                        target_r,
                        summary,
                    )
                )

        output.sort(
            reverse=True,
            key=lambda item:
                item[0],
        )

        for (
            _,
            horizon,
            target_r,
            data,
        ) in output:

            target_label = (
                "TIME"
                if target_r is None
                else f"{target_r:.2f}R"
            )

            print(
                f"H={horizon:2}m",
                f"TARGET={target_label:6}",
                f"N={data['n']:3}",
                f"W={data['win']:5.1f}%",
                f"AVG={data['avg']:+7.3f}%",
                f"MED={data['median']:+7.3f}%",
                f"PF={data['pf']:4.2f}",
                f"DAYS={data['positive_days']}/{data['days']}",
                f"STOP={data['stops']:3}",
                f"GAP={data['gap_stops']:2}",
                f"AMB={data['ambiguous']:2}",
                f"TGT={data['targets']:3}",
                f"TIME={data['time_exits']:3}",
            )


if __name__ == "__main__":

    asyncio.run(
        main()
    )
