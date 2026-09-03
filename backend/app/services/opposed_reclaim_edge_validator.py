from __future__ import annotations

import csv
import random

from collections import defaultdict
from pathlib import Path
from statistics import mean, median


PATH = Path(
    "logs/signal_validation_multi_day.csv"
)


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
        and trigger
        != context
    )


def opportunity_bucket(row):

    score = num(
        row.get(
            "opportunity_score"
        )
    )

    if score is None:
        return "UNKNOWN"

    if score < 50:
        return "40-50"

    if score < 60:
        return "50-60"

    if score < 70:
        return "60-70"

    return ">=70"


def quality_bucket(row):

    value = num(
        row.get(
            "trigger_quality"
        )
    )

    if value is None:
        return "UNKNOWN"

    if value < 0.40:
        return "<0.40"

    if value < 0.55:
        return "0.40-0.55"

    if value < 0.70:
        return "0.55-0.70"

    return ">=0.70"


def time_bucket(row):

    value = str(
        row.get(
            "cutoff",
            "",
        )
    )

    if not value:
        return "UNKNOWN"

    try:

        hour, minute = map(
            int,
            value.split(":")
        )

    except ValueError:

        return "UNKNOWN"

    total = (
        hour * 60
        + minute
    )

    if total <= 630:
        return "OPEN"

    if total <= 810:
        return "MIDDAY"

    return "LATE"


def metrics(
    rows,
    *,
    cost=0.0,
):

    raw = [
        value
        for row in rows
        if (
            value := num(
                row.get(
                    "return_10m"
                )
            )
        )
        is not None
    ]

    adjusted = [
        value - cost
        for value in raw
    ]

    if not adjusted:

        return {
            "n": 0,
            "win": 0.0,
            "avg": 0.0,
            "median": 0.0,
            "continuation": 0.0,
        }

    return {
        "n":
            len(adjusted),

        "win":
            (
                sum(
                    value > 0
                    for value
                    in adjusted
                )
                / len(adjusted)
                * 100
            ),

        "avg":
            mean(
                adjusted
            ),

        "median":
            median(
                adjusted
            ),

        "continuation":
            (
                sum(
                    value >= 0.20
                    for value
                    in adjusted
                )
                / len(adjusted)
                * 100
            ),
    }


def print_group(
    title,
    rows,
    function,
    minimum=5,
):

    groups = defaultdict(
        list
    )

    for row in rows:

        groups[
            function(row)
        ].append(
            row
        )

    print()
    print(
        "=" * 120
    )

    print(title)

    print(
        "=" * 120
    )

    for key, group in sorted(
        groups.items()
    ):

        if len(group) < minimum:
            continue

        result = metrics(
            group
        )

        print(
            f"{str(key):28}",
            f"N={result['n']:3}",
            f"W10={result['win']:5.1f}%",
            f"A10={result['avg']:+7.3f}%",
            f"MED={result['median']:+7.3f}%",
            f">=.20={result['continuation']:5.1f}%",
        )


def cluster_bootstrap(
    rows,
    *,
    iterations=10000,
):

    by_day = defaultdict(
        list
    )

    for row in rows:

        value = num(
            row.get(
                "return_10m"
            )
        )

        if value is None:
            continue

        by_day[
            row.get(
                "validation_session",
                "UNKNOWN",
            )
        ].append(
            value
        )

    days = list(
        by_day.keys()
    )

    if not days:
        return (
            0.0,
            0.0,
        )

    random.seed(
        42
    )

    samples = []

    for _ in range(
        iterations
    ):

        sampled_returns = []

        for _ in range(
            len(days)
        ):

            day = random.choice(
                days
            )

            sampled_returns.extend(
                by_day[
                    day
                ]
            )

        samples.append(
            mean(
                sampled_returns
            )
        )

    samples.sort()

    lower_index = int(
        len(samples)
        * 0.025
    )

    upper_index = int(
        len(samples)
        * 0.975
    )

    return (
        samples[
            lower_index
        ],
        samples[
            min(
                upper_index,
                len(samples) - 1,
            )
        ],
    )


def main():

    if not PATH.exists():

        raise RuntimeError(
            f"Missing: {PATH}"
        )

    with PATH.open() as handle:

        rows = list(
            csv.DictReader(
                handle
            )
        )

    opposed = [
        row
        for row in rows
        if is_opposed(
            row
        )
    ]

    print()
    print(
        "=" * 120
    )

    print(
        "OPPOSED RECLAIM EDGE VALIDATION"
    )

    print(
        "=" * 120
    )

    base = metrics(
        opposed
    )

    print(
        "Signals:",
        base["n"],
    )

    print(
        "10m win:",
        f'{base["win"]:.1f}%',
    )

    print(
        "Avg 10m:",
        f'{base["avg"]:+.3f}%',
    )

    print(
        "Median:",
        f'{base["median"]:+.3f}%',
    )

    print(
        ">= +0.20%:",
        f'{base["continuation"]:.1f}%',
    )

    # ====================================
    # DAY-CLUSTERED BOOTSTRAP
    # ====================================

    lower, upper = (
        cluster_bootstrap(
            opposed
        )
    )

    print()
    print(
        "Day-cluster bootstrap"
    )

    print(
        "Mean return 95% interval:",
        f"{lower:+.3f}%",
        "to",
        f"{upper:+.3f}%",
    )

    # ====================================
    # COST STRESS
    # Total round-trip friction.
    # ====================================

    print()
    print(
        "=" * 120
    )

    print(
        "TRANSACTION / SLIPPAGE STRESS"
    )

    print(
        "=" * 120
    )

    for cost in [
        0.00,
        0.02,
        0.04,
        0.06,
        0.08,
        0.10,
        0.12,
    ]:

        result = metrics(
            opposed,
            cost=cost,
        )

        print(
            f"COST={cost:4.2f}%",
            f"W10={result['win']:5.1f}%",
            f"NET={result['avg']:+7.3f}%",
            f"MED={result['median']:+7.3f}%",
        )

    # ====================================
    # ROBUSTNESS BREAKDOWNS
    # ====================================

    print_group(
        "DAY",
        opposed,
        lambda row:
            row.get(
                "validation_session",
                "UNKNOWN",
            ),
    )

    print_group(
        "RECLAIM DIRECTION",
        opposed,
        lambda row:
            row.get(
                "trigger_direction",
                "UNKNOWN",
            ),
    )

    print_group(
        "OPPORTUNITY",
        opposed,
        opportunity_bucket,
    )

    print_group(
        "TRIGGER QUALITY",
        opposed,
        quality_bucket,
    )

    print_group(
        "COMPRESSION",
        opposed,
        lambda row:
            row.get(
                "compression_state",
                "NONE",
            ),
    )

    print_group(
        "TIME OF DAY",
        opposed,
        time_bucket,
    )


if __name__ == "__main__":

    main()
