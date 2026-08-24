"use client";

import {
  useEffect,
  useState,
} from "react";

import styles from "./BacktestPanel.module.css";


type BacktestTimeframe =
  | "1m"
  | "5m"
  | "15m";


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

  profit_factor:
    number | null;

  trades:
    BacktestTrade[];
};


type Props = {
  apiBase: string;

  symbols: string[];

  defaultSymbol?: string;

  defaultTimeframe:
    BacktestTimeframe;

  onOpenChart: (
    symbol: string
  ) => void;
};


function numberValue(
  value:
    number | null,
  digits = 2
) {

  if (
    value === null ||
    !Number.isFinite(
      value
    )
  ) {

    return "—";

  }

  return value.toFixed(
    digits
  );
}


function resultClass(
  result: string
) {

  const value =
    result
      .trim()
      .toUpperCase();


  if (
    value === "TARGET1" ||
    value === "TARGET2"
  ) {

    return styles.positive;

  }


  if (
    value === "STOPLOSS"
  ) {

    return styles.negative;

  }


  return styles.neutral;
}


function signalClass(
  signal: string
) {

  return signal
    .trim()
    .toUpperCase() ===
    "BUY"

    ? styles.buy

    : styles.sell;
}


export default function BacktestPanel({
  apiBase,
  symbols,
  defaultSymbol,
  defaultTimeframe,
  onOpenChart,
}: Props) {

  const [
    symbol,
    setSymbol,
  ] = useState(
    defaultSymbol ||
    symbols[0] ||
    ""
  );


  const [
    timeframe,
    setTimeframe,
  ] =
    useState<BacktestTimeframe>(
      defaultTimeframe
    );


  const [
    minimumConfidence,
    setMinimumConfidence,
  ] = useState(
    60
  );


  const [
    result,
    setResult,
  ] =
    useState<
      BacktestResult | null
    >(
      null
    );


  const [
    loading,
    setLoading,
  ] = useState(
    false
  );


  const [
    message,
    setMessage,
  ] = useState(
    ""
  );


  // ==================================================
  // KEEP SELECTED STOCK INSIDE WATCHLIST UNIVERSE
  // ==================================================

  useEffect(
    () => {

      const normalizedDefault =
        defaultSymbol
          ?.trim()
          .toUpperCase();


      if (
        normalizedDefault &&
        symbols.includes(
          normalizedDefault
        )
      ) {

        setSymbol(
          normalizedDefault
        );

        return;
      }


      if (
        symbol &&
        symbols.includes(
          symbol
        )
      ) {

        return;

      }


      setSymbol(
        symbols[0] ||
        ""
      );

    },
    [
      defaultSymbol,
      symbols,
      symbol,
    ]
  );


  // ==================================================
  // RUN BACKTEST
  // ==================================================

  async function runBacktest() {

    if (
      !symbol
    ) {

      setMessage(
        "Add a stock to the Watchlist first."
      );

      return;

    }


    setLoading(
      true
    );

    setMessage(
      ""
    );


    try {

      const response =
        await fetch(
          `${apiBase}/api/v2/backtest/${encodeURIComponent(
            symbol
          )}?interval=${encodeURIComponent(
            timeframe
          )}&minimum_confidence=${minimumConfidence}`,
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

        const body =
          await response
            .json()
            .catch(
              () => ({})
            );


        throw new Error(
          body.detail ||
          "Backtest failed"
        );

      }


      const data:
        BacktestResult =
        await response.json();


      setResult(
        data
      );


    } catch (
      error
    ) {

      setResult(
        null
      );


      setMessage(
        error instanceof Error
          ? error.message
          : "Backtest failed"
      );


    } finally {

      setLoading(
        false
      );

    }

  }


  return (

    <section
      className={
        styles.panel
      }
    >

      {/* ==============================================
          HEADER
      ============================================== */}

      <div
        className={
          styles.header
        }
      >

        <div>

          <span
            className={
              styles.eyebrow
            }
          >
            ◈ STRATEGY LAB
          </span>


          <h2>
            NEXUS BACKTEST ENGINE
          </h2>


          <p>
            Test NEXUS scanner signals
            against historical NSE market data.
          </p>

        </div>


        {result && (

          <div
            className={
              styles.runMeta
            }
          >

            <span>
              {
                result.symbol
              }
            </span>

            <span>
              {
                result.timeframe
              }
            </span>

            <span>
              {
                result.candles
              } CANDLES
            </span>

          </div>

        )}

      </div>


      {/* ==============================================
          CONTROLS
      ============================================== */}

      <div
        className={
          styles.controls
        }
      >

        <label
          className={
            styles.field
          }
        >

          <span>
            SYMBOL
          </span>


          <select
            value={
              symbol
            }

            onChange={
              (
                event
              ) => {

                setSymbol(
                  event.target
                    .value
                );

              }
            }

            className={
              styles.input
            }
          >

            {symbols.length ===
              0 && (

              <option value="">
                No Watchlist stocks
              </option>

            )}


            {symbols.map(
              (
                value
              ) => (

                <option
                  key={
                    value
                  }
                  value={
                    value
                  }
                >
                  {
                    value
                  }
                </option>

              )
            )}

          </select>

        </label>


        <label
          className={
            styles.field
          }
        >

          <span>
            TIMEFRAME
          </span>


          <select
            value={
              timeframe
            }

            onChange={
              (
                event
              ) => {

                setTimeframe(
                  event.target
                    .value as
                    BacktestTimeframe
                );

              }
            }

            className={
              styles.input
            }
          >

            <option value="1m">
              1 Minute
            </option>

            <option value="5m">
              5 Minutes
            </option>

            <option value="15m">
              15 Minutes
            </option>

          </select>

        </label>


        <label
          className={
            styles.field
          }
        >

          <span>
            MIN CONFIDENCE
          </span>


          <div
            className={
              styles.confidenceInput
            }
          >

            <input
              type="number"
              min={
                0
              }
              max={
                100
              }

              value={
                minimumConfidence
              }

              onChange={
                (
                  event
                ) => {

                  setMinimumConfidence(
                    Number(
                      event.target
                        .value
                    )
                  );

                }
              }

              className={
                styles.input
              }
            />


            <span>
              %
            </span>

          </div>

        </label>


        <div
          className={
            styles.actions
          }
        >

          <button
            type="button"

            onClick={
              () =>
                void runBacktest()
            }

            disabled={
              loading
            }

            className={
              styles.runButton
            }
          >

            <span
              className={
                styles.buttonIcon
              }
            >
              ▶
            </span>


            {
              loading
                ? "RUNNING..."
                : "RUN BACKTEST"
            }

          </button>


          <button
            type="button"

            onClick={
              () => {

                if (
                  symbol
                ) {

                  onOpenChart(
                    symbol
                  );

                }

              }
            }

            disabled={
              !symbol
            }

            className={
              styles.chartButton
            }
          >

            <span
              className={
                styles.buttonIcon
              }
            >
              ◩
            </span>

            OPEN CHART

          </button>

        </div>

      </div>


      {message && (

        <div
          className={
            styles.message
          }
        >
          {
            message
          }
        </div>

      )}


      {/* ==============================================
          RESULTS
      ============================================== */}

      {result && (

        <>

          <div
            className={
              styles.stats
            }
          >

            <div
              className={
                styles.statCard
              }
            >

              <span>
                WIN RATE
              </span>

              <strong
                className={
                  result.win_rate >=
                  50

                    ? styles.goodValue

                    : styles.badValue
                }
              >
                {
                  numberValue(
                    result.win_rate
                  )
                }
                %
              </strong>

            </div>


            <div
              className={
                styles.statCard
              }
            >

              <span>
                WINS
              </span>

              <strong
                className={
                  styles.goodValue
                }
              >
                {
                  result.wins
                }
              </strong>

            </div>


            <div
              className={
                styles.statCard
              }
            >

              <span>
                LOSSES
              </span>

              <strong
                className={
                  styles.badValue
                }
              >
                {
                  result.losses
                }
              </strong>

            </div>


            <div
              className={
                styles.statCard
              }
            >

              <span>
                TOTAL R
              </span>

              <strong
                className={
                  result.total_r >=
                  0

                    ? styles.goodValue

                    : styles.badValue
                }
              >
                {
                  numberValue(
                    result.total_r
                  )
                }
                R
              </strong>

            </div>


            <div
              className={
                styles.statCard
              }
            >

              <span>
                AVG R
              </span>

              <strong>
                {
                  numberValue(
                    result.average_r
                  )
                }
                R
              </strong>

            </div>


            <div
              className={
                styles.statCard
              }
            >

              <span>
                PROFIT FACTOR
              </span>

              <strong>
                {
                  numberValue(
                    result.profit_factor
                  )
                }
              </strong>

            </div>


            <div
              className={
                styles.statCard
              }
            >

              <span>
                SETUPS
              </span>

              <strong>
                {
                  result.setups
                }
              </strong>

            </div>


            <div
              className={
                styles.statCard
              }
            >

              <span>
                TRIGGERED
              </span>

              <strong>
                {
                  result.triggered
                }
              </strong>

            </div>

          </div>


          {/* ==============================================
              SECONDARY SUMMARY
          ============================================== */}

          <div
            className={
              styles.summaryStrip
            }
          >

            <span>
              BREAKEVEN

              <strong>
                {
                  result.breakeven
                }
              </strong>
            </span>


            <span>
              UNRESOLVED

              <strong>
                {
                  result.unresolved
                }
              </strong>
            </span>


            <span>
              T1 HITS

              <strong>
                {
                  result.target1_hits
                }
              </strong>
            </span>


            <span>
              T2 HITS

              <strong>
                {
                  result.target2_hits
                }
              </strong>
            </span>


            <span>
              SL HITS

              <strong>
                {
                  result.stoploss_hits
                }
              </strong>
            </span>

          </div>


          {/* ==============================================
              TRADE HISTORY
          ============================================== */}

          <div
            className={
              styles.history
            }
          >

            <div
              className={
                styles.historyHeader
              }
            >

              <div>

                <span
                  className={
                    styles.eyebrow
                  }
                >
                  TRADE HISTORY
                </span>

                <p>
                  Historical signal execution
                  results
                </p>

              </div>


              <span
                className={
                  styles.counter
                }
              >
                {
                  result.trades
                    .length
                }
              </span>

            </div>


            {result.trades.length ===
              0 ? (

              <div
                className={
                  styles.empty
                }
              >
                No qualifying trades
                found for this configuration.
              </div>

            ) : (

              <div
                className={
                  styles.tableScroll
                }
              >

                <table
                  className={
                    styles.tradeTable
                  }
                >

                  <colgroup>

                    <col
                      style={{
                        width:
                          "10%",
                      }}
                    />

                    <col
                      style={{
                        width:
                          "10%",
                      }}
                    />

                    <col
                      style={{
                        width:
                          "9%",
                      }}
                    />

                    <col
                      style={{
                        width:
                          "16%",
                      }}
                    />

                    <col
                      style={{
                        width:
                          "16%",
                      }}
                    />

                    <col
                      style={{
                        width:
                          "17%",
                      }}
                    />

                    <col
                      style={{
                        width:
                          "12%",
                      }}
                    />

                    <col
                      style={{
                        width:
                          "10%",
                      }}
                    />

                  </colgroup>


                  <thead>

                    <tr>

                      <th>
                        SIGNAL
                      </th>

                      <th>
                        CONF.
                      </th>

                      <th>
                        GRADE
                      </th>

                      <th>
                        ENTRY
                      </th>

                      <th>
                        EXIT
                      </th>

                      <th>
                        RESULT
                      </th>

                      <th>
                        R
                      </th>

                      <th>
                        BARS
                      </th>

                    </tr>

                  </thead>


                  <tbody>

                    {result.trades.map(
                      (
                        trade,
                        index
                      ) => (

                        <tr
                          key={
                            `${trade.entry_index}-${index}`
                          }
                        >

                          <td>

                            <span
                              className={
                                signalClass(
                                  trade.signal
                                )
                              }
                            >
                              {
                                trade.signal
                              }
                            </span>

                          </td>


                          <td>
                            {
                              trade.confidence
                            }
                            %
                          </td>


                          <td>

                            <span
                              className={
                                styles.grade
                              }
                            >
                              {
                                trade.grade
                              }
                            </span>

                          </td>


                          <td
                            className={
                              styles.numeric
                            }
                          >
                            ₹
                            {
                              numberValue(
                                trade.entry
                              )
                            }
                          </td>


                          <td
                            className={
                              styles.numeric
                            }
                          >

                            {
                              trade.exit_price ===
                                null

                                ? "—"

                                : `₹${numberValue(
                                  trade.exit_price
                                )}`
                            }

                          </td>


                          <td>

                            <span
                              className={
                                resultClass(
                                  trade.result
                                )
                              }
                            >
                              {
                                trade.result
                              }
                            </span>

                          </td>


                          <td
                            className={
                              trade.r_multiple >
                                0

                                ? styles.goodValue

                                : trade.r_multiple <
                                  0

                                  ? styles.badValue

                                  : ""
                            }
                          >
                            {
                              numberValue(
                                trade.r_multiple
                              )
                            }
                            R
                          </td>


                          <td>
                            {
                              trade.bars_held
                            }
                          </td>

                        </tr>

                      )
                    )}

                  </tbody>

                </table>

              </div>

            )}

          </div>

        </>

      )}

    </section>

  );

}