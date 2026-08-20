from app.main import app


def test_important_routes_exist():

    paths = {
        route.path
        for route
        in app.routes
    }

    required = {
        "/api/watchlist",
        "/api/instruments",
        "/api/v2/scanner/{symbol}",
        "/api/ws/market",
    }

    missing = (
        required - paths
    )

    assert not missing, (
        f"Missing routes: {missing}"
    )
