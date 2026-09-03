"use client";

type Props = {
  summary: any;
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

function signedPercent(
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

function signed(
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
    1,
  )}`;
}

function LeaderTable({
  title,
  subtitle,
  rows,
  direction,
}: {
  title: string;
  subtitle: string;
  rows: any[];
  direction:
    | "BULLISH"
    | "BEARISH";
}) {
  const positive =
    direction ===
    "BULLISH";

  const accent =
    positive
      ? "#00f59b"
      : "#ff647c";

  const border =
    positive
      ? "rgba(0,245,155,.22)"
      : "rgba(255,100,124,.22)";

  const background =
    positive
      ? "rgba(0,245,155,.035)"
      : "rgba(255,100,124,.035)";

  return (
    <div
      style={{
        minWidth: 0,

        border:
          `1px solid ${border}`,

        borderRadius:
          "10px",

        padding:
          "15px",

        background,
      }}
    >
      <div>
        <strong
          style={{
            color:
              accent,

            fontSize:
              "12px",
          }}
        >
          {title}
        </strong>

        <div
          style={{
            color:
              "#71869c",

            fontSize:
              "9px",

            marginTop:
              "4px",
          }}
        >
          {subtitle}
        </div>
      </div>

      <div
        style={{
          marginTop:
            "12px",

          overflowX:
            "auto",
        }}
      >
        <div
          style={{
            minWidth:
              "590px",
          }}
        >
          <div
            style={{
              display:
                "grid",

              gridTemplateColumns:
                "1.2fr .65fr .65fr .65fr .65fr .65fr",

              gap:
                "8px",

              padding:
                "0 0 7px",

              color:
                "#536d82",

              fontSize:
                "8px",

              fontWeight:
                800,

              letterSpacing:
                ".05em",
            }}
          >
            <span>STOCK</span>
            <span>OPP</span>
            <span>Δ OPP</span>
            <span>5M</span>
            <span>RS 5M</span>
            <span>RVOL</span>
          </div>

          {rows
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
                      "1.2fr .65fr .65fr .65fr .65fr .65fr",

                    gap:
                      "8px",

                    alignItems:
                      "center",

                    minHeight:
                      "48px",

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
                          "#e9faff",
                      }}
                    >
                      {
                        item.symbol
                      }
                    </strong>

                    <div
                      style={{
                        marginTop:
                          "3px",

                        display:
                          "flex",

                        gap:
                          "5px",

                        alignItems:
                          "center",
                      }}
                    >
                      <span
                        style={{
                          color:
                            accent,

                          fontSize:
                            "8px",

                          fontWeight:
                            800,
                        }}
                      >
                        {
                          item
                            .leader_tier
                        }
                      </span>

                      <span
                        style={{
                          color:
                            "#60788e",

                          fontSize:
                            "8px",
                        }}
                      >
                        {
                          item
                            .confirmation_count
                        }
                        /{
                          item
                            .confirmation_total
                        }
                      </span>
                    </div>
                  </div>

                  <strong>
                    {num(
                      item
                        .opportunity_score,
                    ).toFixed(
                      1,
                    )}
                  </strong>

                  <span
                    style={{
                      color:
                        num(
                          item
                            .opportunity_delta_1m,
                        ) > 0
                          ? "#00f59b"
                          : num(
                              item
                                .opportunity_delta_1m,
                            ) < 0
                            ? "#ff647c"
                            : "#71869c",
                    }}
                  >
                    {signed(
                      item
                        .opportunity_delta_1m,
                    )}
                  </span>

                  <span
                    style={{
                      color:
                        positive
                          ? "#7df0aa"
                          : "#ff8d9d",
                    }}
                  >
                    {signedPercent(
                      item
                        .change_5m_percent,
                    )}
                  </span>

                  <span
                    style={{
                      color:
                        positive
                          ? "#7df0aa"
                          : "#ff8d9d",
                    }}
                  >
                    {signedPercent(
                      item
                        .rs_5m_pct,
                    )}
                  </span>

                  <span>
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

          {rows.length ===
            0 && (
            <div
              style={{
                padding:
                  "18px 0",

                color:
                  "#71869c",

                fontSize:
                  "10px",
              }}
            >
              No qualifying{" "}
              {direction.toLowerCase()}{" "}
              leaders right now.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function DirectionalLeaders({
  summary,
}: Props) {
  const bullish =
    Array.isArray(
      summary
        ?.bullish_leaders,
    )
      ? summary
          .bullish_leaders
      : [];

  const bearish =
    Array.isArray(
      summary
        ?.bearish_leaders,
    )
      ? summary
          .bearish_leaders
      : [];

  return (
    <section
      style={{
        marginTop:
          "14px",
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

          marginBottom:
            "9px",
        }}
      >
        <div>
          <strong
            style={{
              color:
                "#35e8ff",

              fontSize:
                "11px",
            }}
          >
            DIRECTIONAL LEADERSHIP
          </strong>

          <div
            style={{
              marginTop:
                "4px",

              color:
                "#60788e",

              fontSize:
                "9px",
            }}
          >
            Movement + direction +
            NIFTY relative strength +
            volume participation
          </div>
        </div>

        <div
          style={{
            display:
              "flex",

            gap:
              "12px",

            fontSize:
              "9px",
          }}
        >
          <span
            style={{
              color:
                "#00f59b",
            }}
          >
            ▲ {
              bullish.length
            } BULLISH
          </span>

          <span
            style={{
              color:
                "#ff647c",
            }}
          >
            ▼ {
              bearish.length
            } BEARISH
          </span>
        </div>
      </div>

      <div
        style={{
          display:
            "grid",

          gridTemplateColumns:
            "repeat(auto-fit, minmax(420px,1fr))",

          gap:
            "12px",
        }}
      >
        <LeaderTable
          title="🟢 BULLISH LEADERS"
          subtitle="Price rising + outperforming NIFTY"
          rows={bullish}
          direction="BULLISH"
        />

        <LeaderTable
          title="🔴 BEARISH LEADERS"
          subtitle="Price falling + underperforming NIFTY"
          rows={bearish}
          direction="BEARISH"
        />
      </div>

      <div
        style={{
          marginTop:
            "7px",

          color:
            "#50677c",

          fontSize:
            "8px",
        }}
      >
        Leadership ranking is
        context only — not a
        BUY/SELL probability.
      </div>
    </section>
  );
}
