"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import OpportunityDetail from "../live-edge/OpportunityDetail";
import DirectionalLeaders from "./DirectionalLeaders";

type Opportunity = {
  symbol: string;
  ltp: number;
  opportunity_score: number;
  opportunity_state: string;

  rvol?: number;
  volume?: number;
  change_1m_percent?: number;
  change_5m_percent?: number;

  opportunity_velocity?: {
    delta_1m?: number | null;
    delta_5m?: number | null;
    rvol_delta_1m?: number | null;
    rvol_delta_5m?: number | null;
    state?: string;
    new_threshold?: number | null;
  };

  [key: string]: any;
};

type LiveEdgeData = {
  mode?: string;
  data_source?: string;
  generated_at?: string;
  scored_count?: number;
  results?: any[];
  experimental_edge_summary?: any;
};

const num = (
  value: unknown,
  fallback = 0,
) => {
  const parsed =
    Number(value);

  return Number.isFinite(
    parsed,
  )
    ? parsed
    : fallback;
};

function signed(
  value: unknown,
  digits = 1,
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
    digits,
  )}`;
}

function percent(
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

function compactVolume(
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

function timeLabel(
  value?: string,
) {
  if (!value) {
    return "WAITING";
  }

  const date =
    new Date(value);

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return value;
  }

  return date.toLocaleTimeString(
    "en-IN",
    {
      hour:
        "2-digit",

      minute:
        "2-digit",

      second:
        "2-digit",
    },
  );
}

export default function LiveEdgePanel() {
  const [
    data,
    setData,
  ] =
    useState<LiveEdgeData | null>(
      null,
    );

  const [
    error,
    setError,
  ] =
    useState("");

  const [
    autoRefresh,
    setAutoRefresh,
  ] =
    useState(true);

  const [
    selected,
    setSelected,
  ] =
    useState<Opportunity | null>(
      null,
    );

  async function load() {
    try {
      const response =
        await fetch(
          "/api/live-edge",
          {
            credentials:
              "include",

            cache:
              "no-store",
          },
        );

      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}`,
        );
      }

      const payload =
        await response.json();

      setData(
        payload,
      );

      setError(
        "",
      );

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Live Edge unavailable",
      );
    }
  }

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (!autoRefresh) {
      return;
    }

    const timer =
      window.setInterval(
        () =>
          void load(),
        5000,
      );

    return () =>
      window.clearInterval(
        timer,
      );
  }, [
    autoRefresh,
  ]);

  const summary =
    data
      ?.experimental_edge_summary ??
    {};

  const opportunities =
    useMemo(() => {

      let rows: any[] =
        Array.isArray(
          summary
            .opportunity_rows,
        )
          ? summary
              .opportunity_rows
          : [];

      if (
        rows.length === 0
        && Array.isArray(
          data?.results,
        )
      ) {
        rows =
          data.results.map(
            (stock: any) => {
              const edge =
                stock
                  .experimental_edge ??
                {};

              return {
                ...stock,
                ...edge,

                opportunity_velocity:
                  edge
                    .opportunity_velocity,

                rvol:
                  edge.rvol ??
                  stock.rvol,

                volume:
                  stock.volume,
              };
            },
          );
      }

      return rows
        .map(
          (
            item: any,
          ): Opportunity => ({
            ...item,

            symbol:
              String(
                item.symbol ??
                "",
              ),

            ltp:
              num(
                item.ltp,
              ),

            opportunity_score:
              num(
                item
                  .opportunity_score,
              ),

            opportunity_state:
              String(
                item
                  .opportunity_state ??
                "NORMAL",
              ),

            rvol:
              num(
                item.rvol,
              ),

            volume:
              num(
                item.volume,
              ),
          }),
        )
        .filter(
          item =>
            item
              .opportunity_score >
            0,
        )
        .sort(
          (a, b) =>
            b.opportunity_score -
            a.opportunity_score,
        );

    }, [
      data,
      summary,
    ]);

  const risingFast =
    Array.isArray(
      summary.rising_fast,
    )
      ? summary.rising_fast
      : [];

  const newEntrants =
    Array.isArray(
      summary.new_entrants,
    )
      ? summary.new_entrants
      : [];

  const ready =
    num(
      summary.stocks_ready ??
      summary.ready_count ??
      data?.scored_count ??
      data?.results?.length,
    );

  const opp40 =
    opportunities.filter(
      item =>
        item.opportunity_score >=
        40,
    ).length;

  const opp50 =
    opportunities.filter(
      item =>
        item.opportunity_score >=
        50,
    ).length;

  const opp60 =
    opportunities.filter(
      item =>
        item.opportunity_score >=
        60,
    ).length;

  return (
    <section
      style={{
        width:
          "100%",

        minWidth:
          0,

        paddingTop:
          "12px",
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
                "#00e5ff",

              fontSize:
                "10px",

              fontWeight:
                800,

              letterSpacing:
                ".14em",
            }}
          >
            ⚡ LIVE EDGE
          </span>

          <h1
            style={{
              margin:
                "5px 0 0",

              fontSize:
                "24px",
            }}
          >
            Dynamic Opportunity Radar
          </h1>

          <small
            style={{
              color:
                "#71869c",
            }}
          >
            {data?.mode ??
              "WAITING"}
            {" • "}
            {data?.data_source ??
              "—"}
            {" • "}
            {timeLabel(
              data?.generated_at,
            )}
          </small>
        </div>

        <button
          type="button"
          onClick={() =>
            setAutoRefresh(
              current =>
                !current,
            )
          }
          style={{
            border:
              "1px solid #173450",

            borderRadius:
              "7px",

            padding:
              "8px 12px",

            background:
              "#050b16",

            color:
              autoRefresh
                ? "#00f59b"
                : "#71869c",
          }}
        >
          AUTO REFRESH{" "}
          {autoRefresh
            ? "ON"
            : "OFF"}
        </button>
      </div>

      {error && (
        <div
          style={{
            marginTop:
              "12px",

            color:
              "#ff8d8d",
          }}
        >
          {error}
        </div>
      )}

      <div
        style={{
          display:
            "grid",

          gridTemplateColumns:
            "repeat(auto-fit, minmax(140px,1fr))",

          gap:
            "10px",

          marginTop:
            "16px",
        }}
      >
        {[
          [
            "STOCKS READY",
            ready,
          ],

          [
            "40+ WATCH",
            opp40,
          ],

          [
            "50+ PRIORITY",
            opp50,
          ],

          [
            "60+ HOT",
            opp60,
          ],

          [
            "RISING",
            risingFast.length,
          ],

          [
            "NEW ENTRANTS",
            newEntrants.length,
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
                    "8px",

                  fontSize:
                    "23px",
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
            "grid",

          gridTemplateColumns:
            "repeat(auto-fit, minmax(320px,1fr))",

          gap:
            "12px",

          marginTop:
            "14px",
        }}
      >
        <div
          style={{
            border:
              "1px solid rgba(0,245,155,.22)",

            borderRadius:
              "10px",

            padding:
              "15px",

            background:
              "rgba(0,245,155,.035)",
          }}
        >
          <strong
            style={{
              color:
                "#00f59b",
            }}
          >
            🚀 RISING FAST
          </strong>

          <div
            style={{
              marginTop:
                "12px",
            }}
          >
            {risingFast
              .slice(
                0,
                10,
              )
              .map(
                (
                  item: any,
                ) => (
                  <div
                    key={
                      item.symbol
                    }
                    style={{
                      display:
                        "grid",

                      gridTemplateColumns:
                        "1fr auto auto auto",

                      gap:
                        "10px",

                      padding:
                        "9px 0",

                      borderTop:
                        "1px solid #102238",

                      fontSize:
                        "10px",
                    }}
                  >
                    <strong>
                      {
                        item.symbol
                      }
                    </strong>

                    <span>
                      OPP{" "}
                      {num(
                        item
                          .opportunity_score,
                      ).toFixed(
                        1,
                      )}
                    </span>

                    <span
                      style={{
                        color:
                          "#00f59b",
                      }}
                    >
                      Δ1m{" "}
                      {signed(
                        item
                          .delta_1m,
                      )}
                    </span>

                    <span>
                      RVOL{" "}
                      {num(
                        item.rvol,
                      ).toFixed(
                        1,
                      )}
                      x
                    </span>
                  </div>
                ),
              )}

            {risingFast.length ===
              0 && (
              <small
                style={{
                  color:
                    "#71869c",
                }}
              >
                Building velocity
                history...
              </small>
            )}
          </div>
        </div>

        <div
          style={{
            border:
              "1px solid rgba(0,213,255,.22)",

            borderRadius:
              "10px",

            padding:
              "15px",

            background:
              "rgba(0,213,255,.035)",
          }}
        >
          <strong
            style={{
              color:
                "#55dcff",
            }}
          >
            🆕 NEW ENTRANTS
          </strong>

          <div
            style={{
              marginTop:
                "12px",
            }}
          >
            {newEntrants
              .slice(
                0,
                10,
              )
              .map(
                (
                  item: any,
                  index: number,
                ) => (
                  <div
                    key={`${item.symbol}-${item.threshold}-${index}`}
                    style={{
                      display:
                        "grid",

                      gridTemplateColumns:
                        "1fr auto auto",

                      gap:
                        "10px",

                      padding:
                        "9px 0",

                      borderTop:
                        "1px solid #102238",

                      fontSize:
                        "10px",
                    }}
                  >
                    <strong>
                      {
                        item.symbol
                      }
                    </strong>

                    <span
                      style={{
                        color:
                          "#55dcff",

                        fontWeight:
                          700,
                      }}
                    >
                      NEW{" "}
                      {
                        item.threshold
                      }
                      +
                    </span>

                    <span>
                      {num(
                        item
                          .opportunity_score,
                      ).toFixed(
                        1,
                      )}
                    </span>
                  </div>
                ),
              )}

            {newEntrants.length ===
              0 && (
              <small
                style={{
                  color:
                    "#71869c",
                }}
              >
                No recent threshold
                crossings.
              </small>
            )}
          </div>
        </div>
      </div>

      <DirectionalLeaders
        summary={summary}
      />

      <div
        style={{
          marginTop:
            "14px",

          border:
            "1px solid #132a38",

          borderRadius:
            "10px",

          padding:
            "15px",

          background:
            "rgba(3,9,20,.82)",
        }}
      >
        <strong
          style={{
            color:
              "#35e8ff",
          }}
        >
          TOP MOVEMENT OPPORTUNITIES
        </strong>

        <div
          style={{
            display:
              "grid",

            gridTemplateColumns:
              "repeat(auto-fit, minmax(205px,1fr))",

            gap:
              "9px",

            marginTop:
              "12px",
          }}
        >
          {opportunities
            .slice(
              0,
              24,
            )
            .map(
              item => {
                const velocity =
                  item
                    .opportunity_velocity ??
                  {};

                return (
                  <button
                    key={
                      item.symbol
                    }
                    type="button"
                    onClick={() =>
                      setSelected(
                        item,
                      )
                    }
                    style={{
                      border:
                        "1px solid #122c3d",

                      borderRadius:
                        "8px",

                      padding:
                        "12px",

                      background:
                        "#040b16",

                      color:
                        "#dffaff",

                      textAlign:
                        "left",
                    }}
                  >
                    <div
                      style={{
                        display:
                          "flex",

                        justifyContent:
                          "space-between",
                      }}
                    >
                      <strong>
                        {
                          item.symbol
                        }
                      </strong>

                      <strong
                        style={{
                          color:
                            item
                              .opportunity_score >=
                            60
                              ? "#ff7f8d"
                              : "#55dcff",
                        }}
                      >
                        {item
                          .opportunity_score
                          .toFixed(
                            1,
                          )}
                      </strong>
                    </div>

                    <div
                      style={{
                        display:
                          "grid",

                        gridTemplateColumns:
                          "1fr 1fr",

                        gap:
                          "6px",

                        marginTop:
                          "10px",

                        fontSize:
                          "9px",

                        color:
                          "#71869c",
                      }}
                    >
                      <span>
                        VOL{" "}
                        {compactVolume(
                          item.volume,
                        )}
                      </span>

                      <span>
                        RVOL{" "}
                        {num(
                          item.rvol,
                        ).toFixed(
                          1,
                        )}
                        x
                      </span>

                      <span>
                        Δ OPP 1m{" "}
                        <b
                          style={{
                            color:
                              num(
                                velocity
                                  .delta_1m,
                              ) > 0
                                ? "#00f59b"
                                : "#71869c",
                          }}
                        >
                          {signed(
                            velocity
                              .delta_1m,
                          )}
                        </b>
                      </span>

                      <span>
                        Δ RVOL 1m{" "}
                        {signed(
                          velocity
                            .rvol_delta_1m,
                        )}
                      </span>

                      <span>
                        1m{" "}
                        {percent(
                          item
                            .change_1m_percent,
                        )}
                      </span>

                      <span>
                        5m{" "}
                        {percent(
                          item
                            .change_5m_percent,
                        )}
                      </span>
                    </div>

                    <div
                      style={{
                        marginTop:
                          "10px",

                        color:
                          "#00dfff",

                        fontSize:
                          "9px",

                        fontWeight:
                          700,
                      }}
                    >
                      WHY THIS STOCK? →
                    </div>
                  </button>
                );
              },
            )}
        </div>
      </div>

      {selected && (
        <OpportunityDetail
          item={selected}
          onClose={() =>
            setSelected(
              null,
            )
          }
        />
      )}
    </section>
  );
}
