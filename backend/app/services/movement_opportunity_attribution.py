from __future__ import annotations

import csv

from collections import defaultdict
from pathlib import Path
from statistics import mean


PATH = Path(
    "logs/signal_validation_multi_day.csv"
)


def number(value):

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


def bucket(score):

    if score < 30:
        return "<30"

    if score < 40:
        return "30-40"

    if score < 50:
        return "40-50"

    if score < 60:
        return "50-60"

    if score < 70:
        return "60-70"

    return ">=70"


def metrics(rows):

    abs10 = [
        value
        for row in rows
        if (
            value := number(
                row.get(
                    "absolute_10m"
                )
            )
        )
        is not None
    ]

    excursions = [
        value
        for row in rows
        if (
            value := number(
                row.get(
                    "max_excursion_10m"
                )
            )
        )
        is not None
    ]

    directional = [
        value
        for row in rows
        if (
            value := number(
                row.get(
                    "return_10m"
                )
            )
        )
        is not None
    ]

    return {
        "count":
            len(rows),

        "avg_abs":
            mean(abs10)
            if abs10
            else 0.0,

        "move20":
            (
                sum(
                    value >= 0.20
                    for value
                    in abs10
                )
                / len(abs10)
                * 100
            )
            if abs10
            else 0.0,

        "move30":
            (
                sum(
                    value >= 0.30
                    for value
                    in abs10
                )
                / len(abs10)
                * 100
            )
            if abs10
            else 0.0,

        "excursion30":
            (
                sum(
                    value >= 0.30
                    for value
                    in excursions
                )
                / len(excursions)
                * 100
            )
            if excursions
            else 0.0,

        "avg_excursion":
            mean(excursions)
            if excursions
            else 0.0,

        "direction_win":
            (
                sum(
                    value > 0
                    for value
                    in directional
                )
                / len(directional)
                * 100
            )
            if directional
            else 0.0,
    }


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

    groups = defaultdict(
        list
    )

    for row in rows:

        score = number(
            row.get(
                "opportunity_score"
            )
        )

        if score is None:
            continue

        groups[
            bucket(score)
        ].append(
            row
        )

    order = [
        "<30",
        "30-40",
        "40-50",
        "50-60",
        "60-70",
        ">=70",
    ]

    print()
    print(
        "=" * 120
    )

    print(
        "MOVEMENT OPPORTUNITY VALIDATION"
    )

    print(
        "=" * 120
    )

    for key in order:

        rows = groups.get(
            key,
            [],
        )

        if len(rows) < 20:
            continue

        result = metrics(
            rows
        )

        print(
            f"{key:10}",
            f"N={result['count']:5}",
            f"ABS10={result['avg_abs']:.3f}%",
            f">=.20={result['move20']:5.1f}%",
            f">=.30={result['move30']:5.1f}%",
            f"MAX>=.30={result['excursion30']:5.1f}%",
            f"AVGMAX={result['avg_excursion']:.3f}%",
            f"DIRWIN={result['direction_win']:5.1f}%",
        )


if __name__ == "__main__":

    main()
