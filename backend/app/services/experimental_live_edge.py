from __future__ import annotations

import csv
import json
import time

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

from .market_data_quality import IST


LOG_DIR = Path("logs")

SIGNALS_PATH = (
    LOG_DIR
    / "live_experimental_signals.csv"
)

OUTCOMES_PATH = (
    LOG_DIR
    / "live_experimental_outcomes.csv"
)

STATE_PATH = (
    LOG_DIR
    / "live_experimental_state.json"
)


def _number(
    value: Any,
    default: float = 0.0,
) -> float:

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def _epoch(
    value: Any,
) -> int:

    try:

        value = float(value)

        if value > 10_000_000_000:
            value /= 1000

        return int(value)

    except (
        TypeError,
        ValueError,
    ):

        return 0


def _market_open() -> bool:

    now = datetime.now(
        IST
    )

    if now.weekday() >= 5:
        return False

    minute = (
        now.hour * 60
        + now.minute
    )

    return (
        9 * 60 + 15
        <= minute
        <= 15 * 60 + 30
    )


def _completed_candles(
    candles: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:

    if not candles:
        return []

    result = list(
        candles
    )

    if not _market_open():
        return result

    current_minute = (
        int(
            time.time()
        )
        // 60
        * 60
    )

    last_time = _epoch(
        result[-1].get(
            "time"
        )
    )

    # During live market the latest
    # bucket may still be forming.
    #
    # Experimental signals use CLOSED
    # one-minute candles only.
    if (
        last_time
        >= current_minute
    ):

        result = result[:-1]

    return result


def _context_direction(
    confluence: dict[
        str,
        Any,
    ],
) -> str:

    direction = str(
        confluence.get(
            "direction",
            "NEUTRAL",
        )
    ).upper()

    if direction in {
        "BULLISH",
        "BEARISH",
    }:
        return direction

    return "NONE"


def _structural_stop(
    *,
    candles: list[
        dict[str, Any]
    ],
    direction: str,
) -> float | None:

    if not candles:
        return None

    trigger = candles[-1]

    if direction == "BULLISH":

        low = _number(
            trigger.get(
                "low"
            )
        )

        if low <= 0:
            return None

        return (
            low
            * 0.9998
        )

    if direction == "BEARISH":

        high = _number(
            trigger.get(
                "high"
            )
        )

        if high <= 0:
            return None

        return (
            high
            * 1.0002
        )

    return None


def _risk_percent(
    *,
    price: float,
    stop: float | None,
) -> float | None:

    if (
        stop is None
        or price <= 0
    ):
        return None

    return (
        abs(
            price - stop
        )
        / price
        * 100
    )


def _append_csv(
    *,
    path: Path,
    fieldnames: list[str],
    row: dict[str, Any],
) -> None:

    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    exists = (
        path.exists()
        and path.stat().st_size > 0
    )

    with path.open(
        "a",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        if not exists:
            writer.writeheader()

        writer.writerow(
            row
        )


def _directional_return(
    *,
    entry: float,
    price: float,
    direction: str,
) -> float:

    if entry <= 0:
        return 0.0

    if direction == "BULLISH":

        return (
            (
                price
                - entry
            )
            / entry
            * 100
        )

    return (
        (
            entry
            - price
        )
        / entry
        * 100
    )


class ExperimentalPaperTracker:

    def __init__(
        self,
    ) -> None:

        LOG_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.pending: list[
            dict[str, Any]
        ] = []

        self.last_signal: dict[
            str,
            float,
        ] = {}

        self.active_keys: set[
            str
        ] = set()

        self._load()


    def _load(
        self,
    ) -> None:

        if not STATE_PATH.exists():
            return

        try:

            state = json.loads(
                STATE_PATH.read_text()
            )

            self.pending = list(
                state.get(
                    "pending",
                    [],
                )
            )

            self.last_signal = dict(
                state.get(
                    "last_signal",
                    {},
                )
            )

            self.active_keys = set(
                state.get(
                    "active_keys",
                    [],
                )
            )

        except Exception:

            self.pending = []
            self.last_signal = {}
            self.active_keys = set()


    def _save(
        self,
    ) -> None:

        state = {
            "pending":
                self.pending,

            "last_signal":
                self.last_signal,

            "active_keys":
                sorted(
                    self.active_keys
                ),
        }

        STATE_PATH.write_text(
            json.dumps(
                state,
                indent=2,
            )
        )


    def observe(
        self,
        *,
        candidates: list[
            dict[str, Any]
        ],
        price_map: dict[
            str,
            float,
        ],
    ) -> None:

        if not _market_open():
            return

        now = datetime.now(
            timezone.utc
        )

        now_ts = (
            now.timestamp()
        )

        # =================================
        # UPDATE EXISTING PAPER SIGNALS
        # =================================

        remaining = []

        for event in self.pending:

            detected_ts = float(
                event[
                    "detected_ts"
                ]
            )

            age = (
                now_ts
                - detected_ts
            )

            # Never carry an intraday
            # experiment into the next day.
            if age > 60 * 60:

                continue

            symbol = str(
                event[
                    "symbol"
                ]
            )

            current_price = (
                price_map.get(
                    symbol
                )
            )

            if (
                current_price is None
                or current_price <= 0
            ):

                remaining.append(
                    event
                )

                continue

            outcomes = event.setdefault(
                "outcomes",
                {},
            )

            for horizon in (
                5,
                10,
                15,
            ):

                key = str(
                    horizon
                )

                if key in outcomes:
                    continue

                if (
                    age
                    < horizon * 60
                ):
                    continue

                value = (
                    _directional_return(
                        entry=float(
                            event[
                                "entry_price"
                            ]
                        ),
                        price=float(
                            current_price
                        ),
                        direction=str(
                            event[
                                "direction"
                            ]
                        ),
                    )
                )

                outcomes[
                    key
                ] = {
                    "price":
                        round(
                            current_price,
                            4,
                        ),

                    "return_percent":
                        round(
                            value,
                            4,
                        ),

                    "observed_at":
                        now.isoformat(),
                }

                _append_csv(
                    path=(
                        OUTCOMES_PATH
                    ),

                    fieldnames=[
                        "event_id",
                        "symbol",
                        "direction",
                        "horizon_minutes",
                        "entry_price",
                        "observed_price",
                        "return_percent",
                        "opportunity_score",
                        "reclaim_quality",
                        "detected_at",
                        "observed_at",
                    ],

                    row={
                        "event_id":
                            event[
                                "event_id"
                            ],

                        "symbol":
                            symbol,

                        "direction":
                            event[
                                "direction"
                            ],

                        "horizon_minutes":
                            horizon,

                        "entry_price":
                            event[
                                "entry_price"
                            ],

                        "observed_price":
                            round(
                                current_price,
                                4,
                            ),

                        "return_percent":
                            round(
                                value,
                                4,
                            ),

                        "opportunity_score":
                            event[
                                "opportunity_score"
                            ],

                        "reclaim_quality":
                            event[
                                "reclaim_quality"
                            ],

                        "detected_at":
                            event[
                                "detected_at"
                            ],

                        "observed_at":
                            now.isoformat(),
                    },
                )

            if "15" not in outcomes:

                remaining.append(
                    event
                )

        self.pending = (
            remaining
        )

        # =================================
        # REGISTER NEW CANDIDATES
        # =================================

        current_active: set[
            str
        ] = set()

        for candidate in candidates:

            symbol = str(
                candidate[
                    "symbol"
                ]
            )

            direction = str(
                candidate[
                    "direction"
                ]
            )

            event_key = (
                f"{symbol}:"
                f"{direction}"
            )

            current_active.add(
                event_key
            )

            # Same setup is still active.
            if (
                event_key
                in self.active_keys
            ):
                continue

            previous = float(
                self.last_signal.get(
                    event_key,
                    0.0,
                )
            )

            # 20-minute minimum separation
            # between independent events.
            if (
                now_ts - previous
                < 20 * 60
            ):
                continue

            entry_price = _number(
                candidate.get(
                    "ltp"
                )
            )

            if entry_price <= 0:
                continue

            event_id = (
                now.strftime(
                    "%Y%m%dT%H%M%S"
                )
                + "_"
                + symbol
                + "_"
                + direction
            )

            event = {
                "event_id":
                    event_id,

                "detected_ts":
                    now_ts,

                "detected_at":
                    now.isoformat(),

                "symbol":
                    symbol,

                "direction":
                    direction,

                "entry_price":
                    round(
                        entry_price,
                        4,
                    ),

                "opportunity_score":
                    candidate[
                        "opportunity_score"
                    ],

                "opportunity_state":
                    candidate[
                        "opportunity_state"
                    ],

                "reclaim_quality":
                    candidate[
                        "reclaim_quality"
                    ],

                "context_setup":
                    candidate[
                        "context_setup"
                    ],

                "context_direction":
                    candidate[
                        "context_direction"
                    ],

                "structural_stop":
                    candidate.get(
                        "structural_stop"
                    ),

                "structural_risk_percent":
                    candidate.get(
                        "structural_risk_percent"
                    ),

                "outcomes":
                    {},
            }

            self.pending.append(
                event
            )

            self.last_signal[
                event_key
            ] = now_ts

            _append_csv(
                path=(
                    SIGNALS_PATH
                ),

                fieldnames=[
                    "event_id",
                    "detected_at",
                    "symbol",
                    "direction",
                    "entry_price",
                    "opportunity_score",
                    "opportunity_state",
                    "reclaim_quality",
                    "context_setup",
                    "context_direction",
                    "structural_stop",
                    "structural_risk_percent",
                ],

                row={
                    key:
                        event.get(
                            key
                        )
                    for key in [
                        "event_id",
                        "detected_at",
                        "symbol",
                        "direction",
                        "entry_price",
                        "opportunity_score",
                        "opportunity_state",
                        "reclaim_quality",
                        "context_setup",
                        "context_direction",
                        "structural_stop",
                        "structural_risk_percent",
                    ]
                },
            )

            print(
                "[PAPER EDGE]",
                symbol,
                direction,
                "OPP=",
                candidate[
                    "opportunity_score"
                ],
                "RECLAIM=",
                candidate[
                    "reclaim_quality"
                ],
            )

        self.active_keys = (
            current_active
        )

        self._save()


_PAPER_TRACKER = (
    ExperimentalPaperTracker()
)


def attach_experimental_live_edge(
    *,
    snapshot: dict[
        str,
        Any,
    ],
    candle_engine: Any,
) -> dict[
    str,
    Any
]:
    """
    Add experimental research fields to
    the normal Fast Scanner snapshot.

    DOES NOT modify:
    - Fast Score
    - original direction
    - ranking logic
    - execution logic
    """

    breadth = snapshot.get(
        "market_breadth",
        {},
    )

    candidates = []

    opportunity_rows = []

    price_map = {}

    ready_count = 0
    opportunity_40 = 0
    opportunity_50 = 0
    opportunity_60 = 0
    opposed_count = 0

    for stock in snapshot.get(
        "results",
        [],
    ):

        symbol = str(
            stock.get(
                "symbol",
                "",
            )
        ).upper()

        ltp = _number(
            stock.get(
                "ltp"
            )
        )

        if symbol and ltp > 0:

            price_map[
                symbol
            ] = ltp

        if (
            stock.get(
                "status"
            )
            != "READY"
        ):

            continue

        ready_count += 1

        try:

            one_minute = (
                candle_engine.candles(
                    symbol,
                    "1m",
                    limit=30,
                )
            )

            completed = (
                _completed_candles(
                    one_minute
                )
            )

            compression = (
                analyze_compression_expansion(
                    completed
                )
            )

            sweep = (
                analyze_liquidity_sweep(
                    completed
                )
            )

            context_stock = dict(
                stock
            )

            context_stock[
                "compression_expansion"
            ] = compression

            context_stock[
                "liquidity_sweep"
            ] = sweep

            opportunity = (
                analyze_movement_opportunity(
                    stock=(
                        context_stock
                    ),
                    market_breadth=(
                        breadth
                    ),
                )
            )

            confluence = (
                analyze_setup_confluence(
                    stock=(
                        context_stock
                    ),
                    market_breadth=(
                        breadth
                    ),
                )
            )

            reclaim = (
                analyze_reclaim_reversal_trigger(
                    candles=(
                        completed
                    ),
                    opportunity=(
                        opportunity
                    ),
                )
            )

            opportunity_score = (
                _number(
                    opportunity.get(
                        "score"
                    )
                )
            )

            opportunity_state = str(
                opportunity.get(
                    "state",
                    "NORMAL",
                )
            )

            reclaim_direction = str(
                reclaim.get(
                    "direction",
                    "NONE",
                )
            ).upper()

            context_direction = (
                _context_direction(
                    confluence
                )
            )

            opposed = (
                reclaim_direction
                in {
                    "BULLISH",
                    "BEARISH",
                }
                and context_direction
                in {
                    "BULLISH",
                    "BEARISH",
                }
                and reclaim_direction
                != context_direction
            )

            if opportunity_score >= 40:
                opportunity_40 += 1

            if opportunity_score >= 50:
                opportunity_50 += 1

            if opportunity_score >= 60:
                opportunity_60 += 1

            if opposed:
                opposed_count += 1

            structural_stop = (
                _structural_stop(
                    candles=completed,
                    direction=(
                        reclaim_direction
                    ),
                )
                if opposed
                else None
            )

            structural_risk = (
                _risk_percent(
                    price=ltp,
                    stop=(
                        structural_stop
                    ),
                )
            )

            experimental = {
                "status": (
                    "PAPER_CANDIDATE"
                    if opposed
                    else "WATCH"
                    if opportunity_score
                    >= 40
                    else "IGNORE"
                ),

                "paper_candidate":
                    opposed,

                "opportunity_score":
                    round(
                        opportunity_score,
                        2,
                    ),

                "opportunity_state":
                    opportunity_state,

                "context_setup":
                    confluence.get(
                        "setup",
                        "NO_CONFLUENCE",
                    ),

                "context_direction":
                    context_direction,

                "context_quality":
                    confluence.get(
                        "quality",
                        0.0,
                    ),

                "reclaim_state":
                    reclaim.get(
                        "state",
                        "NO_TRIGGER",
                    ),

                "reclaim_direction":
                    reclaim_direction,

                "reclaim_quality":
                    reclaim.get(
                        "quality",
                        0.0,
                    ),

                "opposed_reclaim":
                    opposed,

                "compression_state":
                    compression.get(
                        "state",
                        "NONE",
                    ),

                "liquidity_sweep":
                    sweep.get(
                        "state",
                        "NONE",
                    ),

                "structural_stop": (
                    round(
                        structural_stop,
                        4,
                    )
                    if structural_stop
                    is not None
                    else None
                ),

                "structural_risk_percent": (
                    round(
                        structural_risk,
                        3,
                    )
                    if structural_risk
                    is not None
                    else None
                ),
            }

            stock[
                "experimental_edge"
            ] = experimental

            opportunity_rows.append(
                {
                    "symbol":
                        symbol,

                    "ltp":
                        ltp,

                    "opportunity_score":
                        round(
                            opportunity_score,
                            2,
                        ),

                    "opportunity_state":
                        opportunity_state,

                    "status":
                        experimental[
                            "status"
                        ],

                    # =================================
                    # V2.4 OPPORTUNITY INTELLIGENCE
                    # =================================

                    "rvol":
                        opportunity.get(
                            "rvol",
                            0.0,
                        ),

                    "rvol_source":
                        opportunity.get(
                            "source",
                            "UNKNOWN",
                        ),

                    "direction_hint":
                        opportunity.get(
                            "direction_hint",
                            "NONE",
                        ),

                    "direction_agreement":
                        opportunity.get(
                            "direction_agreement",
                            0.0,
                        ),

                    "movement_reasons":
                        opportunity.get(
                            "reasons",
                            [],
                        ),

                    "movement_components":
                        opportunity.get(
                            "components",
                            {},
                        ),

                    "relative_strength":
                        stock.get(
                            "relative_strength",
                            {},
                        ),

                    "rs_acceleration":
                        stock.get(
                            "rs_acceleration",
                            {},
                        ),

                    "change_1m_percent":
                        stock.get(
                            "change_1m_percent",
                            0.0,
                        ),

                    "change_5m_percent":
                        stock.get(
                            "change_5m_percent",
                            0.0,
                        ),

                    "fast_score":
                        stock.get(
                            "fast_score",
                            0.0,
                        ),

                    "compression_state":
                        compression.get(
                            "state",
                            "NONE",
                        ),

                    "compression_score":
                        compression.get(
                            "score",
                            0.0,
                        ),

                    "liquidity_sweep":
                        sweep.get(
                            "state",
                            "NONE",
                        ),

                    "liquidity_sweep_quality":
                        sweep.get(
                            "quality",
                            0.0,
                        ),

                    "context_setup":
                        confluence.get(
                            "setup",
                            "NO_CONFLUENCE",
                        ),

                    "context_direction":
                        context_direction,

                    "context_quality":
                        confluence.get(
                            "quality",
                            0.0,
                        ),
                }
            )

            if opposed:

                candidates.append(
                    {
                        "symbol":
                            symbol,

                        "ltp":
                            ltp,

                        "direction":
                            reclaim_direction,

                        "opportunity_score":
                            round(
                                opportunity_score,
                                2,
                            ),

                        "opportunity_state":
                            opportunity_state,

                        "reclaim_quality":
                            reclaim.get(
                                "quality",
                                0.0,
                            ),

                        "reclaim_state":
                            reclaim.get(
                                "state",
                                "",
                            ),

                        "context_setup":
                            confluence.get(
                                "setup",
                                "NO_CONFLUENCE",
                            ),

                        "context_direction":
                            context_direction,

                        "structural_stop":
                            experimental[
                                "structural_stop"
                            ],

                        "structural_risk_percent":
                            experimental[
                                "structural_risk_percent"
                            ],
                    }
                )

        except Exception as exc:

            stock[
                "experimental_edge"
            ] = {
                "status":
                    "ERROR",

                "paper_candidate":
                    False,

                "error":
                    str(exc),
            }

    opportunity_rows.sort(
        key=lambda row:
            row[
                "opportunity_score"
            ],
        reverse=True,
    )

    candidates.sort(
        key=lambda row:
            (
                row[
                    "opportunity_score"
                ],
                _number(
                    row[
                        "reclaim_quality"
                    ]
                ),
            ),
        reverse=True,
    )

    snapshot[
        "experimental_edge_summary"
    ] = {
        "mode":
            "PAPER_ONLY",

        "ready_stocks":
            ready_count,

        "opportunity_40_plus":
            opportunity_40,

        "opportunity_50_plus":
            opportunity_50,

        "opportunity_60_plus":
            opportunity_60,

        "opposed_reclaim_candidates":
            opposed_count,

        "pending_paper_outcomes":
            len(
                _PAPER_TRACKER.pending
            ),

        "top_opportunities":
            opportunity_rows[:15],

        "paper_candidates":
            candidates[:20],
    }

    # Automatically collect forward
    # evidence during NSE live hours.
    _PAPER_TRACKER.observe(
        candidates=candidates,
        price_map=price_map,
    )

    return snapshot
