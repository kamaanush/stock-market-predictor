from __future__ import annotations

from typing import Any


def _safe_float(
    value: Any,
) -> float:
    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return 0.0


class LeadershipRotationTracker:
    """
    Tracks changes in the strongest
    bullish and bearish relative-strength
    groups from scan to scan.

    Positive rank_change = climbing.
    Negative rank_change = falling.
    """

    def __init__(
        self,
        top_n: int = 15,
    ) -> None:

        self.top_n = max(
            5,
            int(top_n),
        )

        self._previous_bullish: dict[
            str,
            int,
        ] = {}

        self._previous_bearish: dict[
            str,
            int,
        ] = {}

        self._initialized = False

    def _rank_group(
        self,
        results: list[
            dict[str, Any]
        ],
        *,
        direction: str,
    ) -> list[
        dict[str, Any]
    ]:

        candidates = []

        for item in results:

            if (
                item.get("status")
                != "READY"
            ):
                continue

            symbol = str(
                item.get(
                    "symbol",
                    "",
                )
            ).strip().upper()

            if not symbol:
                continue

            rs = item.get(
                "relative_strength",
                {},
            )

            if not rs.get(
                "available",
                False,
            ):
                continue

            rs_direction = str(
                rs.get(
                    "direction",
                    "NEUTRAL",
                )
            ).upper()

            if (
                rs_direction
                != direction
            ):
                continue

            strength = _safe_float(
                rs.get(
                    "strength"
                )
            )

            candidates.append(
                {
                    "symbol":
                        symbol,

                    "strength":
                        strength,

                    "rs_5m_pct":
                        _safe_float(
                            rs.get(
                                "rs_5m_pct"
                            )
                        ),

                    "fast_score":
                        _safe_float(
                            item.get(
                                "fast_score"
                            )
                        ),
                }
            )

        if direction == "BULLISH":

            candidates.sort(
                key=lambda item:
                    (
                        item[
                            "strength"
                        ],
                        item[
                            "fast_score"
                        ],
                    ),
                reverse=True,
            )

        else:

            candidates.sort(
                key=lambda item:
                    (
                        item[
                            "strength"
                        ],
                        -item[
                            "fast_score"
                        ],
                    ),
            )

        return candidates[
            :self.top_n
        ]

    def _compare(
        self,
        current: list[
            dict[str, Any]
        ],
        previous: dict[
            str,
            int,
        ],
    ) -> dict[str, Any]:

        current_ranks = {
            item["symbol"]:
                index + 1
            for index, item
            in enumerate(current)
        }

        current_symbols = set(
            current_ranks
        )

        previous_symbols = set(
            previous
        )

        entrants = (
            current_symbols
            - previous_symbols
        )

        exits = (
            previous_symbols
            - current_symbols
        )

        leaders = []

        for item in current:

            symbol = item[
                "symbol"
            ]

            rank = current_ranks[
                symbol
            ]

            previous_rank = (
                previous.get(
                    symbol
                )
            )

            if previous_rank is None:

                state = "NEW_ENTRY"

                rank_change = None

            else:

                rank_change = (
                    previous_rank
                    - rank
                )

                if rank_change >= 3:
                    state = (
                        "RISING_FAST"
                    )

                elif rank_change > 0:
                    state = "RISING"

                elif rank_change <= -3:
                    state = (
                        "FALLING_FAST"
                    )

                elif rank_change < 0:
                    state = "FALLING"

                else:
                    state = "STABLE"

            leaders.append(
                {
                    **item,

                    "rank":
                        rank,

                    "previous_rank":
                        previous_rank,

                    "rank_change":
                        rank_change,

                    "rotation_state":
                        state,
                }
            )

        exit_rows = [
            {
                "symbol":
                    symbol,

                "previous_rank":
                    previous[
                        symbol
                    ],
            }
            for symbol
            in sorted(
                exits,
                key=lambda value:
                    previous[value],
            )
        ]

        return {
            "leaders":
                leaders,

            "new_entries":
                len(entrants),

            "exits":
                len(exits),

            "exit_symbols":
                exit_rows,

            "current_ranks":
                current_ranks,
        }

    def update(
        self,
        results: list[
            dict[str, Any]
        ],
    ) -> dict[str, Any]:

        bullish = self._rank_group(
            results,
            direction="BULLISH",
        )

        bearish = self._rank_group(
            results,
            direction="BEARISH",
        )

        bullish_rotation = (
            self._compare(
                bullish,
                self._previous_bullish,
            )
        )

        bearish_rotation = (
            self._compare(
                bearish,
                self._previous_bearish,
            )
        )

        was_initialized = (
            self._initialized
        )

        if not was_initialized:

            # First scan establishes baseline.
            for item in (
                bullish_rotation[
                    "leaders"
                ]
            ):
                item[
                    "rotation_state"
                ] = "BASELINE"

                item[
                    "rank_change"
                ] = None

            for item in (
                bearish_rotation[
                    "leaders"
                ]
            ):
                item[
                    "rotation_state"
                ] = "BASELINE"

                item[
                    "rank_change"
                ] = None

            bullish_rotation[
                "new_entries"
            ] = 0

            bearish_rotation[
                "new_entries"
            ] = 0

            bullish_rotation[
                "exits"
            ] = 0

            bearish_rotation[
                "exits"
            ] = 0

            bullish_rotation[
                "exit_symbols"
            ] = []

            bearish_rotation[
                "exit_symbols"
            ] = []

        total_changes = (
            bullish_rotation[
                "new_entries"
            ]
            + bullish_rotation[
                "exits"
            ]
            + bearish_rotation[
                "new_entries"
            ]
            + bearish_rotation[
                "exits"
            ]
        )

        maximum_changes = max(
            self.top_n * 4,
            1,
        )

        rotation_intensity = min(
            (
                total_changes
                / maximum_changes
            )
            * 100.0,
            100.0,
        )

        if not was_initialized:
            regime = "BASELINE"

        elif rotation_intensity >= 40:
            regime = (
                "HIGH_ROTATION"
            )

        elif rotation_intensity >= 15:
            regime = (
                "MODERATE_ROTATION"
            )

        else:
            regime = (
                "STABLE_LEADERSHIP"
            )

        self._previous_bullish = (
            bullish_rotation[
                "current_ranks"
            ]
        )

        self._previous_bearish = (
            bearish_rotation[
                "current_ranks"
            ]
        )

        self._initialized = True

        bullish_rotation.pop(
            "current_ranks",
            None,
        )

        bearish_rotation.pop(
            "current_ranks",
            None,
        )

        return {
            "available": True,

            "initialized":
                was_initialized,

            "top_n":
                self.top_n,

            "regime":
                regime,

            "rotation_intensity": round(
                rotation_intensity,
                2,
            ),

            "bullish":
                bullish_rotation,

            "bearish":
                bearish_rotation,
        }
