from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Tuple


def _number(
    value: Any,
    default: Optional[float] = None,
) -> Optional[float]:
    try:
        number = float(value)

        if number != number:
            return default

        return number

    except (TypeError, ValueError):
        return default


def _timestamp(
    value: Any,
) -> Optional[float]:
    if value is None:
        return None

    try:
        number = float(value)

        if number > 10_000_000_000:
            number /= 1000.0

        return number

    except (TypeError, ValueError):
        pass

    try:
        return datetime.fromisoformat(
            str(value).replace(
                "Z",
                "+00:00",
            )
        ).timestamp()

    except Exception:
        return None


def _market_timestamp(
    *,
    ticks: List[Dict[str, Any]],
    snapshot: Dict[str, Any],
) -> float:
    values: List[float] = []

    for tick in ticks:
        value = _timestamp(
            tick.get(
                "exchange_timestamp"
            )
        )

        if value is None:
            value = _timestamp(
                tick.get(
                    "received_at"
                )
            )

        if value is not None:
            values.append(
                value
            )

    if values:
        return max(values)

    generated = _timestamp(
        snapshot.get(
            "generated_at"
        )
    )

    if generated is not None:
        return generated

    return datetime.now(
        timezone.utc
    ).timestamp()


def _extract_rvol(
    stock: Dict[str, Any],
    edge: Dict[str, Any],
) -> Optional[float]:
    candidates = [
        edge.get("rvol"),
        edge.get("time_rvol"),
        stock.get("rvol"),
        stock.get("time_rvol"),
        stock.get("relative_volume"),
        stock.get("volume_ratio"),
    ]

    for value in candidates:
        number = _number(
            value
        )

        if number is not None:
            return number

    nested_candidates = [
        edge.get(
            "time_normalized_rvol"
        ),
        stock.get(
            "time_normalized_rvol"
        ),
    ]

    for candidate in nested_candidates:
        if not isinstance(
            candidate,
            dict,
        ):
            continue

        for key in (
            "rvol",
            "ratio",
            "value",
            "relative_volume",
        ):
            number = _number(
                candidate.get(key)
            )

            if number is not None:
                return number

    return None


class OpportunityVelocityTracker:
    def __init__(
        self,
        history_seconds: int = 900,
        entrant_ttl_seconds: int = 180,
    ) -> None:
        self.history_seconds = (
            history_seconds
        )

        self.entrant_ttl_seconds = (
            entrant_ttl_seconds
        )

        self.history = defaultdict(
            deque
        )

        self.entrant_events = deque()

        self.last_batch_timestamp = None

    def reset(
        self,
    ) -> None:
        self.history.clear()
        self.entrant_events.clear()

        self.last_batch_timestamp = (
            None
        )

    @staticmethod
    def _historical_point(
        history: Deque[Dict[str, Any]],
        target_timestamp: float,
    ) -> Optional[Dict[str, Any]]:
        for point in reversed(
            history
        ):
            timestamp = _number(
                point.get(
                    "timestamp"
                )
            )

            if (
                timestamp is not None
                and timestamp
                <= target_timestamp
            ):
                return point

        return None

    def update(
        self,
        *,
        snapshot: Dict[str, Any],
        ticks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        source_timestamp = (
            _market_timestamp(
                ticks=ticks,
                snapshot=snapshot,
            )
        )

        # If replay/backfill moves backwards,
        # don't mix different market periods.
        if (
            self.last_batch_timestamp
            is not None
            and source_timestamp
            < self.last_batch_timestamp - 60
        ):
            self.reset()

        is_new_batch = (
            self.last_batch_timestamp
            is None
            or source_timestamp
            > self.last_batch_timestamp + 0.5
        )

        results = list(
            snapshot.get(
                "results",
                [],
            )
            or []
        )

        enriched_results = []
        velocity_by_symbol = {}
        rising_rows = []

        for original_stock in results:
            if not isinstance(
                original_stock,
                dict,
            ):
                continue

            stock = dict(
                original_stock
            )

            symbol = str(
                stock.get(
                    "symbol",
                    "",
                )
            ).strip().upper()

            edge_raw = stock.get(
                "experimental_edge",
                {},
            )

            edge = (
                dict(edge_raw)
                if isinstance(
                    edge_raw,
                    dict,
                )
                else {}
            )

            score = _number(
                edge.get(
                    "opportunity_score"
                )
            )

            if score is None:
                score = _number(
                    stock.get(
                        "opportunity_score"
                    )
                )

            rvol = _extract_rvol(
                stock,
                edge,
            )

            if (
                not symbol
                or score is None
            ):
                enriched_results.append(
                    stock
                )
                continue

            history = self.history[
                symbol
            ]

            previous = (
                history[-1]
                if history
                else None
            )

            previous_score = (
                _number(
                    previous.get(
                        "score"
                    )
                )
                if previous
                else None
            )

            if is_new_batch:
                while history:
                    oldest_timestamp = (
                        _number(
                            history[0].get(
                                "timestamp"
                            )
                        )
                    )

                    if (
                        oldest_timestamp
                        is None
                    ):
                        history.popleft()
                        continue

                    if (
                        source_timestamp
                        - oldest_timestamp
                        <= self.history_seconds
                    ):
                        break

                    history.popleft()

                history.append(
                    {
                        "timestamp":
                            source_timestamp,
                        "score":
                            score,
                        "rvol":
                            rvol,
                    }
                )

            point_1m = (
                self._historical_point(
                    history,
                    source_timestamp - 60,
                )
            )

            point_5m = (
                self._historical_point(
                    history,
                    source_timestamp - 300,
                )
            )

            score_1m = (
                _number(
                    point_1m.get(
                        "score"
                    )
                )
                if point_1m
                else None
            )

            score_5m = (
                _number(
                    point_5m.get(
                        "score"
                    )
                )
                if point_5m
                else None
            )

            rvol_1m = (
                _number(
                    point_1m.get(
                        "rvol"
                    )
                )
                if point_1m
                else None
            )

            rvol_5m = (
                _number(
                    point_5m.get(
                        "rvol"
                    )
                )
                if point_5m
                else None
            )

            delta_1m = (
                score - score_1m
                if score_1m
                is not None
                else None
            )

            delta_5m = (
                score - score_5m
                if score_5m
                is not None
                else None
            )

            rvol_delta_1m = (
                rvol - rvol_1m
                if (
                    rvol is not None
                    and rvol_1m
                    is not None
                )
                else None
            )

            rvol_delta_5m = (
                rvol - rvol_5m
                if (
                    rvol is not None
                    and rvol_5m
                    is not None
                )
                else None
            )

            crossed_thresholds = []

            if (
                is_new_batch
                and previous_score
                is not None
            ):
                for threshold in (
                    40,
                    50,
                    60,
                ):
                    if (
                        previous_score
                        < threshold
                        <= score
                    ):
                        crossed_thresholds.append(
                            threshold
                        )

            new_threshold = (
                max(
                    crossed_thresholds
                )
                if crossed_thresholds
                else None
            )

            if (
                new_threshold
                is not None
            ):
                self.entrant_events.append(
                    {
                        "symbol":
                            symbol,

                        "threshold":
                            new_threshold,

                        "opportunity_score":
                            round(
                                score,
                                2,
                            ),

                        "rvol":
                            (
                                round(
                                    rvol,
                                    2,
                                )
                                if rvol
                                is not None
                                else None
                            ),

                        "crossed_at":
                            datetime.fromtimestamp(
                                source_timestamp,
                                tz=timezone.utc,
                            ).isoformat(),
                    }
                )

            if (
                delta_1m is None
                and delta_5m is None
            ):
                velocity_state = (
                    "WARMING_UP"
                )

            elif (
                (
                    delta_1m is not None
                    and delta_1m > 0
                )
                or (
                    delta_5m is not None
                    and delta_5m > 0
                )
            ):
                velocity_state = (
                    "RISING"
                )

            elif (
                (
                    delta_1m is not None
                    and delta_1m < 0
                )
                or (
                    delta_5m is not None
                    and delta_5m < 0
                )
            ):
                velocity_state = (
                    "FALLING"
                )

            else:
                velocity_state = (
                    "FLAT"
                )

            velocity = {
                "score_now":
                    round(
                        score,
                        2,
                    ),

                "score_1m_ago":
                    (
                        round(
                            score_1m,
                            2,
                        )
                        if score_1m
                        is not None
                        else None
                    ),

                "score_5m_ago":
                    (
                        round(
                            score_5m,
                            2,
                        )
                        if score_5m
                        is not None
                        else None
                    ),

                "delta_1m":
                    (
                        round(
                            delta_1m,
                            2,
                        )
                        if delta_1m
                        is not None
                        else None
                    ),

                "delta_5m":
                    (
                        round(
                            delta_5m,
                            2,
                        )
                        if delta_5m
                        is not None
                        else None
                    ),

                "rvol_now":
                    (
                        round(
                            rvol,
                            2,
                        )
                        if rvol
                        is not None
                        else None
                    ),

                "rvol_1m_ago":
                    (
                        round(
                            rvol_1m,
                            2,
                        )
                        if rvol_1m
                        is not None
                        else None
                    ),

                "rvol_5m_ago":
                    (
                        round(
                            rvol_5m,
                            2,
                        )
                        if rvol_5m
                        is not None
                        else None
                    ),

                "rvol_delta_1m":
                    (
                        round(
                            rvol_delta_1m,
                            2,
                        )
                        if rvol_delta_1m
                        is not None
                        else None
                    ),

                "rvol_delta_5m":
                    (
                        round(
                            rvol_delta_5m,
                            2,
                        )
                        if rvol_delta_5m
                        is not None
                        else None
                    ),

                "state":
                    velocity_state,

                "new_threshold":
                    new_threshold,
            }

            edge[
                "opportunity_velocity"
            ] = velocity

            stock[
                "experimental_edge"
            ] = edge

            velocity_by_symbol[
                symbol
            ] = velocity

            is_rising = (
                (
                    delta_1m
                    is not None
                    and delta_1m > 0
                )
                or (
                    delta_5m
                    is not None
                    and delta_5m > 0
                )
            )

            if is_rising:
                rising_rows.append(
                    {
                        "symbol":
                            symbol,

                        "ltp":
                            stock.get(
                                "ltp"
                            ),

                        "opportunity_score":
                            round(
                                score,
                                2,
                            ),

                        "delta_1m":
                            velocity[
                                "delta_1m"
                            ],

                        "delta_5m":
                            velocity[
                                "delta_5m"
                            ],

                        "rvol":
                            velocity[
                                "rvol_now"
                            ],

                        "rvol_delta_1m":
                            velocity[
                                "rvol_delta_1m"
                            ],

                        "rvol_delta_5m":
                            velocity[
                                "rvol_delta_5m"
                            ],

                        "volume":
                            stock.get(
                                "volume"
                            ),

                        "change_1m_percent":
                            (
                                edge.get(
                                    "change_1m_percent"
                                )
                                if edge.get(
                                    "change_1m_percent"
                                )
                                is not None
                                else stock.get(
                                    "change_1m_percent"
                                )
                            ),

                        "change_5m_percent":
                            (
                                edge.get(
                                    "change_5m_percent"
                                )
                                if edge.get(
                                    "change_5m_percent"
                                )
                                is not None
                                else stock.get(
                                    "change_5m_percent"
                                )
                            ),
                    }
                )

            enriched_results.append(
                stock
            )

        # Keep New Entrants visible for a few minutes.
        while self.entrant_events:
            event_timestamp = _timestamp(
                self.entrant_events[
                    0
                ].get(
                    "crossed_at"
                )
            )

            if event_timestamp is None:
                self.entrant_events.popleft()
                continue

            if (
                source_timestamp
                - event_timestamp
                <= self.entrant_ttl_seconds
            ):
                break

            self.entrant_events.popleft()

        def rising_sort_key(
            row: Dict[str, Any],
        ) -> Tuple[
            float,
            float,
            float,
            float,
        ]:
            delta_1m_value = _number(
                row.get(
                    "delta_1m"
                ),
                -999.0,
            )

            delta_5m_value = _number(
                row.get(
                    "delta_5m"
                ),
                -999.0,
            )

            rvol_delta_value = _number(
                row.get(
                    "rvol_delta_1m"
                ),
                -999.0,
            )

            score_value = _number(
                row.get(
                    "opportunity_score"
                ),
                0.0,
            )

            return (
                delta_1m_value
                if delta_1m_value
                is not None
                else -999.0,

                delta_5m_value
                if delta_5m_value
                is not None
                else -999.0,

                rvol_delta_value
                if rvol_delta_value
                is not None
                else -999.0,

                score_value
                if score_value
                is not None
                else 0.0,
            )

        rising_rows.sort(
            key=rising_sort_key,
            reverse=True,
        )

        new_snapshot = dict(
            snapshot
        )

        new_snapshot[
            "results"
        ] = enriched_results

        summary_raw = (
            new_snapshot.get(
                "experimental_edge_summary",
                {},
            )
        )

        summary = (
            dict(summary_raw)
            if isinstance(
                summary_raw,
                dict,
            )
            else {}
        )

        opportunity_rows = list(
            summary.get(
                "opportunity_rows",
                [],
            )
            or []
        )

        updated_rows = []

        for original_row in opportunity_rows:
            if not isinstance(
                original_row,
                dict,
            ):
                continue

            row = dict(
                original_row
            )

            symbol = str(
                row.get(
                    "symbol",
                    "",
                )
            ).strip().upper()

            velocity = (
                velocity_by_symbol.get(
                    symbol
                )
            )

            if velocity is not None:
                row[
                    "opportunity_velocity"
                ] = velocity

                row[
                    "opportunity_delta_1m"
                ] = velocity[
                    "delta_1m"
                ]

                row[
                    "opportunity_delta_5m"
                ] = velocity[
                    "delta_5m"
                ]

                row[
                    "rvol_delta_1m"
                ] = velocity[
                    "rvol_delta_1m"
                ]

                row[
                    "rvol_delta_5m"
                ] = velocity[
                    "rvol_delta_5m"
                ]

            updated_rows.append(
                row
            )

        if opportunity_rows:
            summary[
                "opportunity_rows"
            ] = updated_rows

        summary[
            "rising_fast"
        ] = rising_rows[:20]

        summary[
            "rising_fast_count"
        ] = len(
            rising_rows
        )

        summary[
            "new_entrants"
        ] = list(
            reversed(
                self.entrant_events
            )
        )[:20]

        summary[
            "new_entrant_count"
        ] = len(
            self.entrant_events
        )

        summary[
            "velocity_market_timestamp"
        ] = (
            datetime.fromtimestamp(
                source_timestamp,
                tz=timezone.utc,
            ).isoformat()
        )

        new_snapshot[
            "experimental_edge_summary"
        ] = summary

        if is_new_batch:
            self.last_batch_timestamp = (
                source_timestamp
            )

        return new_snapshot


_TRACKER = OpportunityVelocityTracker()


def attach_opportunity_velocity(
    *,
    snapshot: Dict[str, Any],
    ticks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    try:
        return _TRACKER.update(
            snapshot=snapshot,
            ticks=ticks,
        )

    except Exception as exc:
        result = dict(
            snapshot
        )

        result[
            "opportunity_velocity_error"
        ] = str(exc)

        return result
