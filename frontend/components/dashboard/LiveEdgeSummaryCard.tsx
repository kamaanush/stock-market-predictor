"use client";

import {
  useEffect,
  useState,
} from "react";

type LiveEdgeResponse = {
  mode?: string;
  generated_at?: string;
  scored_count?: number;
  results?: any[];
  experimental_edge_summary?: any;
};

function numberValue(
  ...values: unknown[]
) {
  for (const value of values) {
    const parsed = Number(value);

    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return 0;
}

function formatTime(
  value?: string,
) {
  if (!value) {
    return "Waiting...";
  }

  const date = new Date(value);

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
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    },
  );
}

export default function LiveEdgeSummaryCard() {
  const [
    data,
    setData,
  ] = useState<LiveEdgeResponse | null>(
    null,
  );

  const [
    error,
    setError,
  ] = useState("");

  useEffect(() => {
    let active = true;

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

        if (active) {
          setData(payload);
          setError("");
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Live Edge unavailable",
          );
        }
      }
    }

    void load();

    const timer =
      window.setInterval(
        load,
        5000,
      );

    return () => {
      active = false;

      window.clearInterval(
        timer,
      );
    };
  }, []);

  const summary =
    data
      ?.experimental_edge_summary ??
    {};

  const ready =
    numberValue(
      summary.stocks_ready,
      summary.ready_count,
      data?.scored_count,
      data?.results?.length,
    );

  const opp40 =
    numberValue(
      summary.opportunity_40_plus,
      summary.opportunity_40,
      summary.watch_count,
    );

  const opp50 =
    numberValue(
      summary.opportunity_50_plus,
      summary.opportunity_50,
      summary.priority_count,
    );

  const opp60 =
    numberValue(
      summary.opportunity_60_plus,
      summary.opportunity_60,
      summary.high_priority_count,
    );

  let opportunityRows: any[] = [];

  if (
    Array.isArray(
      summary.opportunity_rows,
    )
  ) {
    opportunityRows =
      summary.opportunity_rows;
  } else if (
    Array.isArray(
      summary.top_opportunities,
    )
  ) {
    opportunityRows =
      summary.top_opportunities;
  } else if (
    Array.isArray(
      summary.opportunities,
    )
  ) {
    opportunityRows =
      summary.opportunities;
  }

  if (
    opportunityRows.length === 0 &&
    Array.isArray(data?.results)
  ) {
    opportunityRows =
      data.results
        .map((stock: any) => ({
          symbol:
            stock.symbol,

          opportunity_score:
            stock
              .experimental_edge
              ?.opportunity_score ??
            0,
        }))
        .filter(
          (item: any) =>
            Number(
              item.opportunity_score,
            ) > 0,
        );
  }

  const topOpportunity =
    [...opportunityRows]
      .sort(
        (a, b) =>
          numberValue(
            b.opportunity_score,
            b.score,
          ) -
          numberValue(
            a.opportunity_score,
            a.score,
          ),
      )[0];

  const topSymbol =
    topOpportunity?.symbol ??
    "—";

  const topScore =
    numberValue(
      topOpportunity
        ?.opportunity_score,
      topOpportunity?.score,
    );

  const mode =
    data?.mode ??
    summary.mode ??
    "—";

  return (
    <section
      style={{
        marginBottom:
          "16px",

        border:
          "1px solid rgba(0,245,155,.25)",

        borderRadius:
          "14px",

        padding:
          "18px",

        background:
          "linear-gradient(135deg, rgba(0,245,155,.07), rgba(0,180,255,.035))",

        boxShadow:
          "0 12px 40px rgba(0,0,0,.16)",
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
          <div
            style={{
              color:
                "#00f59b",

              fontSize:
                "10px",

              fontWeight:
                800,

              letterSpacing:
                ".15em",
            }}
          >
            ⚡ LIVE EDGE
          </div>

          <h2
            style={{
              margin:
                "5px 0 0",

              color:
                "#eafff6",

              fontSize:
                "20px",
            }}
          >
            Intraday Opportunity Radar
          </h2>

          <div
            style={{
              marginTop:
                "5px",

              color:
                "#71869c",

              fontSize:
                "10px",
            }}
          >
            {mode}
            {" • "}
            Updated{" "}
            {formatTime(
              data?.generated_at,
            )}
          </div>
        </div>

        <a
          href="/dashboard?view=liveedge"
          style={{
            display:
              "inline-flex",

            alignItems:
              "center",

            justifyContent:
              "center",

            border:
              "1px solid #00f59b",

            borderRadius:
              "8px",

            padding:
              "9px 14px",

            color:
              "#00f59b",

            textDecoration:
              "none",

            fontSize:
              "10px",

            fontWeight:
              800,

            letterSpacing:
              ".08em",
          }}
        >
          OPEN LIVE EDGE →
        </a>
      </div>

      <div
        style={{
          display:
            "grid",

          gridTemplateColumns:
            "repeat(auto-fit, minmax(125px, 1fr))",

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
        ].map(
          ([
            label,
            value,
          ]) => (
            <div
              key={label}
              style={{
                border:
                  "1px solid #102d25",

                borderRadius:
                  "10px",

                padding:
                  "12px",

                background:
                  "rgba(2,12,10,.65)",
              }}
            >
              <div
                style={{
                  color:
                    "#71869c",

                  fontSize:
                    "9px",

                  letterSpacing:
                    ".08em",
                }}
              >
                {label}
              </div>

              <strong
                style={{
                  display:
                    "block",

                  marginTop:
                    "5px",

                  color:
                    "#ffffff",

                  fontSize:
                    "20px",
                }}
              >
                {value}
              </strong>
            </div>
          ),
        )}

        <div
          style={{
            border:
              "1px solid rgba(0,245,155,.22)",

            borderRadius:
              "10px",

            padding:
              "12px",

            background:
              "rgba(0,245,155,.045)",
          }}
        >
          <div
            style={{
              color:
                "#71869c",

              fontSize:
                "9px",

              letterSpacing:
                ".08em",
            }}
          >
            TOP OPPORTUNITY
          </div>

          <strong
            style={{
              display:
                "block",

              marginTop:
                "5px",

              color:
                "#7df0aa",

              fontSize:
                "16px",
            }}
          >
            {topSymbol}
          </strong>

          <span
            style={{
              color:
                "#ffffff",

              fontSize:
                "11px",
            }}
          >
            {topScore > 0
              ? topScore.toFixed(1)
              : "—"}
          </span>
        </div>
      </div>

      {error && (
        <div
          style={{
            marginTop:
              "10px",

            color:
              "#ff8d8d",

            fontSize:
              "10px",
          }}
        >
          Live Edge API:{" "}
          {error}
        </div>
      )}
    </section>
  );
}
