from __future__ import annotations

import asyncio
import csv

from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from . import historical_signal_validator as validator

from .market_data_quality import (
    nse_session_date,
)


MIN_NIFTY_CANDLES = 120
MAX_SESSIONS = 5


def _safe_float(value):

    try:
        if value is None:
            return None

        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None


def _metrics(rows):

    returns = [
        value
        for row in rows
        if (
            value := _safe_float(
                row.get(
                    "return_10m"
                )
            )
        )
        is not None
    ]

    if not returns:

        return {
            "signals": len(rows),
            "win_rate": 0.0,
            "avg_return": 0.0,
            "continuation": 0.0,
        }

    return {
        "signals":
            len(rows),

        "win_rate":
            (
                sum(
                    value > 0
                    for value
                    in returns
                )
                / len(returns)
                * 100
            ),

        "avg_return":
            mean(returns),

        "continuation":
            (
                sum(
                    value >= 0.20
                    for value
                    in returns
                )
                / len(returns)
                * 100
            ),
    }


async def discover_sessions():

    grouped = (
        await validator.load_history()
    )

    nifty = grouped.get(
        "NIFTY 50",
        [],
    )

    counts = Counter()

    for candle in nifty:

        session = (
            nse_session_date(
                candle["time"]
            )
        )

        if session is not None:

            counts[
                session
            ] += 1

    usable = [
        session
        for session, count
        in sorted(
            counts.items()
        )
        if count >= MIN_NIFTY_CANDLES
    ]

    return (
        counts,
        usable[
            -MAX_SESSIONS:
        ],
    )


async def main():

    session_counts, sessions = (
        await discover_sessions()
    )

    print()
    print(
        "=" * 100
    )

    print(
        "AVAILABLE NIFTY SESSIONS"
    )

    print(
        "=" * 100
    )

    for (
        session,
        count,
    ) in sorted(
        session_counts.items()
    ):

        marker = (
            "✅"
            if session in sessions
            else "-"
        )

        print(
            marker,
            session,
            "candles=",
            count,
        )

    if not sessions:

        print()
        print(
            "No sessions with enough "
            "NIFTY history."
        )

        return

    print()
    print(
        "Validating sessions:",
        len(sessions),
    )

    original_latest_session = (
        validator._latest_session
    )

    all_rows = []

    try:

        for session in sessions:

            print()
            print(
                "#" * 100
            )

            print(
                "VALIDATING",
                session,
            )

            print(
                "#" * 100
            )

            # Reuse the already working
            # look-ahead-safe validator,
            # but force the requested day.
            validator._latest_session = (
                lambda grouped,
                selected=session:
                    selected
            )

            (
                actual_session,
                observations,
            ) = await validator.run_validation()

            for row in observations:

                row[
                    "validation_session"
                ] = str(
                    actual_session
                )

            all_rows.extend(
                observations
            )

            data = _metrics(
                observations
            )

            print()
            print(
                "DAY SUMMARY"
            )

            print(
                "Signals:",
                data["signals"],
            )

            print(
                "10m win:",
                f'{data["win_rate"]:.1f}%',
            )

            print(
                "Avg 10m:",
                f'{data["avg_return"]:+.3f}%',
            )

            print(
                ">= +0.20%:",
                f'{data["continuation"]:.1f}%',
            )

    finally:

        validator._latest_session = (
            original_latest_session
        )

    if not all_rows:

        print(
            "No observations generated."
        )

        return

    # =================================================
    # PER-DAY PERFORMANCE
    # =================================================

    by_day = defaultdict(
        list
    )

    by_setup = defaultdict(
        list
    )

    for row in all_rows:

        by_day[
            row[
                "validation_session"
            ]
        ].append(
            row
        )

        by_setup[
            row[
                "setup"
            ]
        ].append(
            row
        )

    print()
    print(
        "=" * 100
    )

    print(
        "MULTI-DAY RESULTS"
    )

    print(
        "=" * 100
    )

    positive_days = 0

    for day in sorted(
        by_day
    ):

        metrics = _metrics(
            by_day[
                day
            ]
        )

        if (
            metrics[
                "avg_return"
            ]
            > 0
        ):
            positive_days += 1

        print(
            f"{day:12}",
            f"N={metrics['signals']:4}",
            f"W10={metrics['win_rate']:5.1f}%",
            f"A10={metrics['avg_return']:+7.3f}%",
            f">=.20={metrics['continuation']:5.1f}%",
        )

    print()
    print(
        "Positive-average days:",
        f"{positive_days}/{len(by_day)}",
    )

    # =================================================
    # SETUP RESULTS ACROSS DAYS
    # =================================================

    print()
    print(
        "=" * 100
    )

    print(
        "SETUP PERFORMANCE ACROSS DAYS"
    )

    print(
        "=" * 100
    )

    for setup in sorted(
        by_setup
    ):

        metrics = _metrics(
            by_setup[
                setup
            ]
        )

        setup_days = defaultdict(
            list
        )

        for row in by_setup[
            setup
        ]:

            setup_days[
                row[
                    "validation_session"
                ]
            ].append(
                row
            )

        profitable_setup_days = 0

        for rows in (
            setup_days.values()
        ):

            if (
                _metrics(
                    rows
                )[
                    "avg_return"
                ]
                > 0
            ):

                profitable_setup_days += 1

        print(
            f"{setup:32}",
            f"N={metrics['signals']:5}",
            f"W10={metrics['win_rate']:5.1f}%",
            f"A10={metrics['avg_return']:+7.3f}%",
            f">=.20={metrics['continuation']:5.1f}%",
            "positive_days="
            f"{profitable_setup_days}/{len(setup_days)}",
        )

    # =================================================
    # FEATURE TELEMETRY COVERAGE
    # =================================================

    compression = Counter(
        str(
            row.get(
                "compression_state",
                "MISSING",
            )
        )
        for row in all_rows
    )

    sweeps = Counter(
        str(
            row.get(
                "liquidity_sweep",
                "MISSING",
            )
        )
        for row in all_rows
    )

    breadth = Counter(
        str(
            row.get(
                "breadth_regime",
                "MISSING",
            )
        )
        for row in all_rows
    )

    print()
    print(
        "=" * 100
    )

    print(
        "FEATURE TELEMETRY COVERAGE"
    )

    print(
        "=" * 100
    )

    print(
        "Compression:",
        dict(
            compression
        ),
    )

    print(
        "Liquidity sweeps:",
        dict(
            sweeps
        ),
    )

    print(
        "Breadth:",
        dict(
            breadth
        ),
    )

    # =================================================
    # SAVE
    # =================================================

    output = Path(
        "logs/"
        "signal_validation_multi_day.csv"
    )

    with output.open(
        "w",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=list(
                all_rows[
                    0
                ].keys()
            ),
        )

        writer.writeheader()

        writer.writerows(
            all_rows
        )

    print()
    print(
        "Combined CSV:",
        output,
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )
