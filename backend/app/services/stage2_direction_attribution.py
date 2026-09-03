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


def opportunity_bucket(row):

    score = number(
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


def metrics(rows):

    r5 = [
        value
        for row in rows
        if (
            value := number(
                row.get(
                    "return_5m"
                )
            )
        )
        is not None
    ]

    r10 = [
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

    mfe = [
        value
        for row in rows
        if (
            value := number(
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
            value := number(
                row.get(
                    "mae_10m"
                )
            )
        )
        is not None
    ]

    return {
        "n":
            len(rows),

        "w5":
            (
                sum(
                    value > 0
                    for value in r5
                )
                / len(r5)
                * 100
            )
            if r5
            else 0.0,

        "a5":
            mean(r5)
            if r5
            else 0.0,

        "w10":
            (
                sum(
                    value > 0
                    for value in r10
                )
                / len(r10)
                * 100
            )
            if r10
            else 0.0,

        "a10":
            mean(r10)
            if r10
            else 0.0,

        "cont":
            (
                sum(
                    value >= 0.20
                    for value in r10
                )
                / len(r10)
                * 100
            )
            if r10
            else 0.0,

        "mfe":
            mean(mfe)
            if mfe
            else 0.0,

        "mae":
            mean(mae)
            if mae
            else 0.0,
    }


def print_group(
    title,
    rows,
    key_func,
):

    groups = defaultdict(
        list
    )

    for row in rows:

        groups[
            key_func(row)
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
        groups.items(),
        key=lambda item:
            item[0],
    ):

        data = metrics(
            group
        )

        print(
            f"{key:30}",
            f"N={data['n']:4}",
            f"W5={data['w5']:5.1f}%",
            f"A5={data['a5']:+6.3f}%",
            f"W10={data['w10']:5.1f}%",
            f"A10={data['a10']:+6.3f}%",
            f">=.20={data['cont']:5.1f}%",
            f"MFE={data['mfe']:+6.3f}%",
            f"MAE={data['mae']:+6.3f}%",
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
        if (
            row.get(
                "stage2_direction"
            )
            in {
                "BULLISH",
                "BEARISH",
            }
        )
    ]

    print()
    print(
        "STAGE 2 DIRECTION VALIDATION"
    )

    print(
        "Signals:",
        len(rows),
    )

    overall = metrics(
        rows
    )

    print()
    print(
        "OVERALL"
    )

    print(
        f"W10={overall['w10']:.1f}% "
        f"A10={overall['a10']:+.3f}% "
        f">=.20={overall['cont']:.1f}% "
        f"MFE={overall['mfe']:+.3f}% "
        f"MAE={overall['mae']:+.3f}%"
    )

    print_group(
        "STAGE 2 STATE",
        rows,
        lambda row:
            row.get(
                "stage2_state",
                "UNKNOWN",
            ),
    )

    print_group(
        "DIRECTION",
        rows,
        lambda row:
            row.get(
                "stage2_direction",
                "UNKNOWN",
            ),
    )

    print_group(
        "OPPORTUNITY SCORE",
        rows,
        opportunity_bucket,
    )

    print_group(
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
