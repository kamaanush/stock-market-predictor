# NSE Stock Tracker — architecture and project context

This document is the hand-off context for a developer or future AI agent. It describes the application as implemented, its deliberate boundaries, and the safe way to extend it.

## Product scope (v1)

The application is a private, desktop-first, single-user NSE dashboard for a MacBook. It tracks NSE cash equities and NSE indices, showing intraday chart data, a personal watchlist, current holdings, average cost, unrealized P/L, and one-shot price alerts.

**Explicitly out of scope in v1:** price prediction or trading recommendations, order placement, broker portfolio sync, multi-user access, tax reports, realized P/L, individual sell/lot matching, and persistent historical price storage.

The black/green user interface uses demo market data until valid Angel One SmartAPI credentials are configured. Demo prices are deliberately simulated and must never be treated as real market prices.

## Stack and why it was chosen

| Layer | Implementation | Reason |
| --- | --- | --- |
| Frontend | Next.js + TypeScript + Tailwind | A responsive local web dashboard with browser notifications and charts. |
| Chart | TradingView Lightweight Charts | Candlesticks, EMA 20, and volume without a proprietary trading terminal. |
| Backend | Python + FastAPI | Simple REST API, CSV validation, and a natural future home for market analysis. |
| Local database | SQLite in direct-development mode | Zero setup on one laptop. `stock_tracker.db` is created automatically. |
| Container database | PostgreSQL in Docker Compose | A production-like, durable option when Docker is preferred. |
| Live-data provider | Angel One SmartAPI (optional) | Read-only quote and candle access; credentials remain backend-only. |

Python is a better fit than Node for this project because future indicators/analytics and Angel One integrations are comfortable in Python. The frontend remains TypeScript because it is a browser interface. There is no compatibility problem in this split: they communicate only over local HTTP.

## Runtime and data flow

```text
Browser at http://127.0.0.1:3000
       | authenticated REST calls + 5–10 second polling
       v
FastAPI at http://127.0.0.1:8000/api
       |-- password session cookie
       |-- watchlist / holdings / CSV import / alert APIs
       |-- alert evaluator (every 10 seconds)
       |-- demo market provider OR Angel One SmartAPI
       v
SQLite file (direct mode) OR PostgreSQL (Docker Compose)
```

The frontend never sees the owner password after login, Angel One credentials, a TOTP secret, or a Telegram bot token. The backend binds to localhost in direct mode and the Docker Compose port mappings are loopback-only.

## Key source files

| File | Responsibility |
| --- | --- |
| `backend/app/main.py` | API routes, password session gate, CSV import, demo instrument seed, and background alert evaluation. |
| `backend/app/market.py` | Demo quote/candle generator, optional SmartAPI client, and in-process 15-second candle aggregation. |
| `backend/app/models.py` | SQLAlchemy database tables. `PortfolioTransaction` is deliberately retained for future lot-based accounting. |
| `backend/app/notifications.py` | Telegram send helper; it does nothing until bot token and chat ID are configured. |
| `frontend/app/page.tsx` | Login screen and all watchlist, portfolio, chart, import, and alert views. |
| `frontend/components/StockChart.tsx` | Candlestick + volume + EMA 20 chart. |
| `.env.example` | Safe configuration template—copy it to an untracked `.env`; never put secrets in source. |

## API contract

- `GET /api/health`
- `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- `GET /api/instruments/search?q=`, `POST /api/instruments/refresh`
- `GET/POST/DELETE /api/watchlist`
- `GET /api/stocks/{symbol}/quote`
- `GET /api/stocks/{symbol}/candles?interval=15s|1m|5m|15m`
- `GET/PUT /api/portfolio/holdings`, `POST /api/portfolio/import`
- `GET/POST/PATCH/DELETE /api/alerts`, `GET /api/alerts/events`

The holdings CSV must contain `symbol,name,quantity,average_price`; `token` is optional. Updating the same symbol replaces the displayed current-holding snapshot. The database has a separate `portfolio_transactions` table reserved for a later lots/realized-P&L feature.

## Alerts

An active alert is evaluated approximately every 10 seconds while the backend runs. It triggers once, records an immutable `alert_events` record, then becomes inactive to avoid repeated messages. The browser polls events, plays a short sound, and shows an operating-system notification only after the user clicks **Enable browser alerts** and grants permission.

Telegram delivery requires both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`; an account/chat ID alone is not sufficient. If Telegram fails, the browser event is still retained. The app does not send alerts when it is stopped.

## Market data modes

### Default demo mode

With blank SmartAPI settings, the tracker starts safely in demo mode, including a small first-run search catalogue: RELIANCE, TCS, INFY, HDFCBANK, and NIFTY 50. Candle data and prices are simulated so all screens can be tested without financial credentials.

### Optional SmartAPI mode

Set all four values below in `.env` to use SmartAPI:

```ini
SMARTAPI_API_KEY=
SMARTAPI_CLIENT_CODE=
SMARTAPI_PIN=
SMARTAPI_TOTP_SECRET=
```

The backend performs a read-only session login and requests quotes/candles on demand. It falls back to demo mode if initial live login fails, rather than making the private dashboard unavailable. SmartAPI requirements and subscription limits change, so validate live authentication and NSE token access with the current official provider documentation before relying on it during market hours. An inbound static IP is not normally needed for this localhost, read-only application; do not expose it to the public internet.

The 15-second chart is aggregated in the running process from requested quotes. It starts after the app starts and is not historical or persisted. One-, five-, and fifteen-minute candles use the provider when SmartAPI is configured, or the demo generator otherwise.

## Run locally (recommended first)

1. Copy `.env.example` to `.env` and choose a private `APP_PASSWORD` and `SESSION_SECRET`. Keep all SmartAPI and Telegram entries blank to use demo mode.
2. Create a virtual environment and install backend requirements:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
   ```

3. In one terminal, start the backend from the project root:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
   ```

4. In a second terminal, install and start the frontend:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

5. Open `http://127.0.0.1:3000` and sign in with the password you placed in `.env`.

On Windows systems whose PowerShell policy blocks `npm.ps1`, use `cmd /c npm install` and `cmd /c npm run dev`, or configure the policy according to local IT rules.

## Docker option

After creating `.env`, Docker can run the full three-service stack:

```powershell
docker compose up --build
```

Use `http://127.0.0.1:3000`. Docker uses PostgreSQL and overrides `DATABASE_URL` internally. Stop it with `docker compose down`; this preserves the named PostgreSQL data volume. Add `--volumes` only if you intentionally want to delete all Docker-held tracker data.

## Security and privacy rules

- Never hardcode, commit, paste into a ticket, or put in a CSV: passwords, session secrets, API keys, client codes, PINs, TOTP secrets, Telegram tokens, or chat IDs.
- `.env` is ignored by Git. Rotate any credential that has been publicly shared.
- This password gate is a light local privacy measure, not enterprise authentication. Keep the service on `127.0.0.1`.
- The app is read-only and must not be extended to place orders without a separate security review and explicit product decision.

## Safe extension path (v2+)

1. **Realized P/L:** write importer/manual entries to `portfolio_transactions`, choose FIFO/LIFO explicitly, then implement sales, corporate actions, and tax reporting.
2. **Predictions:** first decide the data source, prediction target and horizon, evaluation metric, and risk communication. Store model version, training window, inputs, and evaluation results. Do not label an indicator as a prediction.
3. **Live streaming:** replace REST quote polling with a managed SmartAPI stream, explicit reconnect/backoff, subscription caps, and market-session handling.
4. **Multiple devices/users:** move authentication, secrets, database backups, HTTPS, and authorization to a deployment architecture designed for that purpose.
