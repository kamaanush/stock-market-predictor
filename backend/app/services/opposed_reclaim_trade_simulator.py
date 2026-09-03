from __future__ import annotations

import csv
import math

from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median


PATH = Path(
    "logs/signal_validation_multi_day.csv"
)


STOP_SIZES = [
    0.15,
    0.20,
    0.25,
    0.30,
    0.35,
]


TARGET_R_VALUES = [
    1.0,
    1.25,
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


def is_opposed_reclaim(row):

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


def simulate_trade(
    row,
    *,
    stop_percent,
    target_r,
    cost,
):

    mfe = num(
        row.get(
            "mfe_10m"
        )
    )

    mae = num(
        row.get(
            "mae_10m"
        )
    )

    time_return = num(
        row.get(
            "return_10m"
        )
    )

    if (
        mfe is None
        or mae is None
        or time_return is None
    ):

        return None

    target_percent = (
        stop_percent
        * target_r
    )

    target_hit = (
        mfe
        >= target_percent
    )

    stop_hit = (
        mae
        <= -stop_percent
    )

    # -----------------------------------
    # CONSERVATIVE AMBIGUITY RULE
    #
    # With only aggregate MFE/MAE we
    # cannot know which occurred first.
    #
    # If both were touched, assume STOP.
    # -----------------------------------

    if (
        target_hit
        and stop_hit
    ):

        gross = (
            -stop_percent
        )

        exit_type = (
            "AMBIGUOUS_STOP_FIRST"
        )

    elif stop_hit:

        gross = (
            -stop_percent
        )

        exit_type = (
            "STOP"
        )

    elif target_hit:

        gross = (
            target_percent
        )

        exit_type = (
            "TARGET"
        )

    else:

        gross = (
            time_return
        )

        exit_type = (
            "TIME_EXIT"
        )

    net = (
        gross
        - cost
    )

    return {
        "gross":
            gross,

        "net":
            net,

        "exit":
            exit_type,

        "stop":
            stop_percent,

        "target":
            target_percent,

        "target_r":
            target_r,
    }


def calculate(
    rows,
    *,
    stop,
    target_r,
    cost,
):

    trades = []

    exits = Counter()

    by_day = defaultdict(
        list
    )

    for row in rows:

        result = (
            simulate_trade(
                row,
                stop_percent=stop,
                target_r=target_r,
                cost=cost,
            )
        )

        if result is None:
            continue

        trades.append(
            result
        )

        exits[
            result[
                "exit"
            ]
        ] += 1

        by_day[
            row.get(
                "validation_session",
                "UNKNOWN",
            )
        ].append(
            result[
                "net"
            ]
        )

    values = [
        trade[
            "net"
        ]
        for trade in trades
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

    profit_factor = (
        gross_profit
        / gross_loss
        if gross_loss > 0
        else math.inf
    )

    positive_days = sum(
        mean(
            day_values
        ) > 0
        for day_values
        in by_day.values()
        if day_values
    )

    worst_day = min(
        (
            mean(values)
            for values
            in by_day.values()
            if values
        ),
        default=0.0,
    )

    return {
        "n":
            len(values),

        "win":
            (
                len(winners)
                / len(values)
                * 100
            ),

        "avg":
            mean(values),

        "median":
            median(values),

        "pf":
            profit_factor,

        "positive_days":
            positive_days,

        "days":
            len(by_day),

        "worst_day":
            worst_day,

        "target_rate":
            (
                exits["TARGET"]
                / len(values)
                * 100
            ),

        "stop_rate":
            (
                exits["STOP"]
                / len(values)
                * 100
            ),

        "ambiguous_rate":
            (
                exits[
                    "AMBIGUOUS_STOP_FIRST"
                ]
                / len(values)
                * 100
            ),

        "time_rate":
            (
                exits["TIME_EXIT"]
                / len(values)
                * 100
            ),
    }


def leave_one_day_out(
    rows,
    *,
    stop,
    target_r,
    cost,
):

    days = sorted(
        {
            row.get(
                "validation_session",
                "UNKNOWN",
            )
            for row in rows
        }
    )

    results = []

    for omitted in days:

        subset = [
            row
            for row in rows
            if row.get(
                "validation_session"
            )
            != omitted
        ]

        result = calculate(
            subset,
            stop=stop,
            target_r=target_r,
            cost=cost,
        )

        if result:

            results.append(
                (
                    omitted,
                    result[
                        "avg"
                    ],
                )
            )

    return results


def symbol_concentration(
    rows,
):

    counts = Counter(
        row.get(
            "symbol",
            "UNKNOWN",
        )
        for row in rows
    )

    total = sum(
        counts.values()
    )

    print()
    print(
        "=" * 120
    )

    print(
        "SIGNAL CONCENTRATION"
    )

    print(
        "=" * 120
    )

    print(
        "Unique symbols:",
        len(counts),
    )

    print()
    print(
        "Most frequent symbols:"
    )

    for (
        symbol,
        count,
    ) in counts.most_common(
        10
    ):

        share = (
            count
            / total
            * 100
        )

        print(
            f"{symbol:15}",
            f"N={count:3}",
            f"{share:5.1f}%",
        )


def main():

    if not PATH.exists():

        raise RuntimeError(
            f"Missing {PATH}"
        )

    with PATH.open() as handle:

        rows = list(
            csv.DictReader(
                handle
            )
        )

    rows = [
        row
        for row in rows
        if is_opposed_reclaim(
            row
        )
    ]

    print()
    print(
        "=" * 140
    )

    print(
        "OPPOSED RECLAIM TRADE SIMULATION"
    )

    print(
        "=" * 140
    )

    print(
        "Signals:",
        len(rows),
    )

    symbol_concentration(
        rows
    )

    for cost in COSTS:

        print()
        print(
            "=" * 140
        )

        print(
            f"ROUND-TRIP COST = {cost:.2f}%"
        )

        print(
            "=" * 140
        )

        output = []

        for stop in STOP_SIZES:

            for target_r in (
                TARGET_R_VALUES
            ):

                result = calculate(
                    rows,
                    stop=stop,
                    target_r=target_r,
                    cost=cost,
                )

                if not result:
                    continue

                output.append(
                    (
                        result[
                            "avg"
                        ],
                        stop,
                        target_r,
                        result,
                    )
                )

        output.sort(
            reverse=True,
            key=lambda item:
                item[0],
        )

        for (
            _,
            stop,
            target_r,
            data,
        ) in output:

            print(
                f"STOP={stop:.2f}%",
                f"TARGET={target_r:.2f}R",
                f"N={data['n']:3}",
                f"W={data['win']:5.1f}%",
                f"AVG={data['avg']:+7.3f}%",
                f"MED={data['median']:+7.3f}%",
                f"PF={data['pf']:4.2f}",
                f"DAYS={data['positive_days']}/{data['days']}",
                f"WORST={data['worst_day']:+7.3f}%",
                f"TGT={data['target_rate']:5.1f}%",
                f"STOP={data['stop_rate']:5.1f}%",
                f"AMB={data['ambiguous_rate']:5.1f}%",
                f"TIME={data['time_rate']:5.1f}%",
            )

        # --------------------------------
        # Robustness test for best result
        # --------------------------------

        if output:

            (
                _,
                best_stop,
                best_r,
                best,
            ) = output[0]

            print()
            print(
                "BEST CONFIGURATION"
            )

            print(
                f"Stop: {best_stop:.2f}%"
            )

            print(
                f"Target: {best_r:.2f}R"
            )

            print(
                f"Net expectancy: "
                f"{best['avg']:+.3f}%"
            )

            print(
                f"Profit factor: "
                f"{best['pf']:.2f}"
            )

            print()
            print(
                "LEAVE-ONE-DAY-OUT"
            )

            lodo = leave_one_day_out(
                rows,
                stop=best_stop,
                target_r=best_r,
                cost=cost,
            )

            for (
                omitted,
                avg_return,
            ) in lodo:

                print(
                    f"without {omitted}:",
                    f"{avg_return:+.3f}%",
                )


if __name__ == "__main__":

    main()
