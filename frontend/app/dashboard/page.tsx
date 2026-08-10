"use client";

import {
  FormEvent,
  useEffect,
  useMemo,
  useState,
} from "react";

import StockChart, {
  Candle,
} from "../../components/StockChart";


type LiveStock = {
  symbol: string;
  token?: string;
  ltp: number;
  volume?: number | null;
  exchange_timestamp?: number | string | null;
  received_at?: string;
};


type LiveMarketMessage = {
  type: string;
  status?: string;
  stocks?: LiveStock[];
  count?: number;
  time?: string;
};


type LiveCandleResponse = {
  symbol: string;
  "1m": Candle[];
  "5m": Candle[];
  "15m": Candle[];
};

type InstrumentSearchResult = {
  symbol: string;
  name: string;
  token: string;
  kind: string;
};

type DashboardView =
  | "overview"
  | "scanner"
  | "watchlist"
  | "portfolio"
  | "alerts"
  | "backtest"
  | "analytics"
  | "settings";

type PortfolioHolding = {
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

type AlertItem = {
  id: number;
  symbol: string;
  name: string;
  condition: "ABOVE" | "BELOW";
  target_price: number;
  delivery: "BROWSER" | "TELEGRAM" | "BOTH";
  active: boolean;
};

type AlertEventItem = {
  id: number;
  alert_id: number;
  symbol: string;
  message: string;
  delivery: "BROWSER" | "TELEGRAM" | "BOTH";
  created_at: string;
};


type ScannerResult = {
  symbol: string;
  signal: string;
  score: number;
  grade: string;
  trend: string;
  reason: string;

  technical_analysis: {
    ema: string;
    ema_fast: number;
    ema_slow: number;

    supertrend: string;
    supertrend_value: number;

    adx: number;
    plus_di: number;
    minus_di: number;
    trend_strength: string;

    rsi: number;

    macd: string;
    macd_value: number;
    macd_signal: number;

    vwap: string;
    vwap_value: number;

    volume: string;
    volume_value: number;
    average_volume: number;

    atr: number;

    pattern: string | null;
    pattern_direction: string | null;
    pattern_confidence: number | null;
  };

  cpr?: {
    pivot: number;
    top_central: number;
    bottom_central: number;
    width: number;
    width_percent: number;
    classification: string;
    position: string;
  };

  trade_plan: {
    entry: number | null;
    stoploss: number | null;
    target1: number | null;
    target2: number | null;
    risk_reward: string;
  };

  analysis: {
    engine: string;
    confidence: number;
    probability_label: string;
    risk_label: string;
    summary: string;
  };

  ai_analysis: {
    engine: string;
    market_bias: string;
    trend_analysis: string;
    momentum_analysis: string;
    volume_analysis: string;
    risk_analysis: string;
    recommendation: string;
    overall_summary: string;
  };

  execution: {
    status: string;
    timeframe: string;
    last_price: number;
  };
};


const API_BASE =
  "http://localhost:8000";

const WS_URL =
  "ws://localhost:8000/api/ws/market";


const navigation = [
  ["⌂", "OVERVIEW", "Market Dashboard"],
  ["◈", "AI SCANNER", "Opportunities"],
  ["♡", "WATCHLIST", "Live Markets"],
  ["▣", "PORTFOLIO", "Holdings & P&L"],
  ["♢", "ALERTS", "Smart Notifications"],
  ["▧", "BACKTEST", "Strategy Lab"],
  ["⌁", "ANALYTICS", "Market Intelligence"],
  ["⚙", "SETTINGS", "Preferences"],
];


export default function Dashboard() {

  const [
    stocks,
    setStocks,
  ] = useState<LiveStock[]>([]);

  const [
    status,
    setStatus,
  ] = useState("CONNECTING");

  const [
    selected,
    setSelected,
  ] = useState("");

  const [
    clock,
    setClock,
  ] = useState(new Date());

  const [
    authenticated,
    setAuthenticated,
  ] = useState<boolean | null>(
    null
  );

  const [
    password,
    setPassword,
  ] = useState("");

  const [
    loginBusy,
    setLoginBusy,
  ] = useState(false);

  const [
    loginError,
    setLoginError,
  ] = useState("");

  const [
    wsVersion,
    setWsVersion,
  ] = useState(0);

  const [
    timeframe,
    setTimeframe,
  ] = useState<
    "1m" | "5m" | "15m"
  >("5m");

  const [
    chartData,
    setChartData,
  ] = useState<Candle[]>([]);

  const [
    chartLoading,
    setChartLoading,
  ] = useState(false);

  const [
    lastMarketUpdate,
    setLastMarketUpdate,
  ] = useState("");

  const [
    scanners,
    setScanners,
  ] = useState<
    Record<string, ScannerResult>
  >({});

  const [
    scannerLoading,
    setScannerLoading,
  ] = useState(false);

  const [
    activeView,
    setActiveView,
  ] = useState<DashboardView>("overview");

  const [
    searchQuery,
    setSearchQuery,
  ] = useState("");

  const [
    searchResults,
    setSearchResults,
  ] = useState<InstrumentSearchResult[]>([]);

  const [
    searchLoading,
    setSearchLoading,
  ] = useState(false);

  const [
    searchOpen,
    setSearchOpen,
  ] = useState(false);

  const [
    watchlistMessage,
    setWatchlistMessage,
  ] = useState("");

  const [
    holdings,
    setHoldings,
  ] = useState<PortfolioHolding[]>([]);

  const [
    portfolioLoading,
    setPortfolioLoading,
  ] = useState(false);

  const [
    portfolioMessage,
    setPortfolioMessage,
  ] = useState("");

  const [
    alerts,
    setAlerts,
  ] = useState<AlertItem[]>([]);

  const [
    alertsLoading,
    setAlertsLoading,
  ] = useState(false);

  const [
    alertsMessage,
    setAlertsMessage,
  ] = useState("");

  const [
    lastAlertEventId,
    setLastAlertEventId,
  ] = useState(0);


  // ==================================================
  // CLOCK
  // ==================================================

  useEffect(() => {

    const timer =
      window.setInterval(
        () => {
          setClock(
            new Date()
          );
        },
        1000
      );

    return () => {
      window.clearInterval(
        timer
      );
    };

  }, []);


  // ==================================================
  // LOGIN
  // ==================================================

  async function submitLogin(
    event:
      FormEvent<HTMLFormElement>
  ) {

    event.preventDefault();

    setLoginBusy(true);
    setLoginError("");

    try {

      const response =
        await fetch(
          `${API_BASE}/api/auth/login`,
          {
            method: "POST",

            credentials:
              "include",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                password,
              }),
          }
        );


      if (!response.ok) {

        const body =
          await response
            .json()
            .catch(
              () => ({})
            );

        throw new Error(
          body.detail ||
            "Login failed"
        );
      }


      setAuthenticated(
        true
      );

      setPassword("");

      setStatus(
        "CONNECTING"
      );

      setWsVersion(
        (current) =>
          current + 1
      );

    } catch (error) {

      setAuthenticated(
        false
      );

      setLoginError(
        error instanceof Error
          ? error.message
          : "Login failed"
      );

    } finally {

      setLoginBusy(
        false
      );
    }
  }


  // ==================================================
  // LIVE WEBSOCKET
  // ==================================================

  useEffect(() => {

    let socket:
      WebSocket | null =
      null;

    let retryTimer:
      ReturnType<
        typeof setTimeout
      > | null = null;

    let stopped = false;


    const connect = () => {

      setStatus(
        "CONNECTING"
      );

      socket =
        new WebSocket(
          WS_URL
        );


      socket.onopen =
        () => {

          setStatus(
            "LIVE"
          );

          setAuthenticated(
            true
          );
        };


      socket.onmessage =
        (event) => {

          try {

            const message:
              LiveMarketMessage =
              JSON.parse(
                event.data
              );


            if (
              message.type ===
                "market_update"
              &&
              Array.isArray(
                message.stocks
              )
            ) {

              setStocks(
                message.stocks
              );

              setLastMarketUpdate(
                message.time ||
                  new Date()
                    .toISOString()
              );


              setSelected(
                (current) => {

                  if (current) {
                    return current;
                  }

                  if (
                    message.stocks &&
                    message
                      .stocks
                      .length >
                      0
                  ) {

                    return (
                      message
                        .stocks[0]
                        .symbol
                    );
                  }

                  return "";
                }
              );
            }


            if (
              message.status ===
              "offline"
            ) {

              setStatus(
                "OFFLINE"
              );
            }

          } catch (error) {

            console.error(
              "Invalid websocket message",
              error
            );
          }
        };


      socket.onerror =
        () => {

          setStatus(
            "ERROR"
          );
        };


      socket.onclose =
        (event) => {

          if (
            event.code ===
            4401
          ) {

            setStatus(
              "LOGIN REQUIRED"
            );

            setAuthenticated(
              false
            );

            return;
          }


          setStatus(
            "OFFLINE"
          );


          if (!stopped) {

            retryTimer =
              setTimeout(
                connect,
                3000
              );
          }
        };
    };


    connect();


    return () => {

      stopped = true;


      if (retryTimer) {

        clearTimeout(
          retryTimer
        );
      }


      socket?.close();

    };

  }, [wsVersion]);


  // ==================================================
  // LIVE CANDLES
  // ==================================================

  useEffect(() => {

    if (!selected) {
      return;
    }


    let active = true;


    async function loadCandles() {

      setChartLoading(
        true
      );


      try {

        const response =
          await fetch(
            `${API_BASE}/api/live/candles/${selected}`,
            {
              credentials:
                "include",
            }
          );


        if (
          response.status ===
          401
        ) {

          setAuthenticated(
            false
          );

          return;
        }


        if (!response.ok) {

          throw new Error(
            await response.text()
          );
        }


        const data:
          LiveCandleResponse =
          await response.json();


        if (!active) {
          return;
        }


        setChartData(
          data[timeframe] ||
            []
        );

      } catch (error) {

        console.error(
          "Unable to load candles",
          error
        );


        if (active) {

          setChartData(
            []
          );
        }

      } finally {

        if (active) {

          setChartLoading(
            false
          );
        }
      }
    }


    loadCandles();


    const timer =
      window.setInterval(
        loadCandles,
        5000
      );


    return () => {

      active = false;

      window.clearInterval(
        timer
      );
    };

  }, [
    selected,
    timeframe,
  ]);


  // ==================================================
  // SORT STOCKS
  // ==================================================

  const sortedStocks =
    useMemo(
      () =>
        [...stocks].sort(
          (
            first,
            second
          ) =>
            first.symbol
              .localeCompare(
                second.symbol
              )
        ),
      [stocks]
    );


  const scannerSymbolsKey =
    useMemo(
      () =>
        sortedStocks
          .slice(0, 5)
          .map(
            (stock) =>
              stock.symbol
          )
          .join(","),
      [sortedStocks]
    );


  // ==================================================
  // V2 SCANNER
  // ==================================================

  useEffect(() => {

    if (
      !scannerSymbolsKey ||
      authenticated !==
        true
    ) {

      return;
    }


    let active = true;


    async function loadScanner() {

      setScannerLoading(
        true
      );


      const symbols =
        scannerSymbolsKey
          .split(",")
          .filter(Boolean);


      const results =
        await Promise.allSettled(

          symbols.map(
            async (
              symbol
            ) => {

              const response =
                await fetch(
                  `${API_BASE}/api/v2/scanner/${symbol}?interval=${timeframe}`,
                  {
                    credentials:
                      "include",
                  }
                );


              if (
                response.status ===
                401
              ) {

                throw new Error(
                  "Login required"
                );
              }


              if (
                !response.ok
              ) {

                throw new Error(
                  `${symbol}: scanner failed`
                );
              }


              const data:
                ScannerResult =
                await response
                  .json();


              return data;
            }
          )
        );


      if (!active) {
        return;
      }


      setScanners(
        (previous) => {

          const next = {
            ...previous,
          };


          results.forEach(
            (result) => {

              if (
                result.status ===
                "fulfilled"
              ) {

                next[
                  result.value
                    .symbol
                ] =
                  result.value;
              }
            }
          );


          return next;
        }
      );


      setScannerLoading(
        false
      );
    }


    loadScanner();


    const timer =
      window.setInterval(
        loadScanner,
        15000
      );


    return () => {

      active = false;

      window.clearInterval(
        timer
      );
    };

  }, [
    authenticated,
    timeframe,
    scannerSymbolsKey,
  ]);


  // ==================================================
  // PORTFOLIO + ALERTS
  // ==================================================

  async function loadPortfolio() {
    setPortfolioLoading(true);

    try {
      const response = await fetch(
        `${API_BASE}/api/portfolio/holdings`,
        {
          credentials: "include",
        }
      );

      if (!response.ok) {
        throw new Error(
          await response.text()
        );
      }

      const data:
        PortfolioHolding[] =
        await response.json();

      setHoldings(data);
    } catch (error) {
      setPortfolioMessage(
        error instanceof Error
          ? error.message
          : "Could not load portfolio"
      );
    } finally {
      setPortfolioLoading(false);
    }
  }


  async function loadAlerts() {
    setAlertsLoading(true);

    try {
      const response = await fetch(
        `${API_BASE}/api/alerts`,
        {
          credentials: "include",
        }
      );

      if (!response.ok) {
        throw new Error(
          await response.text()
        );
      }

      const data:
        AlertItem[] =
        await response.json();

      setAlerts(data);
    } catch (error) {
      setAlertsMessage(
        error instanceof Error
          ? error.message
          : "Could not load alerts"
      );
    } finally {
      setAlertsLoading(false);
    }
  }


  useEffect(() => {
    if (authenticated !== true) {
      return;
    }

    void loadPortfolio();
    void loadAlerts();
  }, [authenticated]);


  useEffect(() => {
    if (authenticated !== true) {
      return;
    }

    const poll = async () => {
      try {
        const response = await fetch(
          `${API_BASE}/api/alerts/events?after_id=${lastAlertEventId}`,
          {
            credentials: "include",
          }
        );

        if (!response.ok) {
          return;
        }

        const events:
          AlertEventItem[] =
          await response.json();

        if (!events.length) {
          return;
        }

        setLastAlertEventId(
          events[
            events.length - 1
          ].id
        );

        const latest =
          events[
            events.length - 1
          ];

        setAlertsMessage(
          latest.message
        );

        if (
          "Notification" in window &&
          Notification.permission ===
            "granted" &&
          (
            latest.delivery ===
              "BROWSER" ||
            latest.delivery ===
              "BOTH"
          )
        ) {
          new Notification(
            "NEXUS Market Alert",
            {
              body:
                latest.message,
            }
          );
        }

        void loadAlerts();
      } catch {
        // Background alert polling should not interrupt the dashboard.
      }
    };

    void poll();

    const timer =
      window.setInterval(
        poll,
        5000
      );

    return () => {
      window.clearInterval(
        timer
      );
    };
  }, [
    authenticated,
    lastAlertEventId,
  ]);


  async function saveHolding(
    event:
      FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    const form =
      new FormData(
        event.currentTarget
      );

    setPortfolioMessage("");

    try {
      const response = await fetch(
        `${API_BASE}/api/portfolio/holdings`,
        {
          method: "PUT",
          credentials: "include",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            symbol: String(
              form.get("symbol") ||
                ""
            ).toUpperCase(),
            name: String(
              form.get("name") ||
                ""
            ),
            token: String(
              form.get("token") ||
                ""
            ),
            quantity: Number(
              form.get("quantity")
            ),
            average_price: Number(
              form.get(
                "average_price"
              )
            ),
          }),
        }
      );

      if (!response.ok) {
        const body =
          await response
            .json()
            .catch(
              () => ({})
            );

        throw new Error(
          body.detail ||
            "Could not save holding"
        );
      }

      event.currentTarget.reset();

      setPortfolioMessage(
        "Holding saved"
      );

      await loadPortfolio();
    } catch (error) {
      setPortfolioMessage(
        error instanceof Error
          ? error.message
          : "Could not save holding"
      );
    }
  }


  async function importPortfolioCsv(
    event:
      FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    const form =
      new FormData(
        event.currentTarget
      );

    const file =
      form.get("file");

    if (
      !(file instanceof File) ||
      file.size === 0
    ) {
      setPortfolioMessage(
        "Choose a CSV file first"
      );
      return;
    }

    setPortfolioLoading(true);
    setPortfolioMessage("");

    try {
      const response = await fetch(
        `${API_BASE}/api/portfolio/import`,
        {
          method: "POST",
          credentials: "include",
          body: form,
        }
      );

      if (!response.ok) {
        const body =
          await response
            .json()
            .catch(
              () => ({})
            );

        throw new Error(
          body.detail ||
            "Could not import CSV"
        );
      }

      const result:
        { imported: number } =
        await response.json();

      setPortfolioMessage(
        `${result.imported} holdings imported`
      );

      event.currentTarget.reset();

      await loadPortfolio();
    } catch (error) {
      setPortfolioMessage(
        error instanceof Error
          ? error.message
          : "Could not import CSV"
      );
    } finally {
      setPortfolioLoading(false);
    }
  }


  async function createAlert(
    event:
      FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    const form =
      new FormData(
        event.currentTarget
      );

    setAlertsMessage("");

    try {
      const response = await fetch(
        `${API_BASE}/api/alerts`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            symbol: String(
              form.get("symbol") ||
                ""
            ).toUpperCase(),
            name: String(
              form.get("name") ||
                ""
            ),
            condition:
              form.get(
                "condition"
              ),
            target_price: Number(
              form.get(
                "target_price"
              )
            ),
            delivery:
              form.get(
                "delivery"
              ),
          }),
        }
      );

      if (!response.ok) {
        const body =
          await response
            .json()
            .catch(
              () => ({})
            );

        throw new Error(
          body.detail ||
            "Could not create alert"
        );
      }

      event.currentTarget.reset();

      setAlertsMessage(
        "Alert created"
      );

      await loadAlerts();
    } catch (error) {
      setAlertsMessage(
        error instanceof Error
          ? error.message
          : "Could not create alert"
      );
    }
  }


  async function setAlertActive(
    alert:
      AlertItem,
    active:
      boolean
  ) {
    try {
      const response = await fetch(
        `${API_BASE}/api/alerts/${alert.id}?active=${active}`,
        {
          method: "PATCH",
          credentials: "include",
        }
      );

      if (!response.ok) {
        throw new Error(
          await response.text()
        );
      }

      await loadAlerts();
    } catch (error) {
      setAlertsMessage(
        error instanceof Error
          ? error.message
          : "Could not update alert"
      );
    }
  }


  async function deleteAlert(
    alert:
      AlertItem
  ) {
    try {
      const response = await fetch(
        `${API_BASE}/api/alerts/${alert.id}`,
        {
          method: "DELETE",
          credentials: "include",
        }
      );

      if (!response.ok) {
        throw new Error(
          await response.text()
        );
      }

      await loadAlerts();
    } catch (error) {
      setAlertsMessage(
        error instanceof Error
          ? error.message
          : "Could not delete alert"
      );
    }
  }


  const totalPortfolioValue =
    useMemo(
      () =>
        holdings.reduce(
          (
            sum,
            item
          ) =>
            sum +
            (
              item.market_value ||
              0
            ),
          0
        ),
      [holdings]
    );


  const totalPortfolioPnl =
    useMemo(
      () =>
        holdings.reduce(
          (
            sum,
            item
          ) =>
            sum +
            (
              item.unrealized_pnl ||
              0
            ),
          0
        ),
      [holdings]
    );


  // ==================================================
  // INSTRUMENT SEARCH + NAVIGATION
  // ==================================================

  useEffect(() => {
    const value = searchQuery.trim();

    if (
      value.length < 1 ||
      authenticated !== true
    ) {
      setSearchResults([]);
      return;
    }

    let active = true;

    const timer = window.setTimeout(
      async () => {
        setSearchLoading(true);

        try {
          const response = await fetch(
            `${API_BASE}/api/instruments/search?q=${encodeURIComponent(
              value
            )}`,
            {
              credentials: "include",
            }
          );

          if (!response.ok) {
            throw new Error(
              await response.text()
            );
          }

          const data:
            InstrumentSearchResult[] =
            await response.json();

          if (active) {
            setSearchResults(data);
            setSearchOpen(true);
          }
        } catch (error) {
          console.error(
            "Instrument search failed",
            error
          );

          if (active) {
            setSearchResults([]);
          }
        } finally {
          if (active) {
            setSearchLoading(false);
          }
        }
      },
      250
    );

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [
    searchQuery,
    authenticated,
  ]);


  async function addInstrumentToWatchlist(
    item: InstrumentSearchResult
  ) {
    setWatchlistMessage("");

    try {
      const response = await fetch(
        `${API_BASE}/api/watchlist`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify(item),
        }
      );

      if (response.status === 409) {
        setWatchlistMessage(
          `${item.symbol} is already in the watchlist`
        );
        setSelected(item.symbol);
        setSearchOpen(false);
        return;
      }

      if (!response.ok) {
        const body = await response
          .json()
          .catch(() => ({}));

        throw new Error(
          body.detail ||
            "Could not add stock"
        );
      }

      setWatchlistMessage(
        `${item.symbol} added to watchlist`
      );

      setSelected(item.symbol);
      setSearchQuery("");
      setSearchResults([]);
      setSearchOpen(false);
      setActiveView("watchlist");
    } catch (error) {
      setWatchlistMessage(
        error instanceof Error
          ? error.message
          : "Could not add stock"
      );
    }
  }


  function handleNavigation(
    title: string
  ) {
    const map:
      Record<
        string,
        DashboardView
      > = {
        OVERVIEW: "overview",
        "AI SCANNER": "scanner",
        WATCHLIST: "watchlist",
        PORTFOLIO: "portfolio",
        ALERTS: "alerts",
        BACKTEST: "backtest",
        ANALYTICS: "analytics",
        SETTINGS: "settings",
      };

    const next =
      map[title] || "overview";

    setActiveView(next);

    const sectionId =
      next === "overview"
        ? "overview-section"
        : next === "scanner"
        ? "scanner-section"
        : next === "watchlist"
        ? "watchlist-section"
        : next === "portfolio"
        ? "portfolio-section"
        : next === "alerts"
        ? "alerts-section"
        : next === "backtest"
        ? "backtest-section"
        : next === "analytics"
        ? "analytics-section"
        : "settings-section";

    window.setTimeout(
      () => {
        document
          .getElementById(sectionId)
          ?.scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
      },
      0
    );
  }


  // ==================================================
  // SELECTED STOCK
  // ==================================================

  const selectedStock =
    useMemo(
      () =>
        stocks.find(
          (stock) =>
            stock.symbol ===
            selected
        ),
      [
        stocks,
        selected,
      ]
    );


  const selectedScanner =
    selected
      ? scanners[
          selected
        ]
      : undefined;


  // ==================================================
  // LOGIN SCREEN
  // ==================================================

  if (
    authenticated ===
    false
  ) {

    return (
      <main className="nexus-login">

        <div className="login-orb">

          <div
            className="
              login-orb-ring
              login-ring-a
            "
          />

          <div
            className="
              login-orb-ring
              login-ring-b
            "
          />

          <div className="login-ai">
            AI
          </div>

        </div>


        <form
          className="nexus-login-card"
          onSubmit={
            submitLogin
          }
        >

          <span className="eyebrow">
            NEXUS AI SECURITY
          </span>


          <h1>
            MARKET TERMINAL
          </h1>


          <p>
            Authenticate to access
            the private AI market
            intelligence system.
          </p>


          <label>
            OWNER ACCESS KEY
          </label>


          <input
            type="password"
            value={
              password
            }
            onChange={
              (event) =>
                setPassword(
                  event.target
                    .value
                )
            }
            placeholder="Enter password"
            required
            autoFocus
          />


          {loginError && (

            <div className="login-error">

              {loginError}

            </div>

          )}


          <button
            type="submit"
            disabled={
              loginBusy
            }
          >

            {loginBusy
              ? "AUTHENTICATING..."
              : "ENTER TERMINAL"}

          </button>


          <div className="login-security">

            <i />

            ENCRYPTED PRIVATE
            SESSION

          </div>

        </form>

      </main>
    );
  }


  // ==================================================
  // DASHBOARD
  // ==================================================

  return (
    <main className="terminal">

      {/* =================================================
          SIDEBAR
      ================================================= */}

      <aside className="sidebar">

        <div className="logo">

          <div className="logo-cube">
            ◇
          </div>


          <div>

            <strong>
              NEXUS AI
            </strong>

            <span>
              MARKET TERMINAL
            </span>

          </div>

        </div>


        <nav className="nav">

          {navigation.map(
            (
              [
                icon,
                title,
                subtitle,
              ]
            ) => {

              const viewMap:
                Record<
                  string,
                  DashboardView
                > = {
                  OVERVIEW: "overview",
                  "AI SCANNER": "scanner",
                  WATCHLIST: "watchlist",
                  PORTFOLIO: "portfolio",
                  ALERTS: "alerts",
                  BACKTEST: "backtest",
                  ANALYTICS: "analytics",
                  SETTINGS: "settings",
                };

              const itemView =
                viewMap[title] ||
                "overview";

              return (

              <button
                key={
                  title
                }
                onClick={
                  () =>
                    handleNavigation(
                      title
                    )
                }
                className={
                  activeView ===
                  itemView
                    ? "nav-item active"
                    : "nav-item"
                }
              >

                <span className="nav-icon">
                  {icon}
                </span>


                <span className="nav-copy">

                  <strong>
                    {title}
                  </strong>

                  <small>
                    {subtitle}
                  </small>

                </span>


                <span className="nav-arrow">
                  ›
                </span>

              </button>

              );
            }
          )}

        </nav>


        <div className="ai-core">

          <span className="eyebrow">
            AI ENGINE
          </span>


          <div className="online">

            <i />

            ONLINE

          </div>


          <div className="orb">

            <div className="orb-ring ring-one" />

            <div className="orb-ring ring-two" />

            <div className="orb-core">
              AI
            </div>

          </div>


          <small>
            LEARNING • ADAPTING •
            EVOLVING
          </small>

        </div>

      </aside>


      {/* =================================================
          WORKSPACE
      ================================================= */}

      <section className="workspace">


        {/* ===============================================
            HEADER
        =============================================== */}

        <header className="terminal-header">

          <div
            className="search"
            style={{
              position: "relative",
            }}
          >

            <input
              value={searchQuery}
              onChange={
                (event) =>
                  setSearchQuery(
                    event.target.value
                  )
              }
              onFocus={
                () =>
                  setSearchOpen(true)
              }
              placeholder="Search NSE symbol or company"
              style={{
                width: "100%",
                border: "none",
                outline: "none",
                background: "transparent",
                color: "inherit",
              }}
            />

            <span>
              {searchLoading
                ? "…"
                : "⌕"}
            </span>


            {searchOpen &&
            searchQuery.trim() && (
              <div
                style={{
                  position: "absolute",
                  top: "calc(100% + 8px)",
                  left: 0,
                  right: 0,
                  zIndex: 100,
                  border:
                    "1px solid #173450",
                  borderRadius: "7px",
                  background: "#030914",
                  maxHeight: "320px",
                  overflowY: "auto",
                  boxShadow:
                    "0 20px 60px rgba(0,0,0,.45)",
                }}
              >

                {searchResults.length > 0 ? (
                  searchResults.map(
                    (item) => (
                      <button
                        key={`${item.symbol}-${item.token}`}
                        type="button"
                        onClick={
                          () =>
                            addInstrumentToWatchlist(
                              item
                            )
                        }
                        style={{
                          width: "100%",
                          display: "flex",
                          alignItems:
                            "center",
                          justifyContent:
                            "space-between",
                          gap: "12px",
                          padding:
                            "12px 14px",
                          border: "none",
                          borderBottom:
                            "1px solid #102238",
                          background:
                            "transparent",
                          color: "#dffaff",
                          textAlign: "left",
                        }}
                      >
                        <span>
                          <strong
                            style={{
                              display:
                                "block",
                            }}
                          >
                            {item.symbol}
                          </strong>

                          <small
                            style={{
                              color:
                                "#71869c",
                            }}
                          >
                            {item.name}
                          </small>
                        </span>

                        <span
                          style={{
                            color:
                              "#00f59b",
                            fontSize:
                              "10px",
                            fontWeight: 700,
                          }}
                        >
                          ADD
                        </span>
                      </button>
                    )
                  )
                ) : (
                  <div
                    style={{
                      padding: "14px",
                      color: "#71869c",
                      fontSize:
                        "11px",
                    }}
                  >
                    No NSE instruments found
                  </div>
                )}

              </div>
            )}

          </div>


          <div className="exchange">

            ◉ NSE

            <i />

            LIVE MARKET

          </div>


          <div className="clock">

            <strong>

              {clock
                .toLocaleTimeString(
                  "en-IN"
                )}

            </strong>


            <span>

              {clock
                .toLocaleDateString(
                  "en-GB",
                  {
                    day:
                      "2-digit",

                    month:
                      "short",

                    year:
                      "numeric",
                  }
                )
                .toUpperCase()}

            </span>

          </div>


          <div className="core-status">

            <div className="brain">
              ⌬
            </div>


            <div>

              <small>
                AI CORE STATUS
              </small>

              <strong>
                ONLINE
              </strong>

            </div>

          </div>

        </header>


        {/* ===============================================
            TOP CARDS
        =============================================== */}

        <section id="overview-section" className="indices">

          <MarketCard
            name="NIFTY 50"
            value="—"
            change="LIVE FEED"
          />


          <MarketCard
            name="SENSEX"
            value="—"
            change="MARKET"
          />


          <MarketCard
            name="NIFTY BANK"
            value="—"
            change="MONITORING"
          />


          <MarketCard
            name="WATCHLIST"
            value={
              String(
                stocks.length
              )
            }
            change="CONNECTED"
          />


          <div className="market-state">

            <div>

              <span className="eyebrow">
                MARKET STATE
              </span>


              <strong>
                {status}
              </strong>


              <small>
                ANGEL ONE FEED
              </small>

            </div>


            <div className="confidence-ring">

              <span>

                {status ===
                "LIVE"
                  ? "LIVE"
                  : "—"}

              </span>

            </div>

          </div>

        </section>


        {/* ===============================================
            CHART + WATCHLIST
        =============================================== */}

        <section className="primary-grid">


          {/* =============================================
              CHART
          ============================================= */}

          <div className="glass chart-card">

            <div className="card-heading">


              <div>

                <span className="eyebrow">
                  LIVE CHART
                </span>


                <h2>

                  {selected ||
                    "SELECT STOCK"}

                  <small>
                    {" "}
                    • NSE
                  </small>

                </h2>


                <div className="hero-price">

                  {selectedStock
                    ? `₹ ${selectedStock.ltp.toFixed(
                        2
                      )}`
                    : "Waiting for market data"}

                </div>


                {selectedScanner && (

                  <div className="selected-signal-strip">


                    <SignalBadge
                      signal={
                        selectedScanner.signal
                      }
                    />


                    <span
                      className={
                        trendClass(
                          selectedScanner
                            .trend
                        )
                      }
                    >

                      {
                        selectedScanner
                          .trend
                      }

                    </span>


                    <span>

                      CONFIDENCE{" "}
                      {
                        selectedScanner
                          .analysis
                          .confidence
                      }
                      %

                    </span>


                    <span>

                      {
                        selectedScanner
                          .analysis
                          .probability_label
                      }

                    </span>


                    <span>

                      GRADE{" "}
                      {
                        selectedScanner
                          .grade
                      }

                    </span>


                    <span>

                      {
                        selectedScanner
                          .execution
                          .status
                      }

                    </span>

                  </div>

                )}

              </div>


              <div className="timeframes">

                {(
                  [
                    "1m",
                    "5m",
                    "15m",
                  ] as const
                ).map(
                  (value) => (

                    <button
                      key={
                        value
                      }
                      className={
                        timeframe ===
                        value
                          ? "selected-time"
                          : ""
                      }
                      onClick={
                        () =>
                          setTimeframe(
                            value
                          )
                      }
                    >

                      {value}

                    </button>

                  )
                )}

              </div>

            </div>


            <div className="future-chart real-chart">

              {chartLoading &&
              chartData.length ===
                0 ? (

                <div className="chart-message">

                  <div className="pulse-line" />

                  <strong>
                    LOADING MARKET DATA
                  </strong>

                  <span>

                    Loading{" "}
                    {timeframe}
                    {" "}
                    candles for{" "}
                    {selected}

                  </span>

                </div>

              ) : chartData.length >
                0 ? (

                <StockChart
                  data={
                    chartData
                  }
                  interval={
                    timeframe
                  }
                />

              ) : (

                <div className="chart-message">

                  <div className="pulse-line" />

                  <strong>
                    WAITING FOR CANDLES
                  </strong>

                  <span>

                    No{" "}
                    {timeframe}
                    {" "}
                    candles available

                  </span>

                </div>

              )}

            </div>


            <div className="chart-meta">

              <span>

                TIMEFRAME

                <strong>
                  {timeframe}
                </strong>

              </span>


              <span>

                CANDLES

                <strong>
                  {
                    chartData.length
                  }
                </strong>

              </span>


              <span>

                EMA

                <strong>
                  EMA 20
                </strong>

              </span>


              <span>

                LAST FEED

                <strong>

                  {lastMarketUpdate
                    ? new Date(
                        lastMarketUpdate
                      )
                        .toLocaleTimeString(
                          "en-IN"
                        )
                    : "—"}

                </strong>

              </span>

            </div>

          </div>


          {/* =============================================
              WATCHLIST
          ============================================= */}

          <div id="watchlist-section" className="glass watchlist-card">

            <div className="card-heading compact">

              <span className="eyebrow">
                〽 LIVE WATCHLIST
              </span>

              <span className="counter">
                {stocks.length}
              </span>

            </div>


            <div className="watch-head">

              <span>
                SYMBOL
              </span>

              <span>
                LTP
              </span>

              <span>
                VOLUME
              </span>

              <span>
                SIGNAL
              </span>

            </div>


            <div className="watch-scroll">

              {sortedStocks.length ===
              0 ? (

                <div className="waiting">

                  Waiting for
                  Angel One live
                  market data...

                </div>

              ) : (

                sortedStocks.map(
                  (stock) => {

                    const scanner =
                      scanners[
                        stock.symbol
                      ];


                    return (

                      <button
                        key={
                          stock.symbol
                        }
                        className={
                          stock.symbol ===
                          selected
                            ? "watch-row selected-stock"
                            : "watch-row"
                        }
                        onClick={
                          () =>
                            setSelected(
                              stock.symbol
                            )
                        }
                      >

                        <strong>

                          {
                            stock.symbol
                          }

                        </strong>


                        <span className="live-price">

                          ₹
                          {stock.ltp.toFixed(
                            2
                          )}

                        </span>


                        <span>

                          {stock.volume ??
                            "—"}

                        </span>


                        {scanner ? (

                          <SignalBadge
                            signal={
                              scanner.signal
                            }
                            small
                          />

                        ) : (

                          <b>
                            LIVE
                          </b>

                        )}

                      </button>

                    );
                  }
                )

              )}

            </div>

          </div>

        </section>


        {/* ===============================================
            AI AREA
        =============================================== */}

        <section className="secondary-grid">


          {/* =============================================
              OPPORTUNITY MATRIX
          ============================================= */}

          <div id="scanner-section" className="glass opportunity">

            <div className="card-heading compact">

              <span className="eyebrow">

                ◈ AI OPPORTUNITY MATRIX

              </span>


              <span className="live-scan">

                {scannerLoading
                  ? "● ANALYZING"
                  : "● LIVE SCAN"}

              </span>

            </div>


            <div className="opportunity-head">

              <span>
                SYMBOL
              </span>

              <span>
                SIGNAL
              </span>

              <span>
                CONFIDENCE
              </span>

              <span>
                TREND
              </span>

              <span>
                GRADE
              </span>

              <span>
                ENTRY / SL
              </span>

              <span>
                TARGETS
              </span>

            </div>


            {sortedStocks
              .slice(
                0,
                5
              )
              .map(
                (stock) => {

                  const scanner =
                    scanners[
                      stock.symbol
                    ];


                  return (

                    <button
                      className="
                        opportunity-row
                        opportunity-button
                      "
                      key={
                        stock.symbol
                      }
                      onClick={
                        () =>
                          setSelected(
                            stock.symbol
                          )
                      }
                    >


                      <strong>

                        {
                          stock.symbol
                        }

                      </strong>


                      {scanner ? (

                        <SignalBadge
                          signal={
                            scanner.signal
                          }
                        />

                      ) : (

                        <span className="waiting-signal">

                          ANALYZING

                        </span>

                      )}


                      <div className="score-cell">

                        {scanner
                          ? `${scanner.analysis.confidence}%`
                          : "—"}


                        {scanner && (

                          <>

                            <div className="score-track">

                              <i
                                style={{
                                  width:
                                    `${Math.max(
                                      3,
                                      scanner
                                        .analysis
                                        .confidence
                                    )}%`,
                                }}
                              />

                            </div>


                            <small>

                              {
                                scanner
                                  .analysis
                                  .probability_label
                              }

                            </small>

                          </>

                        )}

                      </div>


                      <span
                        className={
                          scanner
                            ? trendClass(
                                scanner.trend
                              )
                            : ""
                        }
                      >

                        {scanner
                          ? scanner.trend
                          : "—"}

                      </span>


                      <span>

                        {scanner
                          ? scanner.grade
                          : "—"}

                      </span>


                      <span className="price-stack">

                        {scanner &&
                        scanner
                          .trade_plan
                          .entry !==
                          null ? (

                          <>

                            <strong>

                              ₹
                              {
                                scanner
                                  .trade_plan
                                  .entry
                              }

                            </strong>


                            <small>

                              SL ₹
                              {
                                scanner
                                  .trade_plan
                                  .stoploss
                              }

                            </small>

                          </>

                        ) : (

                          "—"

                        )}

                      </span>


                      <span className="price-stack">

                        {scanner &&
                        scanner
                          .trade_plan
                          .target1 !==
                          null ? (

                          <>

                            <strong>

                              T1 ₹
                              {
                                scanner
                                  .trade_plan
                                  .target1
                              }

                            </strong>


                            <small>

                              T2 ₹
                              {
                                scanner
                                  .trade_plan
                                  .target2
                              }

                            </small>

                          </>

                        ) : (

                          "—"

                        )}

                      </span>

                    </button>

                  );
                }
              )}


            {sortedStocks.length ===
              0 && (

              <div className="waiting large">

                AI opportunity
                engine waiting for
                live market feed

              </div>

            )}

          </div>


          {/* =============================================
              MARKET PULSE
          ============================================= */}

          <div className="glass pulse-card">

            <span className="eyebrow">
              MARKET PULSE
            </span>


            <div className="radar">

              <div className="radar-ring r1" />

              <div className="radar-ring r2" />

              <div className="radar-ring r3" />


              <div className="radar-center">

                {selectedScanner
                  ? `${selectedScanner.analysis.confidence}`
                  : "AI"}

              </div>

            </div>


            <div className="pulse-stats">

              <span>

                TREND

                <strong
                  className={
                    selectedScanner
                      ? trendClass(
                          selectedScanner
                            .trend
                        )
                      : ""
                  }
                >

                  {selectedScanner
                    ? selectedScanner
                        .trend
                    : "—"}

                </strong>

              </span>


              <span>

                SIGNAL

                <strong>

                  {selectedScanner
                    ? selectedScanner
                        .signal
                    : "—"}

                </strong>

              </span>


              <span>

                CONFIDENCE

                <strong>

                  {selectedScanner
                    ? `${selectedScanner.analysis.confidence}%`
                    : "—"}

                </strong>

              </span>

            </div>

          </div>


          {/* =============================================
              AI SUMMARY
          ============================================= */}

          <div className="glass ai-summary">

            <span className="eyebrow">

              AI MARKET SUMMARY

            </span>


            {selectedScanner ? (

              <>

                <h3 className="summary-symbol">

                  {
                    selectedScanner
                      .symbol
                  }


                  <SignalBadge
                    signal={
                      selectedScanner
                        .signal
                    }
                    small
                  />

                </h3>


                <div className="analysis-tags">

                  <span>

                    CONF{" "}
                    {
                      selectedScanner
                        .analysis
                        .confidence
                    }
                    %

                  </span>


                  <span>

                    {
                      selectedScanner
                        .analysis
                        .probability_label
                    }

                  </span>


                  <span className="risk-tag">

                    RISK{" "}
                    {
                      selectedScanner
                        .analysis
                        .risk_label
                    }

                  </span>

                </div>


                <p>

                  {
                    selectedScanner
                      .ai_analysis
                      .overall_summary
                  }

                </p>


                {selectedScanner
                  .technical_analysis
                  .pattern && (

                  <div className="pattern-box">

                    <span>
                      PATTERN
                    </span>


                    <strong>

                      {
                        selectedScanner
                          .technical_analysis
                          .pattern
                      }

                    </strong>


                    <small>

                      {
                        selectedScanner
                          .technical_analysis
                          .pattern_confidence ??
                        0
                      }
                      % confidence

                    </small>

                  </div>

                )}


                <div className="trade-detail-grid">

                  <div>

                    <span>
                      ENTRY
                    </span>

                    <strong>

                      {formatPrice(
                        selectedScanner
                          .trade_plan
                          .entry
                      )}

                    </strong>

                  </div>


                  <div>

                    <span>
                      STOP
                    </span>

                    <strong>

                      {formatPrice(
                        selectedScanner
                          .trade_plan
                          .stoploss
                      )}

                    </strong>

                  </div>


                  <div>

                    <span>
                      T1
                    </span>

                    <strong>

                      {formatPrice(
                        selectedScanner
                          .trade_plan
                          .target1
                      )}

                    </strong>

                  </div>


                  <div>

                    <span>
                      T2
                    </span>

                    <strong>

                      {formatPrice(
                        selectedScanner
                          .trade_plan
                          .target2
                      )}

                    </strong>

                  </div>

                </div>


                <div className="rr-box">

                  RISK / REWARD

                  <strong>

                    {
                      selectedScanner
                        .trade_plan
                        .risk_reward
                    }

                  </strong>

                </div>

              </>

            ) : (

              <p>

                Select a stock to
                see its V2 scanner
                analysis.

              </p>

            )}


            <div className="sector-box">

              <span>
                EXECUTION STATUS
              </span>


              <strong>

                {selectedScanner
                  ? selectedScanner
                      .execution
                      .status
                  : status}

              </strong>

            </div>

          </div>

        </section>


        <section
          id="portfolio-section"
          className="glass"
          style={{
            marginTop: "12px",
            padding: "18px",
          }}
        >
          <div className="card-heading compact">
            <div>
              <span className="eyebrow">
                ▣ PORTFOLIO
              </span>
              <h2>
                Holdings & P/L
              </h2>
            </div>

            <button
              type="button"
              onClick={
                () =>
                  void loadPortfolio()
              }
              className="selected-time"
            >
              {portfolioLoading
                ? "LOADING..."
                : "REFRESH"}
            </button>
          </div>

          <div
            className="trade-detail-grid"
            style={{
              marginTop: "14px",
            }}
          >
            <div>
              <span>
                CURRENT VALUE
              </span>
              <strong>
                {formatPrice(
                  totalPortfolioValue
                )}
              </strong>
            </div>

            <div>
              <span>
                UNREALIZED P/L
              </span>
              <strong
                className={
                  totalPortfolioPnl >= 0
                    ? "trend-bullish"
                    : "trend-bearish"
                }
              >
                {formatPrice(
                  totalPortfolioPnl
                )}
              </strong>
            </div>
          </div>

          {portfolioMessage && (
            <div
              style={{
                marginTop: "10px",
                color: "#7af5ff",
                fontSize: "10px",
              }}
            >
              {portfolioMessage}
            </div>
          )}

          <div
            style={{
              marginTop: "14px",
              overflowX: "auto",
            }}
          >
            <table
              style={{
                width: "100%",
                borderCollapse:
                  "collapse",
                fontSize: "11px",
              }}
            >
              <thead>
                <tr
                  style={{
                    color: "#71869c",
                    textAlign: "left",
                  }}
                >
                  <th style={{ padding: "8px" }}>SYMBOL</th>
                  <th style={{ padding: "8px" }}>QTY</th>
                  <th style={{ padding: "8px" }}>AVG</th>
                  <th style={{ padding: "8px" }}>CURRENT</th>
                  <th style={{ padding: "8px" }}>VALUE</th>
                  <th style={{ padding: "8px" }}>P/L</th>
                </tr>
              </thead>

              <tbody>
                {holdings.map(
                  (item) => (
                    <tr
                      key={
                        item.symbol
                      }
                      style={{
                        borderTop:
                          "1px solid #102238",
                      }}
                    >
                      <td style={{ padding: "8px" }}>
                        <strong>
                          {item.symbol}
                        </strong>
                      </td>
                      <td style={{ padding: "8px" }}>
                        {item.quantity}
                      </td>
                      <td style={{ padding: "8px" }}>
                        {formatPrice(
                          item.average_price
                        )}
                      </td>
                      <td style={{ padding: "8px" }}>
                        {formatPrice(
                          item.current_price
                        )}
                      </td>
                      <td style={{ padding: "8px" }}>
                        {formatPrice(
                          item.market_value
                        )}
                      </td>
                      <td
                        style={{
                          padding: "8px",
                        }}
                        className={
                          (
                            item.unrealized_pnl ||
                            0
                          ) >= 0
                            ? "trend-bullish"
                            : "trend-bearish"
                        }
                      >
                        {formatPrice(
                          item.unrealized_pnl
                        )}
                      </td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit, minmax(260px, 1fr))",
              gap: "12px",
              marginTop: "16px",
            }}
          >
            <form
              onSubmit={
                saveHolding
              }
              className="pattern-box"
            >
              <span>
                ADD / UPDATE HOLDING
              </span>

              {[
                ["symbol", "Symbol"],
                ["name", "Company name"],
                ["token", "Angel token"],
                ["quantity", "Quantity"],
                [
                  "average_price",
                  "Average buy price",
                ],
              ].map(
                ([name, label]) => (
                  <input
                    key={name}
                    name={name}
                    required={
                      name !==
                      "token"
                    }
                    type={
                      name ===
                        "quantity" ||
                      name ===
                        "average_price"
                        ? "number"
                        : "text"
                    }
                    step="any"
                    placeholder={label}
                    style={{
                      width: "100%",
                      marginTop: "8px",
                      padding:
                        "10px",
                      border:
                        "1px solid #173450",
                      background:
                        "#030914",
                      color:
                        "#dffaff",
                    }}
                  />
                )
              )}

              <button
                type="submit"
                className="selected-time"
                style={{
                  width: "100%",
                  marginTop: "10px",
                }}
              >
                SAVE HOLDING
              </button>
            </form>

            <form
              onSubmit={
                importPortfolioCsv
              }
              className="pattern-box"
            >
              <span>
                IMPORT PORTFOLIO CSV
              </span>

              <p
                style={{
                  color: "#71869c",
                  fontSize: "10px",
                  lineHeight: 1.6,
                }}
              >
                Headers: symbol,
                name, quantity,
                average_price.
                token is optional.
              </p>

              <input
                name="file"
                type="file"
                accept=".csv,text/csv"
                style={{
                  width: "100%",
                  marginTop: "10px",
                  color: "#dffaff",
                }}
              />

              <button
                type="submit"
                className="selected-time"
                disabled={
                  portfolioLoading
                }
                style={{
                  width: "100%",
                  marginTop: "10px",
                }}
              >
                IMPORT CSV
              </button>
            </form>
          </div>
        </section>

        <section
          id="alerts-section"
          className="glass"
          style={{
            marginTop: "12px",
            padding: "18px",
          }}
        >
          <div className="card-heading compact">
            <div>
              <span className="eyebrow">
                ♢ ALERTS
              </span>
              <h2>
                Smart Notifications
              </h2>
            </div>

            <button
              type="button"
              onClick={
                () => {
                  if (
                    "Notification" in
                    window
                  ) {
                    void Notification
                      .requestPermission();
                  }
                }
              }
              className="selected-time"
            >
              ENABLE BROWSER ALERTS
            </button>
          </div>

          {alertsMessage && (
            <div
              style={{
                marginTop: "10px",
                color: "#7af5ff",
                fontSize: "10px",
              }}
            >
              {alertsMessage}
            </div>
          )}

          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "minmax(0, 1.4fr) minmax(280px, .6fr)",
              gap: "12px",
              marginTop: "14px",
            }}
          >
            <div
              className="pattern-box"
              style={{
                margin: 0,
              }}
            >
              <span>
                ACTIVE / TRIGGERED ALERTS
              </span>

              {alertsLoading ? (
                <p
                  style={{
                    color: "#71869c",
                    fontSize: "10px",
                  }}
                >
                  Loading alerts...
                </p>
              ) : alerts.length === 0 ? (
                <p
                  style={{
                    color: "#71869c",
                    fontSize: "10px",
                  }}
                >
                  No alerts created yet.
                </p>
              ) : (
                alerts.map(
                  (alert) => (
                    <div
                      key={
                        alert.id
                      }
                      style={{
                        display: "grid",
                        gridTemplateColumns:
                          "1fr auto",
                        gap: "10px",
                        alignItems:
                          "center",
                        padding:
                          "10px 0",
                        borderTop:
                          "1px solid #102238",
                      }}
                    >
                      <div>
                        <strong>
                          {alert.symbol}
                        </strong>

                        <small
                          style={{
                            display:
                              "block",
                            color:
                              "#71869c",
                            marginTop:
                              "3px",
                          }}
                        >
                          {alert.condition}{" "}
                          {formatPrice(
                            alert.target_price
                          )}{" "}
                          •{" "}
                          {alert.delivery}
                        </small>
                      </div>

                      <div
                        style={{
                          display:
                            "flex",
                          gap: "6px",
                        }}
                      >
                        <button
                          type="button"
                          className="selected-time"
                          onClick={
                            () =>
                              void setAlertActive(
                                alert,
                                !alert.active
                              )
                          }
                        >
                          {alert.active
                            ? "PAUSE"
                            : "REACTIVATE"}
                        </button>

                        <button
                          type="button"
                          className="selected-time"
                          onClick={
                            () =>
                              void deleteAlert(
                                alert
                              )
                          }
                        >
                          DELETE
                        </button>
                      </div>
                    </div>
                  )
                )
              )}
            </div>

            <form
              onSubmit={
                createAlert
              }
              className="pattern-box"
              style={{
                margin: 0,
              }}
            >
              <span>
                CREATE ALERT
              </span>

              <input
                name="symbol"
                required
                placeholder="NSE symbol"
                style={{
                  width: "100%",
                  marginTop: "8px",
                  padding: "10px",
                  border:
                    "1px solid #173450",
                  background:
                    "#030914",
                  color: "#dffaff",
                }}
              />

              <input
                name="name"
                placeholder="Company name"
                style={{
                  width: "100%",
                  marginTop: "8px",
                  padding: "10px",
                  border:
                    "1px solid #173450",
                  background:
                    "#030914",
                  color: "#dffaff",
                }}
              />

              <select
                name="condition"
                style={{
                  width: "100%",
                  marginTop: "8px",
                  padding: "10px",
                  border:
                    "1px solid #173450",
                  background:
                    "#030914",
                  color: "#dffaff",
                }}
              >
                <option value="ABOVE">
                  Price rises above
                </option>
                <option value="BELOW">
                  Price falls below
                </option>
              </select>

              <input
                name="target_price"
                required
                type="number"
                min="0.01"
                step="any"
                placeholder="Target price"
                style={{
                  width: "100%",
                  marginTop: "8px",
                  padding: "10px",
                  border:
                    "1px solid #173450",
                  background:
                    "#030914",
                  color: "#dffaff",
                }}
              />

              <select
                name="delivery"
                style={{
                  width: "100%",
                  marginTop: "8px",
                  padding: "10px",
                  border:
                    "1px solid #173450",
                  background:
                    "#030914",
                  color: "#dffaff",
                }}
              >
                <option value="BROWSER">
                  Browser
                </option>
                <option value="TELEGRAM">
                  Telegram
                </option>
                <option value="BOTH">
                  Browser + Telegram
                </option>
              </select>

              <button
                type="submit"
                className="selected-time"
                style={{
                  width: "100%",
                  marginTop: "10px",
                }}
              >
                SAVE ALERT
              </button>
            </form>
          </div>
        </section>

        <section
          id="backtest-section"
          className="glass"
          style={{
            marginTop: "12px",
            padding: "18px",
          }}
        >
          <span className="eyebrow">
            BACKTEST LAB
          </span>
          <p
            style={{
              color: "#71869c",
              fontSize: "11px",
              marginTop: "10px",
            }}
          >
            Backtest navigation is active and ready for
            your V2 backtest endpoints.
          </p>
        </section>

        <section
          id="analytics-section"
          className="glass"
          style={{
            marginTop: "12px",
            padding: "18px",
          }}
        >
          <span className="eyebrow">
            ANALYTICS
          </span>
          <p
            style={{
              color: "#71869c",
              fontSize: "11px",
              marginTop: "10px",
            }}
          >
            Analytics navigation is active. This is the
            future home for scanner statistics.
          </p>
        </section>

        <section
          id="settings-section"
          className="glass"
          style={{
            marginTop: "12px",
            padding: "18px",
          }}
        >
          <span className="eyebrow">
            SETTINGS
          </span>
          <p
            style={{
              color: "#71869c",
              fontSize: "11px",
              marginTop: "10px",
            }}
          >
            Settings navigation is active.
          </p>
        </section>

        {watchlistMessage && (
          <div
            style={{
              marginTop: "12px",
              border:
                "1px solid #173450",
              borderRadius: "6px",
              padding: "10px 12px",
              color: "#7af5ff",
              background: "#030914",
              fontSize: "10px",
            }}
          >
            {watchlistMessage}
          </div>
        )}

        {/* ===============================================
            FOOTER
        =============================================== */}

        <footer className="market-feed">

          <strong>

            MARKET FEED
            <i />

          </strong>


          <span>

            Angel One QUOTE
            WebSocket

          </span>


          <span>
            •
          </span>


          <span>

            {stocks.length}
            {" "}
            instruments streaming

          </span>


          <span>
            •
          </span>


          <span>

            {timeframe}
            {" "}
            V2 scanner

          </span>


          <div className="health">

            SYSTEM HEALTH

            <b>

              {status ===
              "LIVE"
                ? "● ONLINE"
                : "● CHECKING"}

            </b>

          </div>

        </footer>

      </section>

    </main>
  );
}


// ==================================================
// HELPERS
// ==================================================

function SignalBadge({
  signal,
  small = false,
}: {
  signal: string;
  small?: boolean;
}) {

  const normalized =
    signal
      .toUpperCase();


  const className =
    normalized === "BUY"
      ? "signal-badge buy"
      : normalized === "SELL"
      ? "signal-badge sell"
      : "signal-badge wait";


  return (
    <span
      className={`${className}${
        small
          ? " signal-small"
          : ""
      }`}
    >

      {normalized}

    </span>
  );
}


function trendClass(
  trend: string
) {

  const value =
    trend
      .toUpperCase();


  if (
    value ===
    "BULLISH"
  ) {

    return "trend-bullish";
  }


  if (
    value ===
    "BEARISH"
  ) {

    return "trend-bearish";
  }


  return "trend-neutral";
}


function formatPrice(
  value:
    number | null | undefined
) {

  if (
    value === null
  ) {

    return "—";
  }


  return `₹${value.toFixed(
    2
  )}`;
}


function MarketCard({
  name,
  value,
  change,
}: {
  name: string;
  value: string;
  change: string;
}) {

  return (
    <div className="index-card">

      <span>
        {name}
      </span>


      <strong>
        {value}
      </strong>


      <small>
        ▲ {change}
      </small>


      <div className="sparkline">

        <i />
        <i />
        <i />
        <i />
        <i />
        <i />
        <i />

      </div>

    </div>
  );
}