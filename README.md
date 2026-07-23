# NSE Stock Tracker

A private, desktop-first single-user NSE stock tracking dashboard.

For detailed architecture, stack decisions, runtime data flow, API contracts, and extension guidelines, see [ARCHITECTURE.md](file:///c:/Users/SANDEEP/Desktop/stock%20market%20predictor/ARCHITECTURE.md).

---

## Prerequisites

- **Python**: 3.10 or higher
- **Node.js**: 18 or higher (with npm)
- **Docker & Docker Compose** (Optional, if using containerized setup)

---

## Configuration & Environment Setup

1. Copy `.env.example` to create a `.env` file in the project root:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` to configure your credentials:

   - **`APP_PASSWORD`**: Password to sign into the dashboard.
   - **`SESSION_SECRET`**: A random 32+ character string for authentication sessions.
   - **SmartAPI Credentials** *(Optional)*: Set `SMARTAPI_API_KEY`, `SMARTAPI_CLIENT_CODE`, `SMARTAPI_PIN`, and `SMARTAPI_TOTP_SECRET` for live market data. If left blank, the app runs in **Demo Mode**.
   - **Telegram** *(Optional)*: Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to receive price alerts via Telegram.

---

## Setup & Running

You can run the project either locally (recommended for development) or using Docker Compose.

### Option 1: Local Setup (Recommended)

#### 1. Backend Setup

From the project root:

```powershell
# Create virtual environment
python -m venv .venv

# Install dependencies
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

# Start backend server (runs at http://127.0.0.1:8000)
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

> *On macOS / Linux, replace `.\.venv\Scripts\python.exe` with `./.venv/bin/python`.*

#### 2. Frontend Setup

In a second terminal window:

```powershell
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Next.js development server (runs at http://127.0.0.1:3000)
npm run dev
```

> *Note for Windows PowerShell:* If script execution policy blocks `npm.ps1`, use `cmd /c npm install` and `cmd /c npm run dev`.

#### 3. Access the Dashboard

Open your browser and go to `http://127.0.0.1:3000`. Log in using the `APP_PASSWORD` set in your `.env` file.

---

### Option 2: Docker Setup

If you prefer running everything in containers using PostgreSQL:

```powershell
# Build and start all services (Backend, Frontend, PostgreSQL)
docker compose up --build
```

Access the dashboard at `http://127.0.0.1:3000`.

To stop the services while preserving data:

```powershell
docker compose down
```

---

## Architecture & More Context

For complete details on:
- Product boundaries and design
- Tech stack choices
- Data flow diagrams
- API contracts & endpoints
- Alert evaluation and market modes
- Safe extension pathways

Please refer to [ARCHITECTURE.md](file:///c:/Users/SANDEEP/Desktop/stock%20market%20predictor/ARCHITECTURE.md).
