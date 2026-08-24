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
import StockLoader from "../../components/StockLoader";
import OverviewPanel from "../../components/dashboard/OverviewPanel";
import ScannerPanel from "../../components/dashboard/ScannerPanel";
import MarketRadarPanel from "../../components/dashboard/MarketRadarPanel";
import BacktestPanel from "../../components/dashboard/BacktestPanel";
import WeatherRainBackground from "../../components/WeatherRainBackground";

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
} & Partial<
  Record<
    ChartTimeframe,
    Candle[]
  >
>;

type InstrumentSearchResult = {
  symbol: string;
  name: string;
  token: string;
  kind: string;
};

type WatchlistItem = {
  symbol: string;
  name: string;
  token: string;
  kind: string;

  last_price?: number | null;
  change_percent?: number | null;
};

type DashboardView =
  | "overview"
  | "radar"
  | "scanner"
  | "watchlist"
  | "portfolio"
  | "alerts"
  | "backtest"
  | "analytics"
  | "settings";

type ChartTimeframe =
  | "15s"
  | "1m"
  | "5m"
  | "15m"
  | "1D"
  | "1W"
  | "1M";

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
  [
    "⌂",
    "OVERVIEW",
    "Market Dashboard",
  ],

  [
    "⌁",
    "MARKET RADAR",
    "Market Opportunities",
  ],

  [
    "◈",
    "AI SCANNER",
    "Signal Analysis",
  ],

  [
    "♡",
    "WATCHLIST",
    "Live Markets",
  ],

  [
    "▣",
    "PORTFOLIO",
    "Holdings & P&L",
  ],

  [
    "▧",
    "BACKTEST",
    "Strategy Lab",
  ],

  [
    "⚙",
    "SETTINGS",
    "Preferences",
  ],
];

export default function Dashboard() {

  const [
    stocks,
    setStocks,
  ] = useState<LiveStock[]>([]);

  const [
    watchlistItems,
    setWatchlistItems,
  ] = useState<
    WatchlistItem[]
  >([]);


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
  ] = useState<Date | null>(null);

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
  ] = useState<ChartTimeframe>(
    "15m"
  );

  const scannerTimeframe:
    "1m" |
    "5m" |
    "15m" =
    timeframe === "1m"
      ? "1m"
      : timeframe === "5m"
        ? "5m"
        : timeframe === "15m"
          ? "15m"
          : timeframe === "15s"
            ? "1m"
            : "15m";

  const [
    preferencesLoaded,
    setPreferencesLoaded,
  ] = useState(false);

  const [
    chartData,
    setChartData,
  ] = useState<Candle[]>([]);

  const [
    chartLoading,
    setChartLoading,
  ] = useState(false);

  const [
    fullScreenChart,
    setFullScreenChart,
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
  // TRACKED UNIVERSE
  // DATABASE WATCHLIST = SOURCE OF TRUTH
  // ==================================================

  const trackedSymbols =
    useMemo(
      () =>
        watchlistItems.map(
          (
            item
          ) =>
            item.symbol
              .trim()
              .toUpperCase()
        ),
      [
        watchlistItems,
      ]
    );



  // ==================================================
  // CLOCK
  // ==================================================

  useEffect(() => {
    setClock(new Date());

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

  useEffect(() => {
    const savedTimeframe =
      window.localStorage.getItem(
        "nexus_default_timeframe"
      );

    console.log(
      "[NEXUS] Saved timeframe:",
      savedTimeframe
    );

    if (
      savedTimeframe === "1m" ||
      savedTimeframe === "5m" ||
      savedTimeframe === "15m"
    ) {
      setTimeframe(savedTimeframe);
    }

    setPreferencesLoaded(true);
  }, []);

  useEffect(() => {
    if (
      !fullScreenChart
    ) {
      return;
    }

    const previousOverflow =
      document.body.style
        .overflow;

    document.body.style
      .overflow =
      "hidden";

    function handleKeyDown(
      event: KeyboardEvent
    ) {
      if (
        event.key ===
        "Escape"
      ) {
        setFullScreenChart(
          false
        );
      }
    }

    window.addEventListener(
      "keydown",
      handleKeyDown
    );

    return () => {
      document.body.style
        .overflow =
        previousOverflow;

      window.removeEventListener(
        "keydown",
        handleKeyDown
      );
    };
  }, [
    fullScreenChart,
  ]);

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
    console.log(
      "[CANDLE EFFECT]",
      {
        selected,
        authenticated,
        timeframe,
      }
    );

    if (
      !selected ||
      authenticated !== true
    ) {
      setChartData([]);
      return;
    }

    let active = true;

    async function loadCandles() {
      try {
        setChartLoading(true);

        const response =
          await fetch(
            `${API_BASE}/api/live/candles/${encodeURIComponent(
              selected
            )}?interval=${encodeURIComponent(
              timeframe
            )}`,
            {
              credentials: "include",
              cache: "no-store",
            }
          );

        if (response.status === 401) {
          if (active) {
            setAuthenticated(false);
            setChartData([]);
          }

          return;
        }

        if (!response.ok) {
          throw new Error(
            `Candle request failed: ${response.status
            } ${await response.text()
            }`
          );
        }

        const data:
          LiveCandleResponse =
          await response.json();

        if (!active) {
          return;
        }

        const candles =
          data[timeframe] ?? [];

        console.log(
          "[NEXUS candles]",
          selected,
          timeframe,
          candles.length
        );

        setChartData(candles);
      } catch (error) {
        console.error(
          "Unable to load candles:",
          error
        );

        if (active) {
          setChartData([]);
        }
      } finally {
        if (active) {
          setChartLoading(false);
        }
      }
    }

    void loadCandles();

    const refreshMs =
      timeframe === "15s"
        ? 5000
        : timeframe === "1m"
          ? 60000
          : timeframe === "5m"
            ? 120000
            : timeframe === "15m"
              ? 180000
              : 300000;

    const timer =
      window.setInterval(
        () => {
          void loadCandles();
        },
        refreshMs
      );

    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [
    authenticated,
    selected,
    timeframe,
  ]);


  // ==================================================
  // DATABASE WATCHLIST + LIVE MARKET DATA
  //
  // Database decides WHICH stocks are tracked.
  // WebSocket only enriches them with live data.
  // ==================================================

  const watchlistStocks =
    useMemo(
      () => {

        const liveBySymbol =
          new Map(
            stocks.map(
              (
                stock
              ) => [
                  stock.symbol
                    .trim()
                    .toUpperCase(),
                  stock,
                ]
            )
          );


        return watchlistItems.map(
          (
            item
          ) => {

            const symbol =
              item.symbol
                .trim()
                .toUpperCase();


            const live =
              liveBySymbol.get(
                symbol
              );


            const merged:
              LiveStock = {

              symbol,

              token:
                live?.token ||
                item.token,

              ltp:
                typeof live?.ltp ===
                  "number"

                  ? live.ltp

                  : typeof item.last_price ===
                    "number"

                    ? item.last_price

                    : 0,

              volume:
                live?.volume ??
                null,

              exchange_timestamp:
                live?.exchange_timestamp ??
                null,

              received_at:
                live?.received_at,

            };


            return merged;

          }
        );

      },
      [
        stocks,
        watchlistItems,
      ]
    );


  const sortedWatchlistStocks =
    useMemo(
      () =>
        [
          ...watchlistStocks,
        ].sort(
          (
            first,
            second
          ) =>
            first.symbol.localeCompare(
              second.symbol
            )
        ),
      [
        watchlistStocks,
      ]
    );

  // ==================================================
  // TRACKED SCANNER UNIVERSE
  //
  // IMPORTANT:
  // Database Watchlist is the source of truth.
  //
  // WebSocket data is ONLY used for live prices.
  // A stock does not need to receive a live tick
  // before the AI Scanner can scan it.
  // ==================================================

  const scannerSymbolsKey =
    useMemo(
      () =>
        [
          ...trackedSymbols,
        ]
          .filter(
            Boolean
          )
          .sort()
          .join(","),
      [
        trackedSymbols,
      ]
    );

  // ==================================================
  // PRUNE STALE SCANNER RESULTS
  //
  // Database Watchlist is the source of truth.
  // Scanner results must never survive after
  // a symbol leaves the tracked universe.
  // ==================================================

  useEffect(
    () => {

      const allowedSymbols =
        new Set(
          trackedSymbols
        );


      setScanners(
        (
          current
        ) => {

          let changed =
            false;


          const next:
            Record<
              string,
              ScannerResult
            > = {};


          for (
            const [
              symbol,
              result,
            ]
            of Object.entries(
              current
            )
          ) {

            const normalized =
              symbol
                .trim()
                .toUpperCase();


            if (
              allowedSymbols.has(
                normalized
              )
            ) {

              next[
                normalized
              ] =
                result;

            } else {

              changed =
                true;

            }

          }


          return changed
            ? next
            : current;

        }
      );

    },
    [
      trackedSymbols,
    ]
  );

  // ==================================================
  // V2 SCANNER
  // ==================================================

  useEffect(
    () => {

      if (
        !preferencesLoaded ||
        !scannerSymbolsKey ||
        authenticated !== true
      ) {

        return;

      }


      let active =
        true;


      let nextScanTimer:
        number | null =
        null;


      function sleep(
        milliseconds:
          number
      ) {

        return new Promise<void>(
          (
            resolve
          ) => {

            window.setTimeout(
              resolve,
              milliseconds
            );

          }
        );

      }


      async function scanUniverse() {


        const symbols =
          scannerSymbolsKey
            .split(",")
            .map(
              (
                symbol
              ) =>
                symbol
                  .trim()
                  .toUpperCase()
            )
            .filter(
              Boolean
            );


        if (
          symbols.length ===
          0
        ) {

          return;

        }


        if (
          active
        ) {

          setScannerLoading(
            true
          );

        }


        try {


          for (
            const symbol
            of symbols
          ) {


            if (
              !active
            ) {

              return;

            }


            try {


              const response =
                await fetch(
                  `${API_BASE}/api/v2/scanner/${encodeURIComponent(
                    symbol
                  )}?interval=${scannerTimeframe}`,
                  {

                    credentials:
                      "include",

                    cache:
                      "no-store",

                  }
                );


              if (
                response.status ===
                401
              ) {


                if (
                  active
                ) {

                  setAuthenticated(
                    false
                  );

                }


                return;

              }


              if (
                !response.ok
              ) {


                const body =
                  await response
                    .json()
                    .catch(
                      () => ({})
                    );


                throw new Error(
                  body.detail ||
                  `${symbol}: scanner failed`
                );

              }


              const data:
                ScannerResult =
                await response
                  .json();


              if (
                !active
              ) {

                return;

              }


              setScanners(
                (
                  previous
                ) => ({

                  ...previous,

                  [
                    data.symbol
                      .toUpperCase()
                  ]:
                    data,

                })
              );


            } catch (
            error
            ) {

              const errorMessage =
                error instanceof Error
                  ? error.message
                  : String(
                    error
                  );


              const isCandleIssue =
                errorMessage
                  .toLowerCase()
                  .includes(
                    "candle"
                  );


              if (
                isCandleIssue
              ) {

                /*
                 * Insufficient candles are
                 * not an application crash.
                 *
                 * This can happen with
                 * newly listed, invalid,
                 * suspended or temporarily
                 * unavailable instruments.
                 */
                console.warn(
                  `[NEXUS scanner] skipped ${symbol}: ${errorMessage}`
                );

              } else {

                console.error(
                  `[NEXUS scanner] ${symbol}`,
                  error
                );

              }

            }


            if (
              active
            ) {

              /*
               * Keep Angel One
               * scanner requests
               * spaced apart.
               */
              await sleep(
                2500
              );

            }


          }


        } finally {


          if (
            active
          ) {

            setScannerLoading(
              false
            );

          }


        }


      }


      async function runScannerCycle() {


        await scanUniverse();


        if (
          !active
        ) {

          return;

        }


        /*
         * Start another complete
         * scan after one minute.
         *
         * setTimeout is used
         * instead of setInterval
         * so scans cannot overlap.
         */
        nextScanTimer =
          window.setTimeout(
            () => {

              void runScannerCycle();

            },
            60000
          );


      }


      void runScannerCycle();


      return () => {


        active =
          false;


        if (
          nextScanTimer !==
          null
        ) {

          window.clearTimeout(
            nextScanTimer
          );

        }


      };


    },
    [
      authenticated,
      scannerTimeframe,
      scannerSymbolsKey,
      preferencesLoaded,
    ]
  );

  // ==================================================
  // DATABASE WATCHLIST
  // ==================================================

  async function loadWatchlist() {

    try {

      const response =
        await fetch(
          `${API_BASE}/api/watchlist`,
          {
            credentials:
              "include",

            cache:
              "no-store",
          }
        );


      if (
        !response.ok
      ) {

        throw new Error(
          await response.text()
        );

      }


      const data:
        WatchlistItem[] =
        await response.json();


      setWatchlistItems(
        data.map(
          (
            item
          ) => ({
            ...item,

            symbol:
              item.symbol
                .trim()
                .toUpperCase(),
          })
        )
      );


    } catch (
    error
    ) {

      console.error(
        "Could not load database watchlist:",
        error
      );

    }
  }

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

    if (
      authenticated !==
      true
    ) {
      return;
    }


    void loadWatchlist();

    void loadPortfolio();

    void loadAlerts();

  }, [
    authenticated,
  ]);


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

      const savedHolding:
        PortfolioHolding =
        await response.json();

      setHoldings(
        (current) => {
          const existingIndex =
            current.findIndex(
              (item) =>
                item.symbol ===
                savedHolding.symbol
            );

          if (
            existingIndex === -1
          ) {
            return [
              savedHolding,
              ...current,
            ];
          }

          const next = [
            ...current,
          ];

          next[
            existingIndex
          ] =
            savedHolding;

          return next;
        }
      );

      event.currentTarget.reset();

      setPortfolioMessage(
        `${savedHolding.symbol} saved successfully`
      );

      setActiveView(
        "portfolio"
      );

      window.setTimeout(
        () => {
          document
            .getElementById(
              "portfolio-section"
            )
            ?.scrollIntoView({
              behavior:
                "smooth",
              block:
                "start",
            });
        },
        0
      );

      // Re-sync with backend after updating the UI immediately.
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

    setWatchlistMessage(
      ""
    );


    const symbol =
      item.symbol
        .trim()
        .toUpperCase();


    try {

      const response =
        await fetch(
          `${API_BASE}/api/watchlist`,
          {
            method:
              "POST",

            credentials:
              "include",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify(
                item
              ),
          }
        );


      // ==========================================
      // ALREADY EXISTS
      //
      // Treat this as tracked, not as failure.
      // Backend also re-registers it with
      // the live tracker.
      // ==========================================

      if (
        response.status ===
        409
      ) {

        setWatchlistMessage(
          `${symbol} is already in the watchlist`
        );

        setWatchlistItems(
          (
            current
          ) => {

            const exists =
              current.some(
                (
                  existing
                ) =>
                  existing.symbol
                    .trim()
                    .toUpperCase() ===
                  symbol
              );


            if (
              exists
            ) {
              return current;
            }


            return [
              ...current,
              {
                symbol,
                name:
                  item.name,

                token:
                  item.token,

                kind:
                  item.kind,

                last_price:
                  null,

                change_percent:
                  null,
              },
            ];

          }
        );
        setStocks(
          (
            current
          ) => {

            const exists =
              current.some(
                (
                  stock
                ) =>
                  stock.symbol
                    .toUpperCase() ===
                  symbol
              );


            if (
              exists
            ) {
              return current;
            }


            return [
              ...current,
              {
                symbol:
                  symbol,

                token:
                  item.token,

                ltp:
                  0,

                volume:
                  null,

                received_at:
                  new Date()
                    .toISOString(),
              },
            ];

          }
        );


        setSelected(
          symbol
        );


        setSearchQuery(
          ""
        );

        setSearchResults(
          []
        );

        setSearchOpen(
          false
        );


        setFullScreenChart(
          false
        );


        setWsVersion(
          (
            current
          ) =>
            current + 1
        );


        setActiveView(
          "watchlist"
        );


        return;

      }


      // ==========================================
      // REAL ERROR
      // ==========================================

      if (
        !response.ok
      ) {

        const body =
          await response
            .json()
            .catch(
              () => ({})
            );


        throw new Error(
          body.detail ||
          "Could not add stock"
        );

      }


      // ==========================================
      // SUCCESS
      // ==========================================

      const saved:
        {
          symbol: string;
          name?: string;
          token?: string;
          kind?: string;
          last_price?: number;
          change_percent?: number;
        } =
        await response.json();


      const savedSymbol =
        (
          saved.symbol ||
          symbol
        )
          .trim()
          .toUpperCase();
      setWatchlistItems(
        (
          current
        ) => {

          const nextItem:
            WatchlistItem = {

            symbol:
              savedSymbol,

            name:
              saved.name ||
              item.name,

            token:
              saved.token ||
              item.token,

            kind:
              saved.kind ||
              item.kind,

            last_price:
              typeof saved.last_price ===
                "number"

                ? saved.last_price

                : null,

            change_percent:
              typeof saved.change_percent ===
                "number"

                ? saved.change_percent

                : null,
          };


          const index =
            current.findIndex(
              (
                existing
              ) =>
                existing.symbol
                  .trim()
                  .toUpperCase() ===
                savedSymbol
            );


          if (
            index ===
            -1
          ) {

            return [
              ...current,
              nextItem,
            ];

          }


          const next = [
            ...current,
          ];


          next[
            index
          ] =
            nextItem;


          return next;

        }
      );

      // ==========================================
      // UPDATE UI IMMEDIATELY
      // ==========================================

      setStocks(
        (
          current
        ) => {

          const index =
            current.findIndex(
              (
                stock
              ) =>
                stock.symbol
                  .toUpperCase() ===
                savedSymbol
            );


          const liveStock:
            LiveStock = {

            symbol:
              savedSymbol,

            token:
              saved.token ||
              item.token,

            ltp:
              typeof saved.last_price ===
                "number"

                ? saved.last_price

                : 0,

            volume:
              null,

            received_at:
              new Date()
                .toISOString(),
          };


          if (
            index ===
            -1
          ) {

            return [
              ...current,
              liveStock,
            ];

          }


          const next = [
            ...current,
          ];


          next[
            index
          ] = {
            ...next[
            index
            ],
            ...liveStock,
          };


          return next;

        }
      );


      setWatchlistMessage(
        `${savedSymbol} added to watchlist`
      );


      setSelected(
        savedSymbol
      );


      setSearchQuery(
        ""
      );

      setSearchResults(
        []
      );

      setSearchOpen(
        false
      );


      setFullScreenChart(
        false
      );


      // Reconnect so the frontend receives
      // the newly subscribed SmartAPI stock.

      setWsVersion(
        (
          current
        ) =>
          current + 1
      );


      // Show Watchlist immediately after ADD.

      setActiveView(
        "watchlist"
      );


    } catch (
    error
    ) {

      const message =
        error instanceof
          Error

          ? error.message

          : "Could not add stock";


      console.error(
        "Could not add stock to watchlist:",
        message
      );


      setWatchlistMessage(
        message
      );


      // Important:
      // MarketRadarPanel must know the ADD
      // really failed, otherwise it may mark
      // the stock TRACKED incorrectly.

      throw error;

    }

  }

  async function removeInstrumentFromWatchlist(
    symbol: string
  ) {

    const normalized =
      symbol
        .trim()
        .toUpperCase();


    setWatchlistMessage(
      ""
    );


    try {

      const response =
        await fetch(
          `${API_BASE}/api/watchlist/${encodeURIComponent(
            normalized
          )}`,
          {
            method:
              "DELETE",

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


      if (
        !response.ok &&
        response.status !==
        204
      ) {

        throw new Error(
          await response.text()
        );

      }


      // ==========================================
      // REMOVE FROM DATABASE-BACKED UI STATE
      // ==========================================

      setWatchlistItems(
        (
          current
        ) =>
          current.filter(
            (
              item
            ) =>
              item.symbol
                .trim()
                .toUpperCase() !==
              normalized
          )
      );


      // ==========================================
      // REMOVE STALE LIVE ENTRY
      // ==========================================

      setStocks(
        (
          current
        ) =>
          current.filter(
            (
              stock
            ) =>
              stock.symbol
                .trim()
                .toUpperCase() !==
              normalized
          )
      );


      // ==========================================
      // REMOVE OLD SCANNER RESULT
      // ==========================================

      setScanners(
        (
          current
        ) => {

          const next = {
            ...current,
          };


          delete next[
            normalized
          ];


          return next;

        }
      );


      // ==========================================
      // CLEAR SELECTION IF REMOVED STOCK
      // ==========================================

      setSelected(
        (
          current
        ) =>
          current ===
            normalized

            ? ""

            : current
      );


      setFullScreenChart(
        false
      );


      // Reconnect market WebSocket using
      // updated backend subscriptions.

      setWsVersion(
        (
          current
        ) =>
          current + 1
      );


      setWatchlistMessage(
        `${normalized} removed from watchlist`
      );


    } catch (
    error
    ) {

      const message =
        error instanceof Error
          ? error.message
          : "Could not remove stock";


      console.error(
        "Could not remove stock from watchlist:",
        message
      );


      setWatchlistMessage(
        message
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

      OVERVIEW:
        "overview",

      "MARKET RADAR":
        "radar",

      "AI SCANNER":
        "scanner",

      WATCHLIST:
        "watchlist",

      PORTFOLIO:
        "portfolio",

      BACKTEST:
        "backtest",

      SETTINGS:
        "settings",
    };


    const nextView =
      map[
      title
      ];


    if (
      !nextView
    ) {
      return;
    }


    setActiveView(
      nextView
    );
  }

  function openFullScreenChart(
    symbol: string
  ) {
    setSelected(
      symbol
    );

    setFullScreenChart(
      true
    );
  }

  // ==================================================
  // SELECTED STOCK
  // ==================================================

  const selectedStock =
    useMemo(
      () =>
        watchlistStocks.find(
          (
            stock
          ) =>
            stock.symbol ===
            selected
        ),
      [
        watchlistStocks,
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
  {
    fullScreenChart && (

      <div
        style={{
          position:
            "fixed",

          inset:
            0,

          zIndex:
            99999,

          display:
            "flex",

          flexDirection:
            "column",

          background:
            "#040a06",

          overflow:
            "hidden",
        }}
      >

        {/* ==========================================
        FULLSCREEN HEADER
    ========================================== */}

        <div
          style={{
            display:
              "flex",

            alignItems:
              "center",

            justifyContent:
              "space-between",

            gap:
              "18px",

            padding:
              "14px 20px",

            borderBottom:
              "1px solid #163425",

            background:
              "#07100b",
          }}
        >

          {/* LEFT */}

          <div
            style={{
              display:
                "flex",

              alignItems:
                "center",

              gap:
                "18px",
            }}
          >

            <button
              type="button"
              onClick={
                () =>
                  setFullScreenChart(
                    false
                  )
              }
              style={{
                border:
                  "1px solid #24533c",

                borderRadius:
                  "7px",

                background:
                  "#0a1710",

                color:
                  "#9ee6bc",

                padding:
                  "8px 13px",

                cursor:
                  "pointer",

                fontSize:
                  "11px",

                fontWeight:
                  700,
              }}
            >
              ← BACK
            </button>


            <div>

              <div
                style={{
                  color:
                    "#5f8370",

                  fontSize:
                    "9px",

                  fontWeight:
                    700,

                  letterSpacing:
                    ".15em",
                }}
              >
                NSE • LIVE CHART
              </div>

              <div
                style={{
                  display:
                    "flex",

                  alignItems:
                    "baseline",

                  gap:
                    "10px",

                  marginTop:
                    "3px",
                }}
              >

                <strong
                  style={{
                    color:
                      "#ffffff",

                    fontSize:
                      "22px",
                  }}
                >
                  {
                    selected ||
                    "SELECT STOCK"
                  }
                </strong>

                <span
                  style={{
                    color:
                      "#65e39a",

                    fontSize:
                      "18px",

                    fontWeight:
                      700,
                  }}
                >
                  {
                    selectedStock
                      ? `₹${selectedStock.ltp.toFixed(
                        2
                      )}`
                      : "—"
                  }
                </span>

              </div>

            </div>

          </div>


          {/* RIGHT */}

          <div
            style={{
              display:
                "flex",

              alignItems:
                "center",

              gap:
                "8px",

              flexWrap:
                "wrap",

              justifyContent:
                "flex-end",
            }}
          >

            {(
              [
                "15s",
                "1m",
                "5m",
                "15m",
                "1D",
                "1W",
                "1M",
              ] as ChartTimeframe[]
            ).map(
              (
                value
              ) => (

                <button
                  key={
                    value
                  }
                  type="button"
                  onClick={
                    () =>
                      setTimeframe(
                        value
                      )
                  }
                  style={{
                    border:
                      timeframe ===
                        value
                        ? "1px solid #37d67a"
                        : "1px solid #1a3c2a",

                    borderRadius:
                      "6px",

                    background:
                      timeframe ===
                        value
                        ? "rgba(55,214,122,.12)"
                        : "#08120c",

                    color:
                      timeframe ===
                        value
                        ? "#7df0aa"
                        : "#728879",

                    padding:
                      "7px 11px",

                    cursor:
                      "pointer",

                    fontSize:
                      "10px",

                    fontWeight:
                      700,
                  }}
                >
                  {
                    value
                  }
                </button>

              )
            )}

          </div>

        </div>


        {/* ==========================================
        SIGNAL STRIP
    ========================================== */}

        {selectedScanner && (

          <div
            style={{
              display:
                "flex",

              alignItems:
                "center",

              gap:
                "16px",

              padding:
                "8px 20px",

              borderBottom:
                "1px solid #10281b",

              background:
                "#050d08",

              fontSize:
                "10px",

              color:
                "#809487",
            }}
          >

            <SignalBadge
              signal={
                selectedScanner
                  .signal
              }
            />

            <span>
              TREND{" "}
              <strong>
                {
                  selectedScanner
                    .trend
                }
              </strong>
            </span>

            <span>
              CONFIDENCE{" "}
              <strong>
                {
                  selectedScanner
                    .analysis
                    .confidence
                }
                %
              </strong>
            </span>

            <span>
              GRADE{" "}
              <strong>
                {
                  selectedScanner
                    .grade
                }
              </strong>
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


        {/* ==========================================
        CHART
    ========================================== */}

        <div
          style={{
            flex:
              1,

            minHeight:
              0,

            padding:
              "10px 18px 0",

            overflow:
              "hidden",
          }}
        >

          {chartLoading ? (

            <StockLoader />

          ) : chartData.length >
            0 ? (

            <StockChart
              data={
                chartData
              }
              interval={
                timeframe
              }
              height={
                680
              }
            />

          ) : (

            <div
              style={{
                height:
                  "100%",

                display:
                  "flex",

                alignItems:
                  "center",

                justifyContent:
                  "center",

                color:
                  "#63766a",

                fontSize:
                  "12px",
              }}
            >
              No {timeframe} candles
              available for{" "}
              {selected}
            </div>

          )}

        </div>


        {/* ==========================================
        FOOTER
    ========================================== */}

        <div
          style={{
            display:
              "flex",

            alignItems:
              "center",

            justifyContent:
              "space-between",

            gap:
              "20px",

            padding:
              "9px 20px",

            borderTop:
              "1px solid #163425",

            background:
              "#07100b",

            color:
              "#667c6e",

            fontSize:
              "9px",

            fontWeight:
              700,

            letterSpacing:
              ".08em",
          }}
        >

          <span>
            TIMEFRAME{" "}
            <strong
              style={{
                color:
                  "#a5e8bd",
              }}
            >
              {
                timeframe
              }
            </strong>
          </span>

          <span>
            CANDLES{" "}
            <strong
              style={{
                color:
                  "#a5e8bd",
              }}
            >
              {
                chartData.length
              }
            </strong>
          </span>

          <span>
            EMA{" "}
            <strong
              style={{
                color:
                  "#a5e8bd",
              }}
            >
              EMA 20
            </strong>
          </span>

          <span>
            ESC TO CLOSE
          </span>

        </div>

      </div>

    )
  }
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
      <WeatherRainBackground />

      {/* ==========================================
        FULL SCREEN STOCK CHART
    ========================================== */}

      {fullScreenChart && (

        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 99999,
            display: "flex",
            flexDirection: "column",
            background: "#040a06",
            overflow: "hidden",
          }}
        >

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "18px",
              padding: "14px 20px",
              borderBottom: "1px solid #163425",
              background: "#07100b",
            }}
          >

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "18px",
              }}
            >

              <button
                type="button"
                onClick={() =>
                  setFullScreenChart(false)
                }
                style={{
                  border: "1px solid #24533c",
                  borderRadius: "7px",
                  background: "#0a1710",
                  color: "#9ee6bc",
                  padding: "8px 13px",
                  cursor: "pointer",
                  fontSize: "11px",
                  fontWeight: 700,
                }}
              >
                ← BACK
              </button>

              <div>

                <div
                  style={{
                    color: "#5f8370",
                    fontSize: "9px",
                    fontWeight: 700,
                    letterSpacing: ".15em",
                  }}
                >
                  NSE • LIVE CHART
                </div>

                <div
                  style={{
                    display: "flex",
                    alignItems: "baseline",
                    gap: "10px",
                    marginTop: "3px",
                  }}
                >

                  <strong
                    style={{
                      color: "#ffffff",
                      fontSize: "22px",
                    }}
                  >
                    {selected || "SELECT STOCK"}
                  </strong>

                  <span
                    style={{
                      color: "#65e39a",
                      fontSize: "18px",
                      fontWeight: 700,
                    }}
                  >
                    {selectedStock
                      ? `₹${selectedStock.ltp.toFixed(2)}`
                      : "—"}
                  </span>

                </div>

              </div>

            </div>


            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                flexWrap: "wrap",
              }}
            >

              {(
                [
                  "15s",
                  "1m",
                  "5m",
                  "15m",
                  "1D",
                  "1W",
                  "1M",
                ] as ChartTimeframe[]
              ).map((value) => (

                <button
                  key={value}
                  type="button"
                  onClick={() =>
                    setTimeframe(value)
                  }
                  style={{
                    border:
                      timeframe === value
                        ? "1px solid #37d67a"
                        : "1px solid #1a3c2a",

                    borderRadius: "6px",

                    background:
                      timeframe === value
                        ? "rgba(55,214,122,.12)"
                        : "#08120c",

                    color:
                      timeframe === value
                        ? "#7df0aa"
                        : "#728879",

                    padding: "7px 11px",
                    cursor: "pointer",
                    fontSize: "10px",
                    fontWeight: 700,
                  }}
                >
                  {value}
                </button>

              ))}

            </div>

          </div>


          {selectedScanner && (

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "16px",
                padding: "8px 20px",
                borderBottom: "1px solid #10281b",
                background: "#050d08",
                fontSize: "10px",
                color: "#809487",
              }}
            >

              <SignalBadge
                signal={selectedScanner.signal}
              />

              <span>
                TREND{" "}
                <strong>
                  {selectedScanner.trend}
                </strong>
              </span>

              <span>
                CONFIDENCE{" "}
                <strong>
                  {
                    selectedScanner.analysis
                      .confidence
                  }
                  %
                </strong>
              </span>

              <span>
                GRADE{" "}
                <strong>
                  {selectedScanner.grade}
                </strong>
              </span>

            </div>

          )}


          <div
            style={{
              flex: 1,
              minHeight: 0,
              padding: "10px 18px 0",
              overflow: "hidden",
            }}
          >

            {chartLoading ? (

              <StockLoader />

            ) : chartData.length > 0 ? (

              <StockChart
                data={chartData}
                interval={timeframe}
                height={680}
              />

            ) : (

              <div
                style={{
                  height: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#63766a",
                }}
              >
                No {timeframe} candles available for{" "}
                {selected}
              </div>

            )}

          </div>


          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              padding: "9px 20px",
              borderTop: "1px solid #163425",
              background: "#07100b",
              color: "#667c6e",
              fontSize: "9px",
            }}
          >

            <span>
              TIMEFRAME{" "}
              <strong>
                {timeframe}
              </strong>
            </span>

            <span>
              CANDLES{" "}
              <strong>
                {chartData.length}
              </strong>
            </span>

            <span>
              EMA 20
            </span>

            <span>
              ESC TO CLOSE
            </span>

          </div>

        </div>

      )}

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

                OVERVIEW:
                  "overview",

                "MARKET RADAR":
                  "radar",

                "AI SCANNER":
                  "scanner",

                WATCHLIST:
                  "watchlist",

                PORTFOLIO:
                  "portfolio",

                BACKTEST:
                  "backtest",

                SETTINGS:
                  "settings",
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
                ? clock.toLocaleTimeString(
                  "en-IN"
                )
                : "--:--:--"}
            </strong>

            <span>
              {clock
                ? clock
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
                  .toUpperCase()
                : "---"}
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



        {activeView === "overview" && (
          <OverviewPanel
            stocks={stocks}
            holdings={holdings}
            scanners={scanners}
            status={status}
            lastMarketUpdate={lastMarketUpdate}
            onOpenScanner={() => setActiveView("scanner")}
            onOpenPortfolio={() => setActiveView("portfolio")}
            onSelectSymbol={(sym) => {
              setSelected(sym);
              setActiveView("watchlist");
            }}
          />
        )}

        {activeView === "backtest" && (

          <BacktestPanel
            apiBase={
              API_BASE
            }

            symbols={
              trackedSymbols
            }

            defaultSymbol={
              selected ||
              trackedSymbols[0] ||
              ""
            }

            defaultTimeframe={
              scannerTimeframe
            }

            onOpenChart={
              (
                symbol
              ) => {

                openFullScreenChart(
                  symbol
                );

              }
            }
          />

        )}

        {/* ==========================================
    MARKET RADAR
========================================== */}

        {activeView === "radar" && (

          <MarketRadarPanel
            apiBase={API_BASE}
            liveStocks={stocks}
            trackedSymbols={
              trackedSymbols
            }
            scanners={scanners}

            onOpenStock={(symbol) => {
              openFullScreenChart(
                symbol
              );
            }}

            onAddToWatchlist={
              addInstrumentToWatchlist
            }
          />

        )}

        {/* ===============================================
            TOP CARDS
        =============================================== */}




        {/* ===============================================
            CHART + WATCHLIST
        =============================================== */}

        {activeView === "watchlist" && (
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


                <div
                  className="timeframes"
                  style={{
                    display:
                      "flex",

                    alignItems:
                      "center",

                    gap:
                      "8px",
                  }}
                >
                  <span
                    style={{
                      color:
                        "#71869c",

                      fontSize:
                        "9px",

                      fontWeight:
                        700,

                      letterSpacing:
                        ".08em",
                    }}
                  >
                    TIMEFRAME
                  </span>

                  <select
                    value={
                      timeframe
                    }

                    onChange={
                      (
                        event
                      ) =>
                        setTimeframe(
                          event.target
                            .value as
                          ChartTimeframe
                        )
                    }

                    style={{
                      minWidth:
                        "135px",

                      padding:
                        "8px 11px",

                      border:
                        "1px solid #1f4534",

                      borderRadius:
                        "6px",

                      outline:
                        "none",

                      background:
                        "#07100b",

                      color:
                        "#dff8e9",

                      fontSize:
                        "10px",

                      fontWeight:
                        700,

                      cursor:
                        "pointer",
                    }}
                  >
                    <option value="15s">
                      15 Seconds
                    </option>

                    <option value="1m">
                      1 Minute
                    </option>

                    <option value="5m">
                      5 Minutes
                    </option>

                    <option value="15m">
                      15 Minutes
                    </option>

                    <option value="1D">
                      1 Day
                    </option>

                    <option value="1W">
                      1 Week
                    </option>

                    <option value="1M">
                      1 Month
                    </option>
                  </select>
                </div>

              </div>


              <div className="future-chart real-chart">

                {chartLoading ? (

                  <StockLoader />

                ) : chartData.length > 0 ? (

                  <StockChart
                    data={chartData}
                    interval={timeframe}
                  />

                ) : (

                  <div className="chart-message">

                    <div className="pulse-line" />

                    <strong>
                      WAITING FOR CANDLES
                    </strong>

                    <span>
                      No {timeframe} candles available
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
                  {watchlistStocks.length}
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

                {sortedWatchlistStocks.length ===
                  0 ? (

                  <div className="waiting">

                    Waiting for
                    Angel One live
                    market data...

                  </div>

                ) : (

                  sortedWatchlistStocks.map(
                    (stock) => {

                      const scanner =
                        scanners[
                        stock.symbol
                        ];


                      return (

                        <div
                          key={
                            stock.symbol
                          }
                          style={{
                            display:
                              "grid",

                            gridTemplateColumns:
                              "1fr auto",

                            gap:
                              "6px",

                            alignItems:
                              "stretch",
                          }}
                        >

                          {/* ==========================================
      OPEN STOCK / CHART
    ========================================== */}

                          <button
                            type="button"

                            className={
                              stock.symbol ===
                                selected

                                ? "watch-row selected-stock"

                                : "watch-row"
                            }

                            onClick={
                              () =>
                                openFullScreenChart(
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


                          {/* ==========================================
      REMOVE FROM WATCHLIST
    ========================================== */}

                          <button
                            type="button"

                            aria-label={
                              `Remove ${stock.symbol} from watchlist`
                            }

                            title={
                              `Remove ${stock.symbol}`
                            }

                            onClick={
                              () => {
                                void removeInstrumentFromWatchlist(
                                  stock.symbol
                                );
                              }
                            }

                            style={{
                              border:
                                "1px solid rgba(239,68,68,.32)",

                              borderRadius:
                                "6px",

                              background:
                                "rgba(239,68,68,.08)",

                              color:
                                "#ff8c8c",

                              padding:
                                "0 10px",

                              minWidth:
                                "64px",

                              cursor:
                                "pointer",

                              fontSize:
                                "9px",

                              fontWeight:
                                800,

                              letterSpacing:
                                ".06em",
                            }}
                          >
                            REMOVE
                          </button>

                        </div>

                      );
                    }
                  )

                )}

              </div>

            </div>

          </section>
        )}


        {/* ===============================================
            AI AREA
        =============================================== */}

        {activeView === "scanner" && (
          <ScannerPanel
            stocks={stocks}
            scanners={scanners}
            selected={selected}
            scannerLoading={scannerLoading}
            status={status}
            lastMarketUpdate={lastMarketUpdate}
            onSelectSymbol={(symbol: string) => {
              setSelected(symbol);
            }}
            onOpenChart={(
              symbol: string
            ) => {

              openFullScreenChart(
                symbol
              );

            }}
          />
        )}

        {activeView === "portfolio" && (
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
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent:
                    "space-between",
                  alignItems:
                    "center",
                  marginBottom:
                    "8px",
                  color: "#71869c",
                  fontSize: "10px",
                }}
              >
                <span>
                  HOLDINGS
                </span>
                <span>
                  {holdings.length} stock{holdings.length === 1 ? "" : "s"}
                </span>
              </div>

              {holdings.length === 0 ? (
                <div
                  style={{
                    padding:
                      "16px 0",
                    color:
                      "#71869c",
                    fontSize:
                      "11px",
                  }}
                >
                  No holdings loaded yet.
                </div>
              ) : (
                <div
                  style={{
                    overflowX:
                      "auto",
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
              )}
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


        )}

        {activeView === "alerts" && (
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


        )}


        {activeView === "analytics" && (
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


        )}

        {activeView === "settings" && (
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


        )}

        {activeView === "watchlist" && watchlistMessage && (
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
      className={`${className}${small
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
  value: number | null | undefined
) {
  if (value == null) {
    return "—";
  }

  return `₹${value.toFixed(2)}`;
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