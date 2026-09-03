from __future__ import annotations

import csv

from collections import defaultdict
from pathlib import Path
from statistics import mean


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


def metrics(rows):

    returns = [
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

    mfe = [
        value
        for row in rows
        if (
            value := num(
                row.get(
                    "mfe_10m"
                )
            )
        )
        is not None
    ]

    mae = [
        value
        for row in rows
        if (
            value := num(
                row.get(
                    "mae_10m"
                )
            )
        )
        is not None
    ]

    return {
        "n": len(rows),

        "win": (
            sum(
                value > 0
                for value in returns
            )
            / len(returns)
            * 100
            if returns
            else 0.0
        ),

        "avg": (
            mean(returns)
            if returns
            else 0.0
        ),

        "continuation": (
            sum(
                value >= 0.20
                for value in returns
            )
            / len(returns)
            * 100
            if returns
            else 0.0
        ),

        "mfe": (
            mean(mfe)
            if mfe
            else 0.0
        ),

        "mae": (
            mean(mae)
            if mae
            else 0.0
        ),
    }


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


def print_groups(
    title,
    rows,
    key_func,
):

    grouped = defaultdict(
        list
    )

    for row in rows:

        grouped[
            key_func(row)
        ].append(
            row
        )

    print()
    print(
        "=" * 115
    )

    print(title)

    print(
        "=" * 115
    )

    for key, group in sorted(
        grouped.items()
    ):

        data = metrics(
            group
        )

        print(
            f"{key:30}",
            f"N={data['n']:4}",
            f"W10={data['win']:5.1f}%",
            f"A10={data['avg']:+7.3f}%",
            f">=.20={data['continuation']:5.1f}%",
            f"MFE={data['mfe']:+7.3f}%",
            f"MAE={data['mae']:+7.3f}%",
        )


def main():

    with PATH.open() as handle:

        rows = list(
            csv.DictReader(
                handle
            )
        )

    rows = [
        row
        for row in rows
        if row.get(
            "trigger_direction"
        ) in {
            "BULLISH",
            "BEARISH",
        }
    ]

    print()
    print(
        "DIRECTIONAL TRIGGER VALIDATION"
    )

    overall = metrics(rows)

    print(
        "Signals:",
        overall["n"],
    )

    print(
        f"10m win: {overall['win']:.1f}%"
    )

    print(
        f"Avg 10m: {overall['avg']:+.3f}%"
    )

    print(
        f">= +0.20%: "
        f"{overall['continuation']:.1f}%"
    )

    print(
        f"MFE: {overall['mfe']:+.3f}%"
    )

    print(
        f"MAE: {overall['mae']:+.3f}%"
    )

    print_groups(
        "DIRECTION",
        rows,
        lambda row:
            row.get(
                "trigger_direction",
                "UNKNOWN",
            ),
    )

    print_groups(
        "TRIGGER QUALITY",
        rows,
        quality_bucket,
    )

    print_groups(
        "DAY",
        rows,
        lambda row:
            row.get(
                "validation_session",
                "UNKNOWN",
            ),
    )


if __name__ == "__main__":

    main()
