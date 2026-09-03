from __future__ import annotations

import csv

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


def confluence_direction(
    row,
):

    setup = str(
        row.get(
            "setup",
            "NO_CONFLUENCE",
        )
    ).upper()

    if "BULLISH" in setup:
        return "BULLISH"

    if "BEARISH" in setup:
        return "BEARISH"

    return "NONE"


def confluence_strength(
    row,
):

    setup = str(
        row.get(
            "setup",
            "",
        )
    ).upper()

    if setup.startswith(
        "STRONG_"
    ):
        return "STRONG"

    if setup in {
        "BULLISH_CONFLUENCE",
        "BEARISH_CONFLUENCE",
    }:
        return "REGULAR"

    return "NONE"


def alignment(
    row,
):

    setup = str(
        row.get(
            "setup",
            "",
        )
    ).upper()

    trigger = str(
        row.get(
            "trigger_direction",
            "NONE",
        )
    ).upper()

    context = (
        confluence_direction(
            row
        )
    )

    if setup == "NO_CONFLUENCE":
        return "NO_CONFLUENCE"

    if setup == "CONFLICTED":
        return "CONFLICTED"

    if context == "NONE":
        return "OTHER"

    if context == trigger:
        return "ALIGNED"

    return "OPPOSED"


def detailed_alignment(
    row,
):

    group = alignment(
        row
    )

    if group != "ALIGNED":
        return group

    direction = (
        confluence_direction(
            row
        )
    )

    strength = (
        confluence_strength(
            row
        )
    )

    return (
        f"ALIGNED_{strength}_"
        f"{direction}"
    )


def opportunity_bucket(
    row,
):

    value = num(
        row.get(
            "opportunity_score"
        )
    )

    if value is None:
        return "UNKNOWN"

    if value < 50:
        return "40-50"

    if value < 60:
        return "50-60"

    if value < 70:
        return "60-70"

    return ">=70"


def metrics(
    rows,
):

    r5 = [
        value
        for row in rows
        if (
            value := num(
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

    days = defaultdict(
        list
    )

    for row in rows:

        day = row.get(
            "validation_session",
            "UNKNOWN",
        )

        value = num(
            row.get(
                "return_10m"
            )
        )

        if value is not None:

            days[
                day
            ].append(
                value
            )

    positive_days = sum(
        mean(values) > 0
        for values
        in days.values()
        if values
    )

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

        "med10":
            median(r10)
            if r10
            else 0.0,

        "continuation":
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

        "positive_days":
            positive_days,

        "days":
            len(days),
    }


def print_groups(
    title,
    rows,
    key_function,
    minimum_samples=10,
):

    groups = defaultdict(
        list
    )

    for row in rows:

        groups[
            key_function(
                row
            )
        ].append(
            row
        )

    print()
    print(
        "=" * 125
    )

    print(title)

    print(
        "=" * 125
    )

    output = []

    for key, group in groups.items():

        if (
            len(group)
            < minimum_samples
        ):
            continue

        result = metrics(
            group
        )

        output.append(
            (
                result["a10"],
                key,
                result,
            )
        )

    output.sort(
        key=lambda item:
            item[0],
        reverse=True,
    )

    for (
        _,
        key,
        data,
    ) in output:

        print(
            f"{str(key):36}",
            f"N={data['n']:4}",
            f"W5={data['w5']:5.1f}%",
            f"A5={data['a5']:+7.3f}%",
            f"W10={data['w10']:5.1f}%",
            f"A10={data['a10']:+7.3f}%",
            f"MED={data['med10']:+7.3f}%",
            f">=.20={data['continuation']:5.1f}%",
            f"MFE={data['mfe']:+7.3f}%",
            f"MAE={data['mae']:+7.3f}%",
            f"DAYS={data['positive_days']}/{data['days']}",
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
        if row.get(
            "trigger_direction"
        ) in {
            "BULLISH",
            "BEARISH",
        }
    ]

    print()
    print(
        "RECLAIM + CONTEXT INTERACTION"
    )

    print(
        "Signals:",
        len(rows),
    )

    print_groups(
        "CONFLUENCE / RECLAIM ALIGNMENT",
        rows,
        alignment,
    )

    print_groups(
        "DETAILED ALIGNMENT",
        rows,
        detailed_alignment,
    )

    aligned = [
        row
        for row in rows
        if alignment(row)
        == "ALIGNED"
    ]

    print()
    print(
        "Aligned signals:",
        len(aligned),
    )

    print_groups(
        "ALIGNED × OPPORTUNITY",
        aligned,
        opportunity_bucket,
    )

    print_groups(
        "ALIGNED × COMPRESSION STATE",
        aligned,
        lambda row:
            row.get(
                "compression_state",
                "NONE",
            ),
    )

    print_groups(
        "ALIGNED × RECLAIM DIRECTION",
        aligned,
        lambda row:
            row.get(
                "trigger_direction",
                "NONE",
            ),
    )

    print_groups(
        "ALIGNED × DAY",
        aligned,
        lambda row:
            row.get(
                "validation_session",
                "UNKNOWN",
            ),
        minimum_samples=5,
    )


if __name__ == "__main__":

    main()
