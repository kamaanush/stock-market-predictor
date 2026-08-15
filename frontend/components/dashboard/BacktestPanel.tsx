"use client";

import {
  FormEvent,
  useEffect,
  useMemo,
  useState,
} from "react";

import styles from "./BacktestPanel.module.css";

type BacktestTrade = {
  symbol: string;
  timeframe: string;
  signal: string;
  confidence: number;
  grade: string;

  entry: number;
  stoploss: number;
  target1: number;
  target2: number;

  entry_index: number;
  exit_index: number | null;
  exit_price: number | null;

  result: string;
  r_multiple: number;
  bars_held: number;

  target1_reached: boolean;
};

type BacktestResult = {
  symbol: string;
  timeframe: string;

  candles: number;
  setups: number;
  triggered: number;

  wins: number;
  losses: number;
  breakeven: number;

  unresolved: number;
  not_triggered: number;

  target1_hits: number;
  target2_hits: number;
  stoploss_hits: number;

  win_rate: number;
  average_r: number;
  total_r: number;

  profit_factor: number | null;

  trades: BacktestTrade[];

  requested_days?: number;

  market_mode?: string;
};

type BacktestPanelProps = {
  apiBase: string;
};

function money(
  value: number | null | undefined
) {
  if (value == null) {
    return "—";
  }

  return `₹${value.toFixed(2)}`;
}

function signed(
  value: number | null | undefined,
  suffix = ""
) {
  if (value == null) {
    return "—";
  }

  return `${
    value > 0 ? "+" : ""
  }${value.toFixed(2)}${suffix}`;
}

function resultClass(
  result: string
) {
  const value =
    result.toUpperCase();

  if (
    value.includes("WIN") ||
    value.includes("TARGET")
  ) {
    return styles.win;
  }

  if (
    value.includes("LOSS") ||
    value.includes("STOP")
  ) {
    return styles.loss;
  }

  if (
    value.includes("BREAK")
  ) {
    return styles.breakEven;
  }

  return styles.pending;
}

export default function BacktestPanel({
  apiBase,
}: BacktestPanelProps) {
  const [
    symbol,
    setSymbol,
  ] = useState(
    "RELIANCE"
  );

  const [
    interval,
    setInterval,
  ] = useState<
    "1m" | "5m" | "15m"
  >("5m");

  const [
    confidence,
    setConfidence,
  ] = useState(
    60
  );

  const [
    days,
    setDays,
  ] = useState(
    10
  );

  const [
    mode,
    setMode,
  ] = useState<
    "live" | "history"
  >("history");

  const [
    loading,
    setLoading,
  ] = useState(
    false
  );

  const [
    result,
    setResult,
  ] =
    useState<
      BacktestResult | null
    >(null);

  const [
    error,
    setError,
  ] = useState("");

  // ==================================================
  // LOAD SAVED SETTINGS
  // ==================================================

  useEffect(() => {
    const savedTimeframe =
      localStorage.getItem(
        "nexus_default_timeframe"
      );

    const savedConfidence =
      localStorage.getItem(
        "nexus_minimum_confidence"
      );

    const savedDays =
      localStorage.getItem(
        "nexus_backtest_days"
      );

    if (
      savedTimeframe ===
        "1m" ||
      savedTimeframe ===
        "5m" ||
      savedTimeframe ===
        "15m"
    ) {
      setInterval(
        savedTimeframe
      );
    }

    if (
      savedConfidence
    ) {
      const parsed =
        Number(
          savedConfidence
        );

      if (
        Number.isFinite(
          parsed
        ) &&
        parsed >= 1 &&
        parsed <= 100
      ) {
        setConfidence(
          parsed
        );
      }
    }

    if (
      savedDays
    ) {
      const parsed =
        Number(
          savedDays
        );

      if (
        Number.isFinite(
          parsed
        ) &&
        parsed >= 1
      ) {
        setDays(
          parsed
        );
      }
    }
  }, []);

  const resolvedTrades =
    useMemo(
      () =>
        result?.trades.filter(
          (
            trade
          ) =>
            trade.result !==
              "UNRESOLVED" &&
            trade.result !==
              "NOT_TRIGGERED"
        ) || [],
      [result]
    );

  // ==================================================
  // RUN BACKTEST
  // ==================================================

  async function runTest(
    event?: FormEvent
  ) {
    event?.preventDefault();

    const cleanSymbol =
      symbol
        .trim()
        .toUpperCase();

    if (
      !cleanSymbol
    ) {
      setError(
        "Enter an NSE symbol."
      );

      return;
    }

    setLoading(
      true
    );

    setError("");

    try {
      const endpoint =
        mode ===
        "history"
          ? `${apiBase}/api/v2/backtest-history/${encodeURIComponent(
              cleanSymbol
            )}?interval=${interval}&days=${days}&minimum_confidence=${confidence}`
          : `${apiBase}/api/v2/backtest/${encodeURIComponent(
              cleanSymbol
            )}?interval=${interval}&minimum_confidence=${confidence}`;

      const response =
        await fetch(
          endpoint,
          {
            credentials:
              "include",
          }
        );

      const body =
        await response
          .json()
          .catch(
            () => ({})
          );

      if (
        !response.ok
      ) {
        throw new Error(
          body.detail ||
            `Backtest failed with status ${response.status}`
        );
      }

      setResult(
        body as BacktestResult
      );
    } catch (
      err
    ) {
      setResult(
        null
      );

      setError(
        err instanceof Error
          ? err.message
          : "Could not run backtest."
      );
    } finally {
      setLoading(
        false
      );
    }
  }

  return (
    <section
      id="backtest-section"
      className={
        styles.shell
      }
    >
      {/* =============================================
          HEADER
      ============================================= */}

      <header
        className={
          styles.hero
        }
      >
        <div>
          <span
            className={
              styles.kicker
            }
          >
            STRATEGY LAB /
            V2 ENGINE
          </span>

          <h1>
            Backtest
            Intelligence
          </h1>

          <p>
            Replay scanner
            setups against live
            or historical candles
            and inspect win rate,
            R-multiples, trade
            outcomes and target
            behaviour.
          </p>
        </div>

        <div
          className={
            styles.engineBadge
          }
        >
          <span
            className={
              loading
                ? styles.busyDot
                : styles.liveDot
            }
          />

          <div>
            <strong>
              {loading
                ? "RUNNING"
                : "ENGINE READY"}
            </strong>

            <small>
              Warmup 60 · Max
              hold 12 bars
            </small>
          </div>
        </div>
      </header>

      {/* =============================================
          CONTROLS
      ============================================= */}

      <form
        onSubmit={
          runTest
        }
        className={
          styles.controlDeck
        }
      >
        <label>
          <span>
            NSE SYMBOL
          </span>

          <input
            value={
              symbol
            }
            onChange={(
              event
            ) =>
              setSymbol(
                event.target
                  .value
              )
            }
            placeholder="RELIANCE"
          />
        </label>

        <label>
          <span>
            TIMEFRAME
          </span>

          <select
            value={
              interval
            }
            onChange={(
              event
            ) =>
              setInterval(
                event.target
                  .value as
                  | "1m"
                  | "5m"
                  | "15m"
              )
            }
          >
            <option value="1m">
              1 minute
            </option>

            <option value="5m">
              5 minutes
            </option>

            <option value="15m">
              15 minutes
            </option>
          </select>
        </label>

        <label>
          <span>
            MIN CONFIDENCE
          </span>

          <input
            type="number"
            min="1"
            max="100"
            value={
              confidence
            }
            onChange={(
              event
            ) =>
              setConfidence(
                Number(
                  event.target
                    .value
                )
              )
            }
          />
        </label>

        <label>
          <span>
            MODE
          </span>

          <select
            value={
              mode
            }
            onChange={(
              event
            ) =>
              setMode(
                event.target
                  .value as
                  | "live"
                  | "history"
              )
            }
          >
            <option value="history">
              Historical
            </option>

            <option value="live">
              Current
              candles
            </option>
          </select>
        </label>

        <label
          className={
            mode === "live"
              ? styles.disabledControl
              : ""
          }
        >
          <span>
            HISTORY DAYS
          </span>

          <input
            type="number"
            min="1"
            max="365"
            value={
              days
            }
            disabled={
              mode ===
              "live"
            }
            onChange={(
              event
            ) =>
              setDays(
                Number(
                  event.target
                    .value
                )
              )
            }
          />
        </label>

        <button
          type="submit"
          className={
            styles.runButton
          }
          disabled={
            loading
          }
        >
          {loading
            ? "RUNNING TEST…"
            : "RUN BACKTEST"}

          <span>
            ↗
          </span>
        </button>
      </form>

      {/* =============================================
          ERROR
      ============================================= */}

      {error && (
        <div
          className={
            styles.errorBanner
          }
        >
          {error}
        </div>
      )}

      {/* =============================================
          EMPTY STATE
      ============================================= */}

      {!result ? (
        <div
          className={
            styles.emptyLab
          }
        >
          <div
            className={
              styles.labCore
            }
          >
            <span />
            <span />
            <i />

            <strong>
              V2
            </strong>
          </div>

          <h2>
            Strategy lab is
            ready
          </h2>

          <p>
            Choose a symbol,
            timeframe and
            confidence threshold,
            then run a historical
            or current-candle
            backtest.
          </p>
        </div>
      ) : (
        <>
          {/* =========================================
              METRICS
          ========================================= */}

          <div
            className={
              styles.metricGrid
            }
          >
            <Metric
              label="WIN RATE"
              value={`${result.win_rate.toFixed(
                1
              )}%`}
              hint={`${result.wins} wins / ${result.losses} losses`}
              tone={
                result.win_rate >=
                50
                  ? "green"
                  : "red"
              }
            />

            <Metric
              label="TOTAL R"
              value={signed(
                result.total_r,
                "R"
              )}
              hint={`Average ${signed(
                result.average_r,
                "R"
              )}`}
              tone={
                result.total_r >=
                0
                  ? "cyan"
                  : "red"
              }
            />

            <Metric
              label="PROFIT FACTOR"
              value={
                result.profit_factor ==
                null
                  ? "—"
                  : result.profit_factor.toFixed(
                      2
                    )
              }
              hint="Gross wins / gross losses"
              tone="violet"
            />

            <Metric
              label="TRIGGERED"
              value={String(
                result.triggered
              )}
              hint={`${result.setups} total setups`}
              tone="amber"
            />
          </div>

          {/* =========================================
              ANALYSIS
          ========================================= */}

          <div
            className={
              styles.analysisGrid
            }
          >
            <section
              className={
                styles.performanceCard
              }
            >
              <div
                className={
                  styles.panelHeader
                }
              >
                <div>
                  <span
                    className={
                      styles.kicker
                    }
                  >
                    PERFORMANCE
                    CORE
                  </span>

                  <h2>
                    {
                      result.symbol
                    }{" "}
                    ·{" "}
                    {
                      result.timeframe
                    }
                  </h2>
                </div>

                <span
                  className={
                    styles.modeChip
                  }
                >
                  {result.market_mode ||
                    mode.toUpperCase()}
                </span>
              </div>

              <div
                className={
                  styles.performanceBody
                }
              >
                <div
                  className={
                    styles.performanceRing
                  }
                >
                  <div
                    className={
                      styles.winArc
                    }
                    style={{
                      transform:
                        `rotate(${
                          -135 +
                          Math.min(
                            100,
                            result.win_rate
                          ) *
                            2.7
                        }deg)`,
                    }}
                  />

                  <span
                    className={
                      styles.ringA
                    }
                  />

                  <span
                    className={
                      styles.ringB
                    }
                  />

                  <strong>
                    {result.win_rate.toFixed(
                      0
                    )}
                    %
                  </strong>

                  <small>
                    WIN RATE
                  </small>
                </div>

                <div
                  className={
                    styles.statMatrix
                  }
                >
                  <Stat
                    label="Candles"
                    value={String(
                      result.candles
                    )}
                  />

                  <Stat
                    label="Setups"
                    value={String(
                      result.setups
                    )}
                  />

                  <Stat
                    label="Wins"
                    value={String(
                      result.wins
                    )}
                    positive
                  />

                  <Stat
                    label="Losses"
                    value={String(
                      result.losses
                    )}
                    negative
                  />

                  <Stat
                    label="Breakeven"
                    value={String(
                      result.breakeven
                    )}
                  />

                  <Stat
                    label="Unresolved"
                    value={String(
                      result.unresolved
                    )}
                  />
                </div>
              </div>

              <div
                className={
                  styles.hitStrip
                }
              >
                <div>
                  <span>
                    TARGET 1
                    HITS
                  </span>

                  <strong>
                    {
                      result.target1_hits
                    }
                  </strong>
                </div>

                <div>
                  <span>
                    TARGET 2
                    HITS
                  </span>

                  <strong>
                    {
                      result.target2_hits
                    }
                  </strong>
                </div>

                <div>
                  <span>
                    STOPLOSS
                    HITS
                  </span>

                  <strong
                    className={
                      styles.negativeText
                    }
                  >
                    {
                      result.stoploss_hits
                    }
                  </strong>
                </div>

                <div>
                  <span>
                    NOT
                    TRIGGERED
                  </span>

                  <strong>
                    {
                      result.not_triggered
                    }
                  </strong>
                </div>
              </div>
            </section>

            {/* =========================================
                STRATEGY PROFILE
            ========================================= */}

            <aside
              className={
                styles.strategyCard
              }
            >
              <div
                className={
                  styles.panelHeader
                }
              >
                <div>
                  <span
                    className={
                      styles.kicker
                    }
                  >
                    STRATEGY
                    PROFILE
                  </span>

                  <h2>
                    Run
                    configuration
                  </h2>
                </div>
              </div>

              <div
                className={
                  styles.strategyList
                }
              >
                <Config
                  label="Symbol"
                  value={
                    result.symbol
                  }
                />

                <Config
                  label="Timeframe"
                  value={
                    result.timeframe
                  }
                />

                <Config
                  label="Minimum confidence"
                  value={`${confidence}%`}
                />

                <Config
                  label="Historical range"
                  value={
                    result.requested_days
                      ? `${result.requested_days} days`
                      : "Current candle window"
                  }
                />

                <Config
                  label="Warmup bars"
                  value="60"
                />

                <Config
                  label="Max hold"
                  value="12 bars"
                />
              </div>

              <div
                className={
                  styles.rSummary
                }
              >
                <span>
                  R-MULTIPLE
                  SUMMARY
                </span>

                <strong
                  className={
                    result.total_r >=
                    0
                      ? styles.positiveText
                      : styles.negativeText
                  }
                >
                  {signed(
                    result.total_r,
                    "R"
                  )}
                </strong>

                <small>
                  {
                    resolvedTrades.length
                  }{" "}
                  resolved trade
                  {resolvedTrades.length ===
                  1
                    ? ""
                    : "s"}
                </small>
              </div>
            </aside>
          </div>

          {/* =========================================
              TRADE REPLAY
          ========================================= */}

          <section
            className={
              styles.tradesCard
            }
          >
            <div
              className={
                styles.panelHeader
              }
            >
              <div>
                <span
                  className={
                    styles.kicker
                  }
                >
                  TRADE REPLAY
                </span>

                <h2>
                  Backtested
                  executions
                </h2>
              </div>

              <span
                className={
                  styles.countChip
                }
              >
                {
                  result.trades
                    .length
                }{" "}
                TRADES
              </span>
            </div>

            <div
              className={
                styles.tableWrap
              }
            >
              <div
                className={
                  styles.tableHead
                }
              >
                <span>#</span>
                <span>
                  SIGNAL
                </span>
                <span>
                  CONF
                </span>
                <span>
                  GRADE
                </span>
                <span>
                  ENTRY
                </span>
                <span>
                  EXIT
                </span>
                <span>
                  RESULT
                </span>
                <span>
                  R
                </span>
                <span>
                  BARS
                </span>
              </div>

              {result.trades
                .length ===
              0 ? (
                <div
                  className={
                    styles.noTrades
                  }
                >
                  No trades were
                  generated for
                  this
                  configuration.
                </div>
              ) : (
                result.trades.map(
                  (
                    trade,
                    index
                  ) => (
                    <div
                      className={
                        styles.tableRow
                      }
                      key={`${trade.entry_index}-${index}`}
                    >
                      <span>
                        {String(
                          index +
                            1
                        ).padStart(
                          2,
                          "0"
                        )}
                      </span>

                      <span
                        className={
                          trade.signal ===
                          "BUY"
                            ? styles.positiveText
                            : trade.signal ===
                                "SELL"
                              ? styles.negativeText
                              : ""
                        }
                      >
                        {
                          trade.signal
                        }
                      </span>

                      <span>
                        {
                          trade.confidence
                        }
                        %
                      </span>

                      <span>
                        {
                          trade.grade
                        }
                      </span>

                      <span>
                        {money(
                          trade.entry
                        )}
                      </span>

                      <span>
                        {money(
                          trade.exit_price
                        )}
                      </span>

                      <span
                        className={`${styles.resultPill} ${resultClass(
                          trade.result
                        )}`}
                      >
                        {
                          trade.result
                        }
                      </span>

                      <span
                        className={
                          trade.r_multiple >=
                          0
                            ? styles.positiveText
                            : styles.negativeText
                        }
                      >
                        {signed(
                          trade.r_multiple,
                          "R"
                        )}
                      </span>

                      <span>
                        {
                          trade.bars_held
                        }
                      </span>
                    </div>
                  )
                )
              )}
            </div>
          </section>
        </>
      )}
    </section>
  );
}

function Metric({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint: string;

  tone:
    | "cyan"
    | "green"
    | "red"
    | "violet"
    | "amber";
}) {
  return (
    <div
      className={`${styles.metric} ${
        styles[
          `metric_${tone}`
        ]
      }`}
    >
      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

      <small>
        {hint}
      </small>
    </div>
  );
}

function Stat({
  label,
  value,
  positive = false,
  negative = false,
}: {
  label: string;
  value: string;
  positive?: boolean;
  negative?: boolean;
}) {
  return (
    <div
      className={
        styles.stat
      }
    >
      <span>
        {label}
      </span>

      <strong
        className={
          positive
            ? styles.positiveText
            : negative
              ? styles.negativeText
              : ""
        }
      >
        {value}
      </strong>
    </div>
  );
}

function Config({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div
      className={
        styles.configRow
      }
    >
      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>
    </div>
  );
}