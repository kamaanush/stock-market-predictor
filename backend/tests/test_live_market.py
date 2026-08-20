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
    assert latest["symbol"] == "SBIN"
    assert latest["token"] == "3045"
    assert latest["ltp"] == 812.50

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
