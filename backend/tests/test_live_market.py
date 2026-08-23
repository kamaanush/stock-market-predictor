from app.services.live_market import LiveMarketTracker


def make_tracker():
    return LiveMarketTracker(
        auth_token="test",
        api_key="test",
        client_code="test",
        feed_token="test",
    )


def test_configure_watchlist():
    tracker = make_tracker()

    tracker.configure([
        ("RELIANCE", "2885"),
        ("SBIN", "3045"),
    ])

    assert "2885" in tracker._tokens
    assert "3045" in tracker._tokens

    assert (
        tracker._token_symbol["2885"]
        == "RELIANCE"
    )

    assert (
        tracker._token_symbol["3045"]
        == "SBIN"
    )


def test_add_instrument_to_live_tracker():
    tracker = make_tracker()

    tracker.configure([
        ("RELIANCE", "2885"),
    ])

    tracker.add_instrument(
        symbol="SBIN",
        token="3045",
        last_price=812.50,
    )

    latest = tracker.get_latest(
        "SBIN"
    )

    assert latest is not None

    assert (
        latest["symbol"]
        == "SBIN"
    )

    assert (
        latest["token"]
        == "3045"
    )

    assert (
        latest["ltp"]
        == 812.50
    )

    assert "3045" in tracker._tokens


def test_add_instrument_normalizes_symbol():
    tracker = make_tracker()

    tracker.add_instrument(
        symbol="  icicibank  ",
        token="4963",
        last_price=1420.25,
    )

    latest = tracker.get_latest(
        "ICICIBANK"
    )

    assert latest is not None

    assert (
        latest["symbol"]
        == "ICICIBANK"
    )


def test_snapshot_is_sorted():
    tracker = make_tracker()

    tracker.add_instrument(
        "TCS",
        "11536",
        3200.00,
    )

    tracker.add_instrument(
        "SBIN",
        "3045",
        812.00,
    )

    snapshot = tracker.snapshot()

    symbols = [
        item["symbol"]
        for item in snapshot
    ]

    assert symbols == sorted(
        symbols
    )


def test_remove_instrument_from_live_tracker():
    tracker = make_tracker()

    tracker.add_instrument(
        symbol="ICICIBANK",
        token="4963",
        last_price=1435.25,
    )

    # Confirm it exists.
    assert "4963" in tracker._tokens

    assert (
        tracker._token_symbol["4963"]
        == "ICICIBANK"
    )

    assert (
        tracker.get_latest(
            "ICICIBANK"
        )
        is not None
    )

    # Remove using lowercase + spaces
    # to verify normalization.
    tracker.remove_instrument(
        "  icicibank  "
    )

    # Token removed.
    assert (
        "4963"
        not in tracker._tokens
    )

    # Mapping removed.
    assert (
        "4963"
        not in tracker._token_symbol
    )

    # Cached live value removed.
    assert (
        tracker.get_latest(
            "ICICIBANK"
        )
        is None
    )

    # Snapshot no longer contains ICICI.
    symbols = [
        item["symbol"]
        for item in tracker.snapshot()
    ]

    assert (
        "ICICIBANK"
        not in symbols
    )

def test_removed_instrument_ignores_late_tick():
    tracker = make_tracker()

    tracker.add_instrument(
        symbol="ICICIBANK",
        token="4963",
        last_price=1435.25,
    )

    tracker.remove_instrument(
        "ICICIBANK"
    )

    tracker._handle_data(
        None,
        {
            "token": "4963",
            "last_traded_price": 143525,
            "exchange_timestamp": 1234567890,
            "volume_trade_for_the_day": 2500000,
        },
    )

    assert (
        tracker.get_latest(
            "ICICIBANK"
        )
        is None
    )

    assert (
        "ICICIBANK"
        not in [
            item["symbol"]
            for item in tracker.snapshot()
        ]
    )