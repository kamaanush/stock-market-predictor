from __future__ import annotations

import csv

from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any


CSV_PATH = Path(
    "logs/signal_validation_2026-08-31.csv"
)


def safe_float(
    value: Any,
) -> float | None:

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


def safe_bool(
    value: Any,
) -> bool:

    return str(
        value
    ).strip().lower() in {
        "true",
        "1",
        "yes",
    }


def load_rows():

    if not CSV_PATH.exists():

        raise RuntimeError(
            f"CSV not found: {CSV_PATH}"
        )

    with CSV_PATH.open() as handle:

        return list(
            csv.DictReader(
                handle
            )
        )


def rvol_bucket(
    row,
):

    value = safe_float(
        row.get("rvol")
    )

    if value is None:
        return "UNKNOWN"

    if value < 1.0:
        return "<1.0x"

    if value < 1.3:
        return "1.0-1.3x"

    if value < 2.0:
        return "1.3-2.0x"

    if value < 3.0:
        return "2.0-3.0x"

    return ">=3.0x"


def quality_bucket(
    row,
):

    value = safe_float(
        row.get("quality")
    )

    if value is None:
        return "UNKNOWN"

    if value < 0.40:
        return "<0.40"

    if value < 0.50:
        return "0.40-0.50"

    if value < 0.60:
        return "0.50-0.60"

    if value < 0.70:
        return "0.60-0.70"

    return ">=0.70"


def rs_strength_bucket(
    row,
):

    value = safe_float(
        row.get(
            "rs_strength"
        )
    )

    if value is None:
        return "UNKNOWN"

    value = abs(value)

    if value < 0.50:
        return "<0.50"

    if value < 1.0:
        return "0.50-1.00"

    if value < 2.0:
        return "1.00-2.00"

    return ">=2.00"


def acceleration_bucket(
    row,
):

    quality = safe_float(
        row.get(
            "rs_acceleration_quality"
        )
    )

    if quality is None:
        return "UNKNOWN"

    if quality < 0.20:
        return "<0.20"

    if quality < 0.40:
        return "0.20-0.40"

    if quality < 0.60:
        return "0.40-0.60"

    return ">=0.60"


def time_bucket(
    row,
):

    value = str(
        row.get(
            "cutoff",
            "",
        )
    )

    if not value:
        return "UNKNOWN"

    hour, minute = map(
        int,
        value.split(":")
    )

    total = (
        hour * 60
        + minute
    )

    if total <= (
        10 * 60 + 30
    ):
        return "OPEN"

    if total <= (
        13 * 60 + 30
    ):
        return "MIDDAY"

    return "LATE"


def sweep_bucket(
    row,
):

    if safe_bool(
        row.get(
            "strong_sweep"
        )
    ):
        return "STRONG_SWEEP"

    state = str(
        row.get(
            "liquidity_sweep",
            "NONE",
        )
    )

    if (
        state
        not in {
            "",
            "NONE",
            "ZERO_RANGE",
            "INSUFFICIENT_DATA",
        }
    ):
        return "WEAK_SWEEP"

    return "NO_SWEEP"


def calculate_metrics(
    rows,
):

    return_5 = [
        value
        for row in rows
        if (
            value := safe_float(
                row.get(
                    "return_5m"
                )
            )
        )
        is not None
    ]

    return_10 = [
        value
        for row in rows
        if (
            value := safe_float(
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
            value := safe_float(
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
            value := safe_float(
                row.get(
                    "mae_10m"
                )
            )
        )
        is not None
    ]

    return {
        "count":
            len(rows),

        "win5":
            (
                sum(
                    value > 0
                    for value
                    in return_5
                )
                / len(return_5)
                * 100
            )
            if return_5
            else 0.0,

        "avg5":
            mean(return_5)
            if return_5
            else 0.0,

        "win10":
            (
                sum(
                    value > 0
                    for value
                    in return_10
                )
                / len(return_10)
                * 100
            )
            if return_10
            else 0.0,

        "avg10":
            mean(return_10)
            if return_10
            else 0.0,

        "median10":
            median(return_10)
            if return_10
            else 0.0,

        "continuation":
            (
                sum(
                    value >= 0.20
                    for value
                    in return_10
                )
                / len(return_10)
                * 100
            )
            if return_10
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
    key_function,
    *,
    minimum_samples=30,
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
        "=" * 120
    )

    print(title)

    print(
        "=" * 120
    )

    output = []

    for key, group in groups.items():

        if len(group) < minimum_samples:
            continue

        metrics = (
            calculate_metrics(
                group
            )
        )

        output.append(
            (
                metrics[
                    "avg10"
                ],
                key,
                metrics,
            )
        )

    output.sort(
        reverse=True,
        key=lambda row:
            row[0],
    )

    for (
        _,
        key,
        data,
    ) in output:

        print(
            f"{str(key):28}",
            f"N={data['count']:4}",
            f"W5={data['win5']:5.1f}%",
            f"A5={data['avg5']:+6.3f}%",
            f"W10={data['win10']:5.1f}%",
            f"A10={data['avg10']:+6.3f}%",
            f"MED10={data['median10']:+6.3f}%",
            f">=.20={data['continuation']:5.1f}%",
            f"MFE={data['mfe']:+6.3f}%",
            f"MAE={data['mae']:+6.3f}%",
        )


def main():

    rows = load_rows()

    print()
    print(
        "SIGNAL FEATURE ATTRIBUTION"
    )

    print(
        "Signals:",
        len(rows),
    )

    print_group(
        "SETUP",
        rows,
        lambda row:
            row.get(
                "setup",
                "UNKNOWN",
            ),
    )

    print_group(
        "TIME OF DAY",
        rows,
        time_bucket,
    )

    print_group(
        "RVOL",
        rows,
        rvol_bucket,
    )

    print_group(
        "CONFLUENCE QUALITY",
        rows,
        quality_bucket,
    )

    print_group(
        "ABSOLUTE RS STRENGTH",
        rows,
        rs_strength_bucket,
    )

    print_group(
        "RS ACCELERATION QUALITY",
        rows,
        acceleration_bucket,
    )

    print_group(
        "LIQUIDITY SWEEP",
        rows,
        sweep_bucket,
    )

    print_group(
        "COMPRESSION STATE",
        rows,
        lambda row:
            row.get(
                "compression_state",
                "UNKNOWN",
            ),
    )

    print_group(
        "MARKET BREADTH",
        rows,
        lambda row:
            row.get(
                "breadth_regime",
                "UNKNOWN",
            ),
    )

    print_group(
        "VOLUME SOURCE",
        rows,
        lambda row:
            row.get(
                "volume_source",
                "UNKNOWN",
            ),
    )


if __name__ == "__main__":
    main()
