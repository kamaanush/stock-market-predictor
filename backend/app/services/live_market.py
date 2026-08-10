
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from SmartApi.smartWebSocketV2 import (
    SmartWebSocketV2,
)


class LiveMarketTracker:
    """
    Angel One SmartWebSocketV2 live NSE tracker.

    V1.8 responsibilities:
    - subscribe to NSE watchlist tokens
    - receive live LTP ticks
    - cache latest prices
    - expose snapshots to FastAPI
    """

    def __init__(
        self,
        *,
        auth_token: str,
        api_key: str,
        client_code: str,
        feed_token: str,
    ) -> None:

        self.auth_token = auth_token
        self.api_key = api_key
        self.client_code = client_code
        self.feed_token = feed_token

        self._socket: Optional[
            SmartWebSocketV2
        ] = None

        self._thread: Optional[
            threading.Thread
        ] = None

        self._tokens: list[str] = []

        self._token_symbol: dict[
            str,
            str,
        ] = {}

        self._latest: dict[
            str,
            dict[str, Any],
        ] = {}

        self._lock = threading.Lock()

        self._running = False

        self._listeners: list[
            Callable[
                [dict[str, Any]],
                None,
            ]
        ] = []

    @property
    def running(
        self,
    ) -> bool:
        return self._running

    def configure(
        self,
        instruments: list[
            tuple[str, str]
        ],
    ) -> None:
        """
        instruments:
            [
                ("SBIN", "3045"),
                ("ICICIBANK", "4963"),
            ]
        """

        token_symbol: dict[
            str,
            str,
        ] = {}

        for symbol, token in instruments:

            normalized_symbol = (
                str(symbol)
                .strip()
                .upper()
            )

            normalized_token = (
                str(token)
                .strip()
            )

            if (
                not normalized_symbol
                or not normalized_token
            ):
                continue

            token_symbol[
                normalized_token
            ] = normalized_symbol

        self._token_symbol = (
            token_symbol
        )

        self._tokens = list(
            token_symbol.keys()
        )

    def add_listener(
        self,
        callback: Callable[
            [dict[str, Any]],
            None,
        ],
    ) -> None:

        if callback not in self._listeners:
            self._listeners.append(
                callback
            )

    def remove_listener(
        self,
        callback: Callable[
            [dict[str, Any]],
            None,
        ],
    ) -> None:

        if callback in self._listeners:
            self._listeners.remove(
                callback
            )

    def _notify(
        self,
        tick: dict[str, Any],
    ) -> None:

        for callback in list(
            self._listeners
        ):

            try:
                callback(tick)

            except Exception:
                continue

    def _handle_data(
        self,
        wsapp: Any,
        message: dict[str, Any],
    ) -> None:

        token = str(
            message.get(
                "token",
                "",
            )
        )

        if not token:
            return

        symbol = self._token_symbol.get(
            token,
            token,
        )

        raw_ltp = message.get(
            "last_traded_price"
        )

        if raw_ltp is None:
            return

        # Angel One WebSocket prices are
        # generally returned in paise.
        try:
            ltp = float(raw_ltp) / 100.0
        except (
            TypeError,
            ValueError,
        ):
            return

        exchange_timestamp = (
            message.get(
                "exchange_timestamp"
            )
        )

        cumulative_volume = (
            message.get(
                "volume_trade_for_the_day"
            )
        )

        tick = {
            "symbol": symbol,
            "token": token,
            "ltp": ltp,
            "exchange_timestamp": (
                exchange_timestamp
            ),
            "volume": (
                float(cumulative_volume)
                if cumulative_volume
                is not None
                else None
            ),
            "received_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        }

        with self._lock:

            self._latest[
                symbol
            ] = tick

        self._notify(tick)

    def _handle_open(
        self,
        wsapp: Any,
    ) -> None:

        if not self._tokens:
            return

        assert self._socket is not None

        token_list = [
            {
                "exchangeType": 1,
                "tokens": self._tokens,
            }
        ]

        self._socket.subscribe(
              "livev18",
                2,
                token_list,
            )

    def _handle_error(
        self,
        wsapp: Any,
        error: Any,
    ) -> None:

        print(
            "SmartAPI WebSocket error:",
            error,
        )

    def _handle_close(
        self,
        wsapp: Any,
    ) -> None:

        self._running = False

        print(
            "SmartAPI WebSocket closed"
        )

    def _run(
        self,
    ) -> None:

        self._socket = (
            SmartWebSocketV2(
                self.auth_token,
                self.api_key,
                self.client_code,
                self.feed_token,
            )
        )

        self._socket.on_open = (
            self._handle_open
        )

        self._socket.on_data = (
            self._handle_data
        )

        self._socket.on_error = (
            self._handle_error
        )

        self._socket.on_close = (
            self._handle_close
        )

        self._running = True

        try:
            self._socket.connect()

        finally:
            self._running = False

    def start(
        self,
    ) -> None:

        if self._running:
            return

        if not self._tokens:
            raise RuntimeError(
                "No watchlist tokens "
                "configured for live tracking"
            )

        self._thread = (
            threading.Thread(
                target=self._run,
                name=(
                    "smartapi-live-market"
                ),
                daemon=True,
            )
        )

        self._thread.start()

    def stop(
        self,
    ) -> None:

        self._running = False

        if self._socket is not None:

            try:
                self._socket.close_connection()

            except Exception:
                pass

    def get_latest(
        self,
        symbol: str,
    ) -> Optional[
        dict[str, Any]
    ]:

        normalized = (
            symbol
            .strip()
            .upper()
        )

        with self._lock:

            value = self._latest.get(
                normalized
            )

            if value is None:
                return None

            return dict(value)

    def snapshot(
        self,
    ) -> list[
        dict[str, Any]
    ]:

        with self._lock:

            values = [
                dict(value)
                for value
                in self._latest.values()
            ]

        return sorted(
            values,
            key=lambda item: (
                item["symbol"]
            ),
        )
