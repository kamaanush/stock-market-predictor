"use client";

import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import StockChart, { Candle } from "../components/StockChart";

const API =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

type View = "watchlist" | "portfolio" | "alerts";

type Instrument = {
  symbol: string;
  name: string;
  token: string;
  kind: string;
};

type WatchItem = Instrument & {
  last_price: number | null;
  change_percent: number | null;
};

type Holding = {
  symbol: string;
  name: string;
  token: string;
  quantity: number;
  average_price: number;
  current_price: number | null;
  market_value: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_percent: number | null;
};

type Alert = {
  id: number;
  symbol: string;
  name: string;
  condition: "ABOVE" | "BELOW";
  target_price: number;
  delivery: "BROWSER" | "TELEGRAM" | "BOTH";
  active: boolean;
};

type AlertEvent = {
  id: number;
  alert_id: number;
  symbol: string;
  message: string;
  delivery: "BROWSER" | "TELEGRAM" | "BOTH";
  created_at: string;
};

type TimeframeRisk = {
  level: string;
  risk_score: number;
  reward_risk_ratio: number | null;
  stop_distance_percent: number | null;
  target_distance_percent: number | null;
  warnings: string[];
  positives: string[];
  summary: string;
};

type TimeframeDecision = {
  signal: string;
  confidence: number;
  grade: string;
  action: string;
  summary: string;
};

type TimeframeConfidence = {
  signal: string;
  confidence: number;
  grade: string;
  probability: string;
  positive_score: number;
  penalty_score: number;
  summary: string;
};

type TimeframeAnalysis = {
  decision: TimeframeDecision;
  market_structure: Record<string, unknown>;
  trend_strength: Record<string, unknown>;
  momentum: Record<string, unknown>;
  participation: Record<string, unknown>;
  buyer_seller_pressure: Record<string, unknown>;
  candle_flow: Record<string, unknown>;
  location: Record<string, unknown>;
  risk: TimeframeRisk;
  breakout_readiness: Record<string, unknown>;
  confidence: TimeframeConfidence;
};

type MarketOpportunity = {
  symbol: string;
  name: string | null;
  signal: "BUY" | "SELL" | "WAIT";
  confidence: number;
  grade: string;
  action: string;
  alignment: string;
  strongest_timeframe: string;
  timeframes: Record<string, TimeframeAnalysis>;
};

type MarketScanResponse = {
  scanned: number;
  successful: number;
  failed: number;
  opportunities: MarketOpportunity[];
  failures: {
    symbol: string;
    error: string;
  }[];
};

async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const formData =
    typeof FormData !== "undefined" && options.body instanceof FormData;

  const response = await fetch(`${API}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      ...(formData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Request failed");
  }

  return response.status === 204
    ? (undefined as T)
    : response.json();
}

const money = (value: number | null | undefined) =>
  value == null
    ? "—"
    : new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 2,
      }).format(value);

const number = (value: number | null | undefined) =>
  value == null
    ? "—"
    : new Intl.NumberFormat("en-IN", {
        maximumFractionDigits: 2,
      }).format(value);

export default function Home() {
  const [authenticated, setAuthenticated] =
    useState<boolean | null>(null);
  const [password, setPassword] = useState("");
  const [view, setView] = useState<View>("watchlist");

  const [watchlist, setWatchlist] = useState<WatchItem[]>([]);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  const [selected, setSelected] = useState<WatchItem | null>(null);
  const [interval, setInterval] = useState("5m");
  const [candles, setCandles] = useState<Candle[]>([]);

  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<Instrument[]>([]);

  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [lastEventId, setLastEventId] = useState(0);

  const [marketScan, setMarketScan] =
    useState<MarketScanResponse | null>(null);
  const [scannerBusy, setScannerBusy] = useState(false);
  const [autoScannerEnabled, setAutoScannerEnabled] =
    useState(false);
  const [lastScannerRun, setLastScannerRun] =
    useState<string | null>(null);

  const [selectedOpportunity, setSelectedOpportunity] =
    useState<MarketOpportunity | null>(null);

  const scannerRunningRef = useRef(false);

  const load = useCallback(async () => {
    const [watch, portfolio, alertList] = await Promise.all([
      api<WatchItem[]>("/watchlist"),
      api<Holding[]>("/portfolio/holdings"),
      api<Alert[]>("/alerts"),
    ]);

    setWatchlist(watch);
    setHoldings(portfolio);
    setAlerts(alertList);

    setSelected((current) =>
      current
        ? watch.find((item) => item.symbol === current.symbol) ||
          watch[0] ||
          null
        : watch[0] || null,
    );
  }, []);

  useEffect(() => {
    api<{ authenticated: boolean }>("/auth/me")
      .then(({ authenticated: loggedIn }) => {
        setAuthenticated(loggedIn);

        if (loggedIn) {
          void load().catch((error: Error) =>
            setNotice(error.message),
          );
        }
      })
      .catch(() => setAuthenticated(false));
  }, [load]);

  useEffect(() => {
    if (!selected) {
      setCandles([]);
      return;
    }

    api<Candle[]>(
      `/stocks/${encodeURIComponent(
        selected.symbol,
      )}/candles?interval=${interval}`,
    )
      .then(setCandles)
      .catch((error: Error) => setNotice(error.message));
  }, [selected, interval]);

  useEffect(() => {
    if (!authenticated) {
      return;
    }

    const ticker = window.setInterval(() => {
      void load().catch(() => undefined);
    }, 10_000);

    return () => window.clearInterval(ticker);
  }, [authenticated, load]);

  useEffect(() => {
    if (!authenticated) {
      return;
    }

    const poll = async () => {
      try {
        const events = await api<AlertEvent[]>(
          `/alerts/events?after_id=${lastEventId}`,
        );

        if (!events.length) {
          return;
        }

        setLastEventId(events[events.length - 1].id);

        for (const event of events) {
          if (
            event.delivery === "BROWSER" ||
            event.delivery === "BOTH"
          ) {
            playAlertSound();

            if (
              "Notification" in window &&
              Notification.permission === "granted"
            ) {
              new Notification("NSE Stock Tracker", {
                body: event.message,
              });
            }
          }

          setNotice(event.message);
        }

        await load();
      } catch {
        // Temporary background errors should not interrupt the app.
      }
    };

    void poll();

    const timer = window.setInterval(() => {
      void poll();
    }, 5_000);

    return () => window.clearInterval(timer);
  }, [authenticated, lastEventId, load]);

  const runWatchlistScanner = useCallback(async () => {
    if (
      scannerRunningRef.current ||
      watchlist.length === 0
    ) {
      return;
    }

    scannerRunningRef.current = true;
    setScannerBusy(true);
    setNotice("");

    try {
      const result = await api<MarketScanResponse>(
        "/v2/market-scanner",
      );

      setMarketScan(result);

      setSelectedOpportunity((current) => {
        if (result.opportunities.length === 0) {
          return null;
        }

        if (current) {
          return (
            result.opportunities.find(
              (item) => item.symbol === current.symbol,
            ) || result.opportunities[0]
          );
        }

        return result.opportunities[0];
      });

      setLastScannerRun(
        new Date().toLocaleTimeString("en-IN"),
      );

      if (result.successful === 0) {
        setNotice(
          result.failed > 0
            ? `Scan completed with ${result.failed} failure(s).`
            : "No scanner results found.",
        );
      } else {
        setNotice(
          `${result.successful} of ${result.scanned} stocks scanned successfully.`,
        );
      }
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not run V2 market scanner",
      );
    } finally {
      scannerRunningRef.current = false;
      setScannerBusy(false);
    }
  }, [watchlist.length]);

  useEffect(() => {
    if (
      !authenticated ||
      !autoScannerEnabled ||
      watchlist.length === 0
    ) {
      return;
    }

    void runWatchlistScanner();

    const timer = window.setInterval(() => {
      void runWatchlistScanner();
    }, 60_000);

    return () => window.clearInterval(timer);
  }, [
    authenticated,
    autoScannerEnabled,
    watchlist.length,
    runWatchlistScanner,
  ]);

  const totalPnl = useMemo(
    () =>
      holdings.reduce(
        (sum, item) => sum + (item.unrealized_pnl || 0),
        0,
      ),
    [holdings],
  );

  const totalValue = useMemo(
    () =>
      holdings.reduce(
        (sum, item) => sum + (item.market_value || 0),
        0,
      ),
    [holdings],
  );

  async function submitLogin(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setNotice("");

    try {
      await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ password }),
      });

      setAuthenticated(true);
      setPassword("");
      await load();
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : "Login failed",
      );
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    try {
      await api("/auth/logout", {
        method: "POST",
      });
    } finally {
      setAuthenticated(false);
      setWatchlist([]);
      setHoldings([]);
      setAlerts([]);
      setMarketScan(null);
      setSelectedOpportunity(null);
      setSelected(null);
      setCandles([]);
      setAutoScannerEnabled(false);
      setLastScannerRun(null);
      setNotice("");
    }
  }

  async function refreshInstruments() {
    setBusy(true);
    setNotice("");

    try {
      const result = await api<{ imported: number }>(
        "/instruments/refresh",
        {
          method: "POST",
        },
      );

      setNotice(
        `${result.imported.toLocaleString()} NSE instruments loaded. Search to add a stock.`,
      );
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not load instruments",
      );
    } finally {
      setBusy(false);
    }
  }

  async function search(value: string) {
    setQuery(value);

    if (!value.trim()) {
      setMatches([]);
      return;
    }

    try {
      setMatches(
        await api<Instrument[]>(
          `/instruments/search?q=${encodeURIComponent(value)}`,
        ),
      );
    } catch {
      setMatches([]);
    }
  }

  async function addToWatchlist(item: Instrument) {
    try {
      await api("/watchlist", {
        method: "POST",
        body: JSON.stringify(item),
      });

      setQuery("");
      setMatches([]);
      await load();
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not add symbol",
      );
    }
  }

  async function removeWatchlist(symbol: string) {
    try {
      await api(
        `/watchlist/${encodeURIComponent(symbol)}`,
        {
          method: "DELETE",
        },
      );

      await load();
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not remove symbol",
      );
    }
  }

  async function saveHolding(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const form = new FormData(event.currentTarget);
    setNotice("");

    try {
      await api("/portfolio/holdings", {
        method: "PUT",
        body: JSON.stringify({
          symbol: form.get("symbol"),
          name: form.get("name"),
          token: form.get("token") || "",
          quantity: Number(form.get("quantity")),
          average_price: Number(form.get("averagePrice")),
        }),
      });

      event.currentTarget.reset();
      await load();
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not save holding",
      );
    }
  }

  async function importHoldings(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const form = new FormData(event.currentTarget);
    const file = form.get("file");

    if (!(file instanceof File) || file.size === 0) {
      setNotice("Choose a CSV file first.");
      return;
    }

    setBusy(true);
    setNotice("");

    try {
      const result = await api<{ imported: number }>(
        "/portfolio/import",
        {
          method: "POST",
          body: form,
        },
      );

      setNotice(
        `${result.imported} holding${
          result.imported === 1 ? "" : "s"
        } imported.`,
      );

      event.currentTarget.reset();
      await load();
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not import CSV",
      );
    } finally {
      setBusy(false);
    }
  }

  async function saveAlert(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const form = new FormData(event.currentTarget);

    try {
      await api("/alerts", {
        method: "POST",
        body: JSON.stringify({
          symbol: form.get("symbol"),
          name: form.get("name") || "",
          condition: form.get("condition"),
          target_price: Number(form.get("targetPrice")),
          delivery: form.get("delivery"),
        }),
      });

      event.currentTarget.reset();
      await load();
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not create alert",
      );
    }
  }

  async function setAlertActive(
    alert: Alert,
    active: boolean,
  ) {
    try {
      await api(`/alerts/${alert.id}?active=${active}`, {
        method: "PATCH",
      });

      await load();
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not update alert",
      );
    }
  }

  async function deleteAlert(alert: Alert) {
    try {
      await api(`/alerts/${alert.id}`, {
        method: "DELETE",
      });

      await load();
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not delete alert",
      );
    }
  }

  if (authenticated === null) {
    return (
      <main className="grid min-h-screen place-items-center grid-bg text-muted">
        Starting tracker…
      </main>
    );
  }

  if (!authenticated) {
    return (
      <main className="grid min-h-screen place-items-center px-6 grid-bg">
        <form
          onSubmit={submitLogin}
          className="w-full max-w-sm border border-line bg-panel/95 p-8 shadow-2xl"
        >
          <p className="mb-2 text-sm tracking-[.25em] text-accent">
            PRIVATE DASHBOARD
          </p>

          <h1 className="mb-6 text-3xl font-semibold">
            NSE Stock Tracker
          </h1>

          <label className="mb-2 block text-sm text-muted">
            Owner password
          </label>

          <input
            value={password}
            onChange={(event) =>
              setPassword(event.target.value)
            }
            type="password"
            required
            autoFocus
            className="mb-4 w-full border border-line bg-ink px-3 py-3 outline-none focus:border-accent"
          />

          <button
            disabled={busy}
            className="w-full bg-accent px-4 py-3 font-bold text-black disabled:opacity-60"
          >
            {busy ? "Signing in…" : "Open dashboard"}
          </button>

          {notice && (
            <p className="mt-4 text-sm text-red-300">
              {notice}
            </p>
          )}
        </form>
      </main>
    );
  }

  return (
    <main className="min-h-screen grid-bg">
      <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-line bg-ink/95 px-6 backdrop-blur">
        <div>
          <span className="mr-3 text-xs tracking-[.22em] text-accent">
            LIVE · NSE
          </span>
          <span className="font-semibold">Stock Tracker</span>
        </div>

        <div className="flex items-center gap-4 text-sm text-muted">
          <button
            onClick={() => {
              if ("Notification" in window) {
                void Notification.requestPermission();
              }
            }}
            className="hover:text-accent"
          >
            Enable browser alerts
          </button>

          <button
            onClick={() => void logout()}
            className="hover:text-red-400"
          >
            Logout
          </button>

          <span>Local, read-only dashboard</span>
        </div>
      </header>

      <div className="flex">
        <aside className="min-h-[calc(100vh-4rem)] w-56 border-r border-line bg-[#080e0a] p-4">
          <nav className="space-y-1">
            {(
              ["watchlist", "portfolio", "alerts"] as View[]
            ).map((item) => (
              <button
                key={item}
                onClick={() => setView(item)}
                className={`w-full px-3 py-3 text-left capitalize ${
                  view === item
                    ? "bg-[#13321c] text-accent"
                    : "text-muted hover:bg-panel hover:text-white"
                }`}
              >
                {item}
              </button>
            ))}
          </nav>

          <div className="mt-8 border-t border-line pt-5">
            <button
              onClick={refreshInstruments}
              disabled={busy}
              className="w-full border border-line px-3 py-2 text-left text-sm text-muted hover:border-accent hover:text-accent"
            >
              Refresh NSE instruments
            </button>

            <p className="mt-3 text-xs leading-5 text-muted">
              Indicators summarize past price action. They are
              not buy or sell recommendations.
            </p>
          </div>
        </aside>

        <section className="min-w-0 flex-1 p-6">
          {notice && (
            <div className="mb-5 border border-accent/30 bg-[#102617] px-4 py-3 text-sm text-[#bdeecb]">
              {notice}
            </div>
          )}

          {view === "watchlist" && (
            <WatchlistPanel
              watchlist={watchlist}
              selected={selected}
              query={query}
              matches={matches}
              interval={interval}
              candles={candles}
              marketScan={marketScan}
              selectedOpportunity={selectedOpportunity}
              scannerBusy={scannerBusy}
              autoScannerEnabled={autoScannerEnabled}
              lastScannerRun={lastScannerRun}
              onRunScanner={runWatchlistScanner}
              onSelectOpportunity={setSelectedOpportunity}
              onToggleAutoScanner={() =>
                setAutoScannerEnabled(
                  (enabled) => !enabled,
                )
              }
              onSearch={search}
              onAdd={addToWatchlist}
              onRemove={removeWatchlist}
              onSelect={setSelected}
              onInterval={setInterval}
            />
          )}

          {view === "portfolio" && (
            <PortfolioPanel
              holdings={holdings}
              totalPnl={totalPnl}
              totalValue={totalValue}
              onSave={saveHolding}
              onImport={importHoldings}
              busy={busy}
            />
          )}

          {view === "alerts" && (
            <AlertsPanel
              alerts={alerts}
              onSave={saveAlert}
              onToggle={setAlertActive}
              onDelete={deleteAlert}
            />
          )}
        </section>
      </div>
    </main>
  );
}

function WatchlistPanel({
  watchlist,
  selected,
  query,
  matches,
  interval,
  candles,
  marketScan,
  selectedOpportunity,
  scannerBusy,
  autoScannerEnabled,
  lastScannerRun,
  onSearch,
  onAdd,
  onRemove,
  onSelect,
  onInterval,
  onRunScanner,
  onSelectOpportunity,
  onToggleAutoScanner,
}: {
  watchlist: WatchItem[];
  selected: WatchItem | null;
  query: string;
  matches: Instrument[];
  interval: string;
  candles: Candle[];
  marketScan: MarketScanResponse | null;
  selectedOpportunity: MarketOpportunity | null;
  scannerBusy: boolean;
  autoScannerEnabled: boolean;
  lastScannerRun: string | null;
  onSearch: (value: string) => void;
  onAdd: (item: Instrument) => void;
  onRemove: (symbol: string) => void;
  onSelect: (item: WatchItem) => void;
  onInterval: (value: string) => void;
  onRunScanner: () => void;
  onSelectOpportunity: (item: MarketOpportunity) => void;
  onToggleAutoScanner: () => void;
}) {
  return (
    <>
      <div className="mb-6 flex items-end justify-between gap-5">
        <div>
          <p className="text-xs tracking-[.18em] text-accent">
            MARKET OVERVIEW
          </p>
          <h1 className="mt-1 text-3xl font-semibold">
            Watchlist
          </h1>
        </div>

        <div className="relative w-80">
          <input
            value={query}
            onChange={(event) =>
              onSearch(event.target.value)
            }
            placeholder="Search NSE symbol or company"
            className="w-full border border-line bg-panel px-3 py-2.5 outline-none focus:border-accent"
          />

          {matches.length > 0 && (
            <div className="absolute z-10 mt-1 w-full border border-line bg-[#0b120d] shadow-xl">
              {matches.map((item) => (
                <button
                  key={`${item.symbol}-${item.token}`}
                  onClick={() => onAdd(item)}
                  className="flex w-full items-center justify-between px-3 py-3 text-left hover:bg-[#13321c]"
                >
                  <span>
                    <b>{item.symbol}</b>
                    <span className="ml-2 text-xs text-muted">
                      {item.name}
                    </span>
                  </span>

                  <span className="text-xs text-accent">
                    ADD
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="mb-6 border border-line bg-panel">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line p-4">
          <div>
            <p className="text-xs tracking-[.18em] text-accent">
              AI SCANNER
            </p>

            <h2 className="mt-1 text-xl font-semibold">
              V2 Multi-Timeframe Opportunities
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="text-right text-xs text-muted">
              <p>
                Auto scan:{" "}
                <span
                  className={
                    autoScannerEnabled
                      ? "text-accent"
                      : "text-yellow-300"
                  }
                >
                  {autoScannerEnabled ? "ON" : "OFF"}
                </span>
              </p>

              <p>
                Last scan:{" "}
                {lastScannerRun || "Not run yet"}
              </p>
            </div>

            <button
              onClick={onToggleAutoScanner}
              disabled={watchlist.length === 0}
              className="border border-line px-4 py-2 font-semibold text-muted hover:border-accent hover:text-accent disabled:opacity-50"
            >
              {autoScannerEnabled
                ? "Stop Auto Scan"
                : "Start Auto Scan"}
            </button>

            <button
              onClick={onRunScanner}
              disabled={
                scannerBusy || watchlist.length === 0
              }
              className="bg-accent px-4 py-2 font-bold text-black disabled:opacity-50"
            >
              {scannerBusy ? "Scanning…" : "Run V2 Scan"}
            </button>
          </div>
        </div>

        {!marketScan || marketScan.opportunities.length === 0 ? (
          <div className="p-5 text-sm text-muted">
            <p>
              Run the V2 market scanner to analyze and rank your watchlist
              across 1m, 5m, and 15m.
            </p>

            {marketScan && marketScan.failures.length > 0 && (
              <div className="mt-3 space-y-1 text-xs text-red-300">
                {marketScan.failures.map((failure) => (
                  <p key={failure.symbol}>
                    {failure.symbol}: {failure.error}
                  </p>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs text-muted">
                  <th className="p-3">Rank</th>
                  <th className="p-3">Symbol</th>
                  <th className="p-3">Signal</th>
                  <th className="p-3">Confidence</th>
                  <th className="p-3">Grade</th>
                  <th className="p-3">Action</th>
                  <th className="p-3">Alignment</th>
                  <th className="p-3">Best TF</th>
                  <th className="p-3">Risk</th>
                </tr>
              </thead>

              <tbody>
                {marketScan.opportunities.map((result, index) => {
                  const strongest =
                    result.timeframes[result.strongest_timeframe];
                  const risk = strongest?.risk?.level || "—";

                  return (
                    <tr
                      key={result.symbol}
                      onClick={() => onSelectOpportunity(result)}
                      className={`cursor-pointer border-b border-line/60 hover:bg-[#102016] ${
                        selectedOpportunity?.symbol === result.symbol
                          ? "bg-[#12301b]"
                          : ""
                      }`}
                    >
                      <td className="p-3 text-muted">
                        {String(index + 1).padStart(2, "0")}
                      </td>

                      <td className="p-3">
                        <b>{result.symbol}</b>
                        {result.name && (
                          <span className="ml-2 text-xs text-muted">
                            {result.name}
                          </span>
                        )}
                      </td>

                      <td className="p-3">
                        <span
                          className={
                            result.signal === "BUY"
                              ? "font-bold text-accent"
                              : result.signal === "SELL"
                                ? "font-bold text-red-400"
                                : "font-bold text-yellow-300"
                          }
                        >
                          {result.signal}
                        </span>
                      </td>

                      <td className="p-3 font-semibold">
                        {result.confidence}%
                      </td>

                      <td className="p-3">
                        {result.grade}
                      </td>

                      <td className="p-3">
                        <span
                          className={
                            result.action === "ACTIVE"
                              ? "font-semibold text-accent"
                              : "text-yellow-300"
                          }
                        >
                          {result.action}
                        </span>
                      </td>

                      <td className="p-3">
                        {result.alignment}
                      </td>

                      <td className="p-3 font-semibold text-accent">
                        {result.strongest_timeframe}
                      </td>

                      <td
                        className={`p-3 ${
                          risk === "VERY HIGH" || risk === "HIGH"
                            ? "text-red-400"
                            : risk === "MEDIUM"
                              ? "text-yellow-300"
                              : "text-accent"
                        }`}
                      >
                        {risk}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            <div className="flex flex-wrap gap-4 border-t border-line px-4 py-3 text-xs text-muted">
              <span>Scanned: {marketScan.scanned}</span>
              <span>Successful: {marketScan.successful}</span>
              <span>Failed: {marketScan.failed}</span>
              <span>
                Ranked opportunities: {marketScan.opportunities.length}
              </span>
            </div>
          </div>
        )}
      </div>

      {selectedOpportunity && (
        <MultiTimeframeDetail
          opportunity={selectedOpportunity}
        />
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(360px,.8fr)_minmax(0,1.5fr)]">
        <div className="border border-line bg-panel">
          <div className="grid grid-cols-[1.2fr_.7fr_.6fr_32px] border-b border-line px-4 py-3 text-xs tracking-wider text-muted">
            <span>SYMBOL</span>
            <span>PRICE</span>
            <span>DAY</span>
            <span />
          </div>

          <div className="scrollbar max-h-[570px] overflow-y-auto">
            {watchlist.length === 0 ? (
              <p className="p-6 text-sm text-muted">
                Search the built-in NSE symbols or refresh
                the instrument master, then add a stock.
              </p>
            ) : (
              watchlist.map((item) => (
                <div
                  key={item.symbol}
                  className={`grid grid-cols-[1.2fr_.7fr_.6fr_32px] items-center px-4 py-4 ${
                    selected?.symbol === item.symbol
                      ? "bg-[#12301b]"
                      : "hover:bg-[#0f1e12]"
                  }`}
                >
                  <button
                    onClick={() => onSelect(item)}
                    className="text-left"
                  >
                    <b>{item.symbol}</b>
                    <span className="mt-1 block truncate text-xs text-muted">
                      {item.name}
                    </span>
                  </button>

                  <span>{money(item.last_price)}</span>

                  <span
                    className={
                      (item.change_percent || 0) >= 0
                        ? "text-accent"
                        : "text-red-400"
                    }
                  >
                    {item.change_percent == null
                      ? "—"
                      : `${
                          item.change_percent >= 0 ? "+" : ""
                        }${item.change_percent}%`}
                  </span>

                  <button
                    onClick={() =>
                      onRemove(item.symbol)
                    }
                    className="text-muted hover:text-red-400"
                    title={`Remove ${item.symbol}`}
                  >
                    ×
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="min-w-0 border border-line bg-panel">
          <div className="flex items-start justify-between border-b border-line p-5">
            <div>
              <h2 className="text-xl font-semibold">
                {selected?.symbol || "Select a stock"}
              </h2>

              <p className="mt-1 text-sm text-muted">
                {selected?.name ||
                  "Your chart will appear here"}
              </p>
            </div>

            <div className="text-right">
              <strong className="text-xl text-accent">
                {money(selected?.last_price)}
              </strong>

              <p className="mt-1 text-xs text-muted">
                EMA 20 · Volume
              </p>
            </div>
          </div>

          <div className="flex gap-2 border-b border-line p-4">
            {["15s", "1m", "5m", "15m"].map(
              (option) => (
                <button
                  key={option}
                  onClick={() => onInterval(option)}
                  className={`px-3 py-1.5 text-sm ${
                    interval === option
                      ? "bg-accent font-bold text-black"
                      : "border border-line text-muted hover:text-white"
                  }`}
                >
                  {option}
                </button>
              ),
            )}
          </div>

          {candles.length ? (
            <StockChart data={candles} interval={interval} />
          ) : (
            <div className="grid h-[430px] place-items-center text-muted">
              Select a watched stock to load its chart.
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function MultiTimeframeDetail({
  opportunity,
}: {
  opportunity: MarketOpportunity;
}) {
  const orderedTimeframes = ["1m", "5m", "15m"].filter(
    (timeframe) => opportunity.timeframes[timeframe],
  );

  return (
    <div className="mb-6 border border-line bg-panel">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line p-4">
        <div>
          <p className="text-xs tracking-[.18em] text-accent">
            MULTI-TIMEFRAME INTELLIGENCE
          </p>

          <div className="mt-1 flex flex-wrap items-center gap-3">
            <h2 className="text-xl font-semibold">
              {opportunity.symbol}
            </h2>

            <span
              className={
                opportunity.signal === "BUY"
                  ? "font-bold text-accent"
                  : opportunity.signal === "SELL"
                    ? "font-bold text-red-400"
                    : "font-bold text-yellow-300"
              }
            >
              {opportunity.signal}
            </span>

            <span className="text-sm text-muted">
              {opportunity.confidence}% confidence
            </span>

            <span className="text-sm text-muted">
              Grade {opportunity.grade}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 text-right text-xs">
          <div>
            <p className="text-muted">ACTION</p>
            <p
              className={
                opportunity.action === "ACTIVE"
                  ? "mt-1 font-semibold text-accent"
                  : "mt-1 font-semibold text-yellow-300"
              }
            >
              {opportunity.action}
            </p>
          </div>

          <div>
            <p className="text-muted">ALIGNMENT</p>
            <p className="mt-1 font-semibold">
              {opportunity.alignment}
            </p>
          </div>

          <div>
            <p className="text-muted">BEST TF</p>
            <p className="mt-1 font-semibold text-accent">
              {opportunity.strongest_timeframe}
            </p>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[1180px] text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs text-muted">
              <th className="p-3">TIMEFRAME</th>
              <th className="p-3">SIGNAL</th>
              <th className="p-3">CONFIDENCE</th>
              <th className="p-3">ACTION</th>
              <th className="p-3">RISK</th>
              <th className="p-3">TREND</th>
              <th className="p-3">MOMENTUM</th>
              <th className="p-3">PRESSURE</th>
              <th className="p-3">CANDLE FLOW</th>
              <th className="p-3">BREAKOUT</th>
            </tr>
          </thead>

          <tbody>
            {orderedTimeframes.map((timeframe) => {
              const item = opportunity.timeframes[timeframe];

              const trendStrength =
                item.trend_strength as {
                  classification?: string;
                  direction?: string;
                  adx?: number;
                };

              const momentum =
                item.momentum as {
                  classification?: string;
                  direction?: string;
                  rsi?: number;
                };

              const pressure =
                item.buyer_seller_pressure as {
                  pressure?: string;
                  dominance?: string;
                  buyers_score?: number;
                  sellers_score?: number;
                };

              const candleFlow =
                item.candle_flow as {
                  direction?: string;
                  strength?: string;
                  score?: number;
                };

              const breakout =
                item.breakout_readiness as {
                  status?: string;
                  readiness_score?: number;
                };

              return (
                <tr
                  key={timeframe}
                  className={
                    timeframe === opportunity.strongest_timeframe
                      ? "border-b border-line/60 bg-[#102016]"
                      : "border-b border-line/60"
                  }
                >
                  <td className="p-3">
                    <span className="font-bold text-accent">
                      {timeframe}
                    </span>
                    {timeframe === opportunity.strongest_timeframe && (
                      <span className="ml-2 text-[10px] text-yellow-300">
                        BEST
                      </span>
                    )}
                  </td>

                  <td className="p-3">
                    <span
                      className={
                        item.decision.signal === "BUY"
                          ? "font-bold text-accent"
                          : item.decision.signal === "SELL"
                            ? "font-bold text-red-400"
                            : "font-bold text-yellow-300"
                      }
                    >
                      {item.decision.signal}
                    </span>
                  </td>

                  <td className="p-3">
                    <b>{item.confidence.confidence}%</b>
                    <span className="ml-2 text-xs text-muted">
                      {item.confidence.probability}
                    </span>
                  </td>

                  <td className="p-3">
                    {item.decision.action}
                  </td>

                  <td
                    className={
                      item.risk.level === "VERY HIGH" ||
                      item.risk.level === "HIGH"
                        ? "p-3 text-red-400"
                        : item.risk.level === "MEDIUM"
                          ? "p-3 text-yellow-300"
                          : "p-3 text-accent"
                    }
                  >
                    {item.risk.level}
                  </td>

                  <td className="p-3">
                    <b>{trendStrength.direction || "—"}</b>
                    <span className="mt-1 block text-xs text-muted">
                      {trendStrength.classification || "—"} · ADX{" "}
                      {trendStrength.adx ?? "—"}
                    </span>
                  </td>

                  <td className="p-3">
                    <b>{momentum.direction || "—"}</b>
                    <span className="mt-1 block text-xs text-muted">
                      {momentum.classification || "—"} · RSI{" "}
                      {momentum.rsi ?? "—"}
                    </span>
                  </td>

                  <td className="p-3">
                    <b>{pressure.pressure || "—"}</b>
                    <span className="mt-1 block text-xs text-muted">
                      B {pressure.buyers_score ?? "—"} / S{" "}
                      {pressure.sellers_score ?? "—"}
                    </span>
                  </td>

                  <td className="p-3">
                    <b>{candleFlow.direction || "—"}</b>
                    <span className="mt-1 block text-xs text-muted">
                      {candleFlow.strength || "—"} · Score{" "}
                      {candleFlow.score ?? "—"}
                    </span>
                  </td>

                  <td className="p-3">
                    <b>{breakout.status || "—"}</b>
                    <span className="mt-1 block text-xs text-muted">
                      Readiness {breakout.readiness_score ?? "—"}%
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="grid gap-4 border-t border-line p-4 lg:grid-cols-3">
        {orderedTimeframes.map((timeframe) => {
          const item = opportunity.timeframes[timeframe];

          return (
            <div
              key={`${timeframe}-summary`}
              className="border border-line bg-ink/60 p-4"
            >
              <div className="mb-2 flex items-center justify-between">
                <b className="text-accent">
                  {timeframe.toUpperCase()} SUMMARY
                </b>

                <span className="text-xs text-muted">
                  Risk {item.risk.risk_score}/100
                </span>
              </div>

              <p className="text-xs leading-5 text-muted">
                {item.decision.summary}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PortfolioPanel({
  holdings,
  totalPnl,
  totalValue,
  onSave,
  onImport,
  busy,
}: {
  holdings: Holding[];
  totalPnl: number;
  totalValue: number;
  onSave: (event: FormEvent<HTMLFormElement>) => void;
  onImport: (
    event: FormEvent<HTMLFormElement>,
  ) => void;
  busy: boolean;
}) {
  return (
    <>
      <p className="text-xs tracking-[.18em] text-accent">
        HOLDINGS
      </p>

      <h1 className="mt-1 text-3xl font-semibold">
        Portfolio
      </h1>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <Metric
          label="Current value"
          value={money(totalValue)}
        />

        <Metric
          label="Unrealized P/L"
          value={money(totalPnl)}
          positive={totalPnl >= 0}
        />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.7fr_.8fr]">
        <div className="border border-line bg-panel">
          <div className="grid grid-cols-5 border-b border-line px-4 py-3 text-xs text-muted">
            <span>SYMBOL</span>
            <span>QTY</span>
            <span>AVG</span>
            <span>CURRENT</span>
            <span>P/L</span>
          </div>

          {holdings.length === 0 ? (
            <p className="p-6 text-sm text-muted">
              Add a holding below, or import a CSV with
              symbol, name, quantity, average_price, and
              optional token.
            </p>
          ) : (
            holdings.map((item) => (
              <div
                className="grid grid-cols-5 px-4 py-4"
                key={item.symbol}
              >
                <b>{item.symbol}</b>
                <span>{number(item.quantity)}</span>
                <span>{money(item.average_price)}</span>
                <span>{money(item.current_price)}</span>
                <span
                  className={
                    (item.unrealized_pnl || 0) >= 0
                      ? "text-accent"
                      : "text-red-400"
                  }
                >
                  {money(item.unrealized_pnl)}
                </span>
              </div>
            ))
          )}
        </div>

        <div className="space-y-6">
          <form
            onSubmit={onSave}
            className="border border-line bg-panel p-5"
          >
            <h2 className="mb-4 font-semibold">
              Add or update holding
            </h2>

            <div className="space-y-3">
              {[
                ["symbol", "NSE symbol e.g. RELIANCE"],
                ["name", "Company name"],
                ["token", "Angel token (optional in demo)"],
                ["quantity", "Quantity"],
                ["averagePrice", "Average buy price"],
              ].map(([name, placeholder]) => (
                <input
                  key={name}
                  name={name}
                  required={name !== "token"}
                  type={
                    name === "quantity" ||
                    name === "averagePrice"
                      ? "number"
                      : "text"
                  }
                  min={
                    name === "quantity" ||
                    name === "averagePrice"
                      ? "0.01"
                      : undefined
                  }
                  step="any"
                  placeholder={placeholder}
                  className="w-full border border-line bg-ink px-3 py-2.5 outline-none focus:border-accent"
                />
              ))}

              <button className="w-full bg-accent px-4 py-2.5 font-bold text-black">
                Save holding
              </button>
            </div>
          </form>

          <form
            onSubmit={onImport}
            className="border border-line bg-panel p-5"
          >
            <h2 className="mb-2 font-semibold">
              Import CSV
            </h2>

            <p className="mb-4 text-xs leading-5 text-muted">
              Headers: symbol, name, quantity,
              average_price. Token is optional.
            </p>

            <input
              name="file"
              type="file"
              accept=".csv,text/csv"
              className="mb-3 block w-full text-sm text-muted file:mr-3 file:border-0 file:bg-[#173b21] file:px-3 file:py-2 file:text-[#bdeecb]"
            />

            <button
              disabled={busy}
              className="w-full border border-accent px-4 py-2.5 font-semibold text-accent disabled:opacity-60"
            >
              {busy ? "Importing…" : "Import CSV"}
            </button>
          </form>
        </div>
      </div>
    </>
  );
}

function AlertsPanel({
  alerts,
  onSave,
  onToggle,
  onDelete,
}: {
  alerts: Alert[];
  onSave: (event: FormEvent<HTMLFormElement>) => void;
  onToggle: (alert: Alert, active: boolean) => void;
  onDelete: (alert: Alert) => void;
}) {
  return (
    <>
      <p className="text-xs tracking-[.18em] text-accent">
        NOTIFICATIONS
      </p>

      <h1 className="mt-1 text-3xl font-semibold">
        Alerts
      </h1>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.5fr_.8fr]">
        <div className="border border-line bg-panel">
          {alerts.length === 0 ? (
            <p className="p-6 text-sm text-muted">
              No alerts yet. Configure a target price to
              receive browser sound or Telegram
              notifications.
            </p>
          ) : (
            alerts.map((alert) => (
              <div
                key={alert.id}
                className="flex items-center justify-between gap-4 border-b border-line px-5 py-4"
              >
                <span>
                  <b>{alert.symbol}</b>
                  <span className="ml-3 text-muted">
                    {alert.condition}{" "}
                    {money(alert.target_price)}
                  </span>
                </span>

                <span className="flex items-center gap-3">
                  <span
                    className={
                      alert.active
                        ? "text-xs text-accent"
                        : "text-xs text-muted"
                    }
                  >
                    {alert.active
                      ? alert.delivery
                      : "TRIGGERED"}
                  </span>

                  <button
                    onClick={() =>
                      onToggle(alert, !alert.active)
                    }
                    className="text-xs text-muted hover:text-accent"
                  >
                    {alert.active
                      ? "Pause"
                      : "Reactivate"}
                  </button>

                  <button
                    onClick={() => onDelete(alert)}
                    className="text-lg text-muted hover:text-red-400"
                    title="Delete alert"
                  >
                    ×
                  </button>
                </span>
              </div>
            ))
          )}
        </div>

        <form
          onSubmit={onSave}
          className="border border-line bg-panel p-5"
        >
          <h2 className="mb-4 font-semibold">
            Create alert
          </h2>

          <div className="space-y-3">
            <input
              name="symbol"
              required
              placeholder="NSE symbol"
              className="w-full border border-line bg-ink px-3 py-2.5 outline-none focus:border-accent"
            />

            <input
              name="name"
              placeholder="Company name (optional)"
              className="w-full border border-line bg-ink px-3 py-2.5 outline-none focus:border-accent"
            />

            <select
              name="condition"
              className="w-full border border-line bg-ink px-3 py-2.5"
            >
              <option value="ABOVE">
                Price rises above
              </option>
              <option value="BELOW">
                Price falls below
              </option>
            </select>

            <input
              name="targetPrice"
              required
              min="0.01"
              step="any"
              type="number"
              placeholder="Target price"
              className="w-full border border-line bg-ink px-3 py-2.5 outline-none focus:border-accent"
            />

            <select
              name="delivery"
              className="w-full border border-line bg-ink px-3 py-2.5"
            >
              <option value="BROWSER">
                Browser sound
              </option>
              <option value="TELEGRAM">
                Telegram
              </option>
              <option value="BOTH">
                Browser + Telegram
              </option>
            </select>

            <button className="w-full bg-accent px-4 py-2.5 font-bold text-black">
              Save alert
            </button>
          </div>
        </form>
      </div>
    </>
  );
}

function Metric({
  label,
  value,
  positive,
}: {
  label: string;
  value: string;
  positive?: boolean;
}) {
  return (
    <div className="border border-line bg-panel p-5">
      <p className="text-sm text-muted">{label}</p>

      <p
        className={`mt-2 text-2xl font-semibold ${
          positive === undefined
            ? ""
            : positive
              ? "text-accent"
              : "text-red-400"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function playAlertSound() {
  try {
    const AudioContextConstructor =
      window.AudioContext ||
      (
        window as typeof window & {
          webkitAudioContext?: typeof window.AudioContext;
        }
      ).webkitAudioContext;

    if (!AudioContextConstructor) {
      return;
    }

    const context = new AudioContextConstructor();
    const oscillator = context.createOscillator();
    const gain = context.createGain();

    oscillator.frequency.value = 880;
    gain.gain.setValueAtTime(
      0.06,
      context.currentTime,
    );

    oscillator.connect(gain);
    gain.connect(context.destination);

    oscillator.start();
    oscillator.stop(context.currentTime + 0.2);

    oscillator.addEventListener("ended", () => {
      void context.close();
    });
  } catch {
    // Browser audio is optional.
  }
}