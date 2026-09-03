"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

type Tab =
  | "ALL"
  | "RISING"
  | "FALLING"
  | "GAINERS"
  | "LOSERS"
  | "VOLUME"
  | "STRONGEST";

type ScannerRow = {
  symbol: string;
  name?: string;
  ltp?: number;
  day_change_pct?: number | null;
  change_1m_pct?: number | null;
  change_5m_pct?: number | null;
  change_15m_pct?: number | null;
  volume?: number | null;
  volume_delta_1m?: number | null;
  turnover?: number | null;
  momentum_score?: number | null;
  momentum_state?: string;
};

type ScannerData = {
  status?: string;
  error?: string;
  generated_at?: string;
  source?: string;
  dynamic_universe_size?: number;
  quoted_count?: number;

  all_stocks?: ScannerRow[];
  total_nse_equities?: number;
  waiting_count?: number;
  scan_progress_pct?: number;

  rising?: ScannerRow[];
  falling?: ScannerRow[];
  gainers?: ScannerRow[];
  losers?: ScannerRow[];
  volume_activity?: ScannerRow[];
  strongest?: ScannerRow[];
};

function num(
  value: unknown,
  fallback = 0,
) {
  const parsed =
    Number(value);

  return Number.isFinite(
    parsed,
  )
    ? parsed
    : fallback;
}

function pct(
  value: unknown,
) {
  const parsed =
    Number(value);

  if (
    !Number.isFinite(
      parsed,
    )
  ) {
    return "—";
  }

  return `${
    parsed > 0
      ? "+"
      : ""
  }${parsed.toFixed(
    2,
  )}%`;
}

function compact(
  value: unknown,
) {
  const parsed =
    Number(value);

  if (
    !Number.isFinite(
      parsed,
    )
  ) {
    return "—";
  }

  return new Intl.NumberFormat(
    "en-IN",
    {
      notation:
        "compact",

      maximumFractionDigits:
        1,
    },
  ).format(
    parsed,
  );
}

export default function FullMarketScannerPanel() {
  const [
    data,
    setData,
  ] =
    useState<ScannerData | null>(
      null,
    );

  const [
    tab,
    setTab,
  ] =
    useState<Tab>(
      "ALL",
    );

  const [
    loading,
    setLoading,
  ] =
    useState(true);

  async function load() {
    try {
      const response =
        await fetch(
          "/api/market-scanner",
          {
            credentials:
              "include",

            cache:
              "no-store",
          },
        );

      const payload =
        await response.json();

      setData(
        payload,
      );

    } catch (error) {
      setData(
        {
          status:
            "ERROR",

          error:
            error instanceof Error
              ? error.message
              : "Unable to load scanner",
        },
      );

    } finally {
      setLoading(
        false,
      );
    }
  }

  useEffect(() => {
    void load();

    const timer =
      window.setInterval(
        () =>
          void load(),
        3000,
      );

    return () =>
      window.clearInterval(
        timer,
      );
  }, []);

  const rows =
    useMemo(
      () => {
        if (!data) {
          return [];
        }

        if (
          tab ===
          "ALL"
        ) {
          return data.all_stocks ??
            [];
        }

        if (
          tab ===
          "RISING"
        ) {
          return data.rising ??
            [];
        }

        if (
          tab ===
          "FALLING"
        ) {
          return data.falling ??
            [];
        }

        if (
          tab ===
          "GAINERS"
        ) {
          return data.gainers ??
            [];
        }

        if (
          tab ===
          "LOSERS"
        ) {
          return data.losers ??
            [];
        }

        if (
          tab ===
          "VOLUME"
        ) {
          return data
            .volume_activity ??
            [];
        }

        return data.strongest ??
          [];
      },
      [
        data,
        tab,
      ],
    );

  const bullish =
    data?.rising?.length ??
    0;

  const bearish =
    data?.falling?.length ??
    0;

  return (
    <section
      style={{
        paddingTop:
          "12px",

        width:
          "100%",

        minWidth:
          0,
      }}
    >
      <div
        style={{
          display:
            "flex",

          justifyContent:
            "space-between",

          alignItems:
            "center",

          gap:
            "16px",

          flexWrap:
            "wrap",
        }}
      >
        <div>
          <span
            style={{
              color:
                "#35e8ff",

              fontSize:
                "10px",

              fontWeight:
                800,

              letterSpacing:
                ".14em",
            }}
          >
            ▤ FULL NSE MARKET SCANNER
          </span>

          <h1
            style={{
              margin:
                "5px 0 0",

              fontSize:
                "24px",
            }}
          >
            Live Momentum Sheet
          </h1>

          <small
            style={{
              color:
                "#71869c",
            }}
          >
            SmartAPI • Dynamic liquid NSE universe
          </small>
        </div>

        <button
          type="button"
          onClick={() =>
            void load()
          }
          style={{
            border:
              "1px solid #00dfff",

            background:
              "rgba(0,223,255,.08)",

            color:
              "#7af5ff",

            padding:
              "8px 13px",

            borderRadius:
              "7px",
          }}
        >
          REFRESH
        </button>
      </div>

      {data?.status ===
        "ERROR" && (
        <div
          style={{
            marginTop:
              "14px",

            padding:
              "12px",

            border:
              "1px solid rgba(255,90,90,.35)",

            color:
              "#ff8d8d",

            borderRadius:
              "8px",
          }}
        >
          {data.error}
        </div>
      )}

      <div
        style={{
          display:
            "grid",

          gridTemplateColumns:
            "repeat(auto-fit,minmax(150px,1fr))",

          gap:
            "10px",

          marginTop:
            "16px",
        }}
      >
        {[
          [
            "ALL NSE EQ",
            data?.total_nse_equities ??
              0,
          ],

          [
            "QUOTED",
            data?.quoted_count ??
              0,
          ],

          [
            "RISING",
            bullish,
          ],

          [
            "FALLING",
            bearish,
          ],
        ].map(
          ([
            label,
            value,
          ]) => (
            <div
              key={label}
              style={{
                border:
                  "1px solid #132a38",

                borderRadius:
                  "9px",

                padding:
                  "14px",

                background:
                  "rgba(3,9,20,.82)",
              }}
            >
              <span
                style={{
                  color:
                    "#71869c",

                  fontSize:
                    "9px",
                }}
              >
                {label}
              </span>

              <strong
                style={{
                  display:
                    "block",

                  marginTop:
                    "7px",

                  fontSize:
                    "22px",
                }}
              >
                {value}
              </strong>
            </div>
          ),
        )}
      </div>

      <div
        style={{
          display:
            "flex",

          gap:
            "7px",

          flexWrap:
            "wrap",

          marginTop:
            "15px",
        }}
      >
        {(
          [
            "ALL",
            "RISING",
            "FALLING",
            "GAINERS",
            "LOSERS",
            "VOLUME",
            "STRONGEST",
          ] as Tab[]
        ).map(
          value => (
            <button
              key={value}
              type="button"
              onClick={() =>
                setTab(
                  value,
                )
              }
              style={{
                border:
                  tab === value
                    ? "1px solid #00e5ff"
                    : "1px solid #173450",

                background:
                  tab === value
                    ? "rgba(0,229,255,.10)"
                    : "#050b16",

                color:
                  tab === value
                    ? "#7af5ff"
                    : "#71869c",

                borderRadius:
                  "7px",

                padding:
                  "8px 11px",

                fontSize:
                  "9px",

                fontWeight:
                  800,
              }}
            >
              {value}
            </button>
          ),
        )}
      </div>

      <div
        style={{
          marginTop:
            "12px",

          border:
            "1px solid #132a38",

          borderRadius:
            "10px",

          overflowX:
            "auto",

          background:
            "rgba(3,9,20,.82)",
        }}
      >
        <div
          style={{
            minWidth:
              "900px",
          }}
        >
          <div
            style={{
              display:
                "grid",

              gridTemplateColumns:
                "1.1fr .75fr .65fr .65fr .65fr .65fr .8fr .8fr",

              gap:
                "8px",

              padding:
                "11px 13px",

              color:
                "#60788e",

              fontSize:
                "8px",

              fontWeight:
                800,
            }}
          >
            <span>STOCK</span>
            <span>LTP</span>
            <span>1M</span>
            <span>5M</span>
            <span>15M</span>
            <span>DAY</span>
            <span>VOLUME</span>
            <span>MOMENTUM</span>
          </div>

          {loading && (
            <div
              style={{
                padding:
                  "20px",

                color:
                  "#71869c",
              }}
            >
              Building full NSE universe...
            </div>
          )}

          {!loading &&
            rows.map(
              (
                item,
                index,
              ) => {
                const momentum =
                  num(
                    item
                      .momentum_score,
                  );

                const positive =
                  momentum > 0;

                return (
                  <div
                    key={
                      item.symbol
                    }
                    style={{
                      display:
                        "grid",

                      gridTemplateColumns:
                        "1.1fr .75fr .65fr .65fr .65fr .65fr .8fr .8fr",

                      gap:
                        "8px",

                      alignItems:
                        "center",

                      minHeight:
                        "48px",

                      padding:
                        "7px 13px",

                      borderTop:
                        "1px solid #102238",

                      fontSize:
                        "10px",
                    }}
                  >
                    <div>
                      <strong
                        style={{
                          color:
                            "#eaffff",
                        }}
                      >
                        {index +
                          1}.{" "}
                        {
                          item.symbol
                        }
                      </strong>

                      <small
                        style={{
                          display:
                            "block",

                          marginTop:
                            "2px",

                          color:
                            "#536a80",
                        }}
                      >
                        {
                          item
                            .momentum_state
                        }
                      </small>
                    </div>

                    <span>
                      ₹
                      {num(
                        item.ltp,
                      ).toFixed(
                        2,
                      )}
                    </span>

                    <span>
                      {pct(
                        item
                          .change_1m_pct,
                      )}
                    </span>

                    <span>
                      {pct(
                        item
                          .change_5m_pct,
                      )}
                    </span>

                    <span>
                      {pct(
                        item
                          .change_15m_pct,
                      )}
                    </span>

                    <span>
                      {pct(
                        item
                          .day_change_pct,
                      )}
                    </span>

                    <span>
                      {compact(
                        item.volume,
                      )}
                    </span>

                    <strong
                      style={{
                        color:
                          positive
                            ? "#00f59b"
                            : momentum < 0
                              ? "#ff647c"
                              : "#71869c",
                      }}
                    >
                      {momentum >
                      0
                        ? "+"
                        : ""}
                      {momentum.toFixed(
                        1,
                      )}
                    </strong>
                  </div>
                );
              },
            )}
        </div>
      </div>

      <div
        style={{
          marginTop:
            "8px",

          color:
            "#536a80",

          fontSize:
            "8px",
        }}
      >
        Momentum ranking is a discovery tool,
        not a BUY/SELL probability. 1m, 5m and
        15m history builds after the scanner starts.
      </div>
    </section>
  );
}
