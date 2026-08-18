"use client";

import {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  ColorType,
  createChart,
  TickMarkType,
  UTCTimestamp,
} from "lightweight-charts";

export type Candle = {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

type OhlcState = {
  open: number;
  high: number;
  low: number;
  close: number;
  changePercent: number;
  time: number;
} | null;

function ema(
  values: Candle[],
  period = 20,
) {
  if (!values.length) {
    return [];
  }

  const multiplier =
    2 / (period + 1);

  let previous =
    values[0]?.close ?? 0;

  return values.map(
    (item) => {
      previous =
        (item.close - previous) *
          multiplier +
        previous;

      return {
        time:
          item.time as UTCTimestamp,
        value: previous,
      };
    }
  );
}

function formatIstTime(
  timestamp: number,
  interval: string,
) {
  const date =
    new Date(
      timestamp * 1000
    );

  if (
    interval === "15s" ||
    interval === "1m" ||
    interval === "5m" ||
    interval === "15m"
  ) {
    return new Intl.DateTimeFormat(
      "en-IN",
      {
        timeZone:
          "Asia/Kolkata",
        hour:
          "2-digit",
        minute:
          "2-digit",
        second:
          interval === "15s"
            ? "2-digit"
            : undefined,
        hour12:
          false,
      }
    ).format(date);
  }

  if (
    interval === "1D"
  ) {
    return new Intl.DateTimeFormat(
      "en-IN",
      {
        timeZone:
          "Asia/Kolkata",
        day:
          "2-digit",
        month:
          "short",
      }
    ).format(date);
  }

  if (
    interval === "1W"
  ) {
    return new Intl.DateTimeFormat(
      "en-IN",
      {
        timeZone:
          "Asia/Kolkata",
        month:
          "short",
        year:
          "2-digit",
      }
    ).format(date);
  }

  if (
    interval === "1M"
  ) {
    return new Intl.DateTimeFormat(
      "en-IN",
      {
        timeZone:
          "Asia/Kolkata",
        year:
          "numeric",
      }
    ).format(date);
  }

  return "";
}

function formatCrosshairTime(
  timestamp: number,
  interval: string,
) {
  const date =
    new Date(
      timestamp * 1000
    );

  const intraday =
    interval === "15s" ||
    interval === "1m" ||
    interval === "5m" ||
    interval === "15m";

  if (intraday) {
    return new Intl.DateTimeFormat(
      "en-IN",
      {
        timeZone:
          "Asia/Kolkata",
        day:
          "2-digit",
        month:
          "short",
        year:
          "numeric",
        hour:
          "2-digit",
        minute:
          "2-digit",
        second:
          interval === "15s"
            ? "2-digit"
            : undefined,
        hour12:
          false,
      }
    ).format(date);
  }

  return new Intl.DateTimeFormat(
    "en-IN",
    {
      timeZone:
        "Asia/Kolkata",
      day:
        "2-digit",
      month:
        "short",
      year:
        "numeric",
    }
  ).format(date);
}

function getBarSpacing(
  interval: string,
) {
  switch (
    interval
  ) {
    case "15s":
      return 9;

    case "1m":
      return 8;

    case "5m":
      return 9;

    case "15m":
      return 10;

    case "1D":
      return 8;

    case "1W":
      return 9;

    case "1M":
      return 10;

    default:
      return 8;
  }
}

function getVisibleCount(
  interval: string,
) {
  switch (
    interval
  ) {
    case "15s":
      return 80;

    case "1m":
      return 100;

    case "5m":
      return 100;

    case "15m":
      return 100;

    case "1D":
      return 120;

    case "1W":
      return 104;

    case "1M":
      return 72;

    default:
      return 100;
  }
}

function calculateOhlc(
  candle: Candle,
): OhlcState {
  const changePercent =
    candle.open !== 0
      ? (
          (
            candle.close
            - candle.open
          )
          / candle.open
        ) * 100
      : 0;

  return {
    open:
      candle.open,
    high:
      candle.high,
    low:
      candle.low,
    close:
      candle.close,
    changePercent,
    time:
      candle.time,
  };
}

export default function StockChart({
  data,
  interval = "5m",
}: {
  data: Candle[];
  interval?: string;
}) {
  const target =
    useRef<HTMLDivElement>(
      null
    );

  const visibleRangeRef =
    useRef<{
      from: number;
      to: number;
    } | null>(
      null
    );

  const [
    ohlc,
    setOhlc,
  ] = useState<OhlcState>(
    data.length
      ? calculateOhlc(
          data[
            data.length - 1
          ]
        )
      : null
  );

  useEffect(() => {
    if (
      data.length > 0
    ) {
      setOhlc(
        calculateOhlc(
          data[
            data.length - 1
          ]
        )
      );
    } else {
      setOhlc(null);
    }
  }, [
    data,
  ]);

  useEffect(() => {
    if (
      !target.current
    ) {
      return;
    }

    const chart =
      createChart(
        target.current,
        {
          autoSize:
            true,

          height:
            430,

          layout: {
            background: {
              type:
                ColorType.Solid,
              color:
                "#07100b",
            },

            textColor:
              "#8da294",
          },

          grid: {
            vertLines: {
              color:
                "#122319",
            },

            horzLines: {
              color:
                "#122319",
            },
          },

          rightPriceScale: {
            borderColor:
              "#1d3525",

            scaleMargins: {
              top:
                0.08,
              bottom:
                0.18,
            },
          },

          timeScale: {
            borderColor:
              "#1d3525",

            timeVisible:
              interval === "15s" ||
              interval === "1m" ||
              interval === "5m" ||
              interval === "15m",

            secondsVisible:
              interval === "15s",

            rightOffset:
              4,

            barSpacing:
              getBarSpacing(
                interval
              ),

            minBarSpacing:
              4,

            fixLeftEdge:
              false,

            fixRightEdge:
              false,

            rightBarStaysOnScroll:
              true,

            tickMarkFormatter: (
              time: number,
              _tickMarkType:
                TickMarkType,
            ) => {
              if (
                typeof time ===
                "number"
              ) {
                return formatIstTime(
                  time,
                  interval
                );
              }

              return "";
            },
          },

          localization: {
            timeFormatter: (
              time: number,
            ) => {
              if (
                typeof time ===
                "number"
              ) {
                return formatCrosshairTime(
                  time,
                  interval
                );
              }

              return "";
            },
          },

          crosshair: {
            vertLine: {
              color:
                "#557065",
              width:
                1,
              labelBackgroundColor:
                "#263a31",
            },

            horzLine: {
              color:
                "#557065",
              width:
                1,
              labelBackgroundColor:
                "#263a31",
            },
          },
        }
      );

    const candles =
      chart
        .addCandlestickSeries({
          upColor:
            "#00c853",

          downColor:
            "#ff1744",

          borderVisible:
            true,

          borderUpColor:
            "#00c853",

          borderDownColor:
            "#ff1744",

          wickUpColor:
            "#00c853",

          wickDownColor:
            "#ff1744",

          priceLineVisible:
            true,

          lastValueVisible:
            true,

          priceFormat: {
            type:
              "price",
            precision:
              2,
            minMove:
              0.05,
          },
        });

    const volume =
      chart
        .addHistogramSeries({
          priceFormat: {
            type:
              "volume",
          },

          priceScaleId:
            "volume",
        });

    volume
      .priceScale()
      .applyOptions({
        scaleMargins: {
          top:
            0.82,

          bottom:
            0,
        },
      });

    const movingAverage =
      chart
        .addLineSeries({
          color:
            "#F5C451",

          lineWidth:
            2,

          title:
            "EMA 20",

          priceLineVisible:
            false,

          lastValueVisible:
            true,
        });

    const normalizedData =
      data.map(
        (item) => ({
          ...item,

          time:
            item.time as
              UTCTimestamp,
        })
      );

    candles.setData(
      normalizedData
    );

    volume.setData(
      normalizedData.map(
        (item) => ({
          time:
            item.time,

          value:
            item.volume,

          color:
            item.close >=
            item.open
              ? "rgba(0,200,83,0.40)"
              : "rgba(255,23,68,0.40)",
        })
      )
    );

    movingAverage.setData(
      ema(
        data
      )
    );

    const timeScale =
      chart.timeScale();

    const visibleCount =
      getVisibleCount(
        interval
      );

    if (
      data.length >
      visibleCount
    ) {
      timeScale
        .setVisibleLogicalRange({
          from:
            data.length
            - visibleCount,

          to:
            data.length
            + 3,
        });
    } else {
      timeScale
        .fitContent();
    }

    const handleVisibleRangeChange = (
      range:
        | {
            from: number;
            to: number;
          }
        | null,
    ) => {
      if (range) {
        visibleRangeRef
          .current = {
            from:
              range.from,
            to:
              range.to,
          };
      }
    };

    timeScale
      .subscribeVisibleLogicalRangeChange(
        handleVisibleRangeChange
      );

    chart
      .subscribeCrosshairMove(
        (param) => {
          if (
            !param.time
          ) {
            if (
              data.length > 0
            ) {
              setOhlc(
                calculateOhlc(
                  data[
                    data.length - 1
                  ]
                )
              );
            }

            return;
          }

          const seriesData =
            param.seriesData.get(
              candles
            );

          if (
            !seriesData ||
            !(
              "open"
              in seriesData
            )
          ) {
            return;
          }

          const candle =
            seriesData as {
              time:
                UTCTimestamp;

              open:
                number;

              high:
                number;

              low:
                number;

              close:
                number;
            };

          const open =
            Number(
              candle.open
            );

          const close =
            Number(
              candle.close
            );

          const changePercent =
            open !== 0
              ? (
                  (
                    close - open
                  )
                  / open
                )
                * 100
              : 0;

          setOhlc({
            open,
            high:
              Number(
                candle.high
              ),
            low:
              Number(
                candle.low
              ),
            close,
            changePercent,
            time:
              Number(
                candle.time
              ),
          });
        }
      );

    return () => {
      timeScale
        .unsubscribeVisibleLogicalRangeChange(
          handleVisibleRangeChange
        );

      chart.remove();
    };
  }, [
    data,
    interval,
  ]);

  return (
    <div>
      <div
        style={{
          display:
            "flex",

          alignItems:
            "center",

          flexWrap:
            "wrap",

          gap:
            "12px",

          minHeight:
            "28px",

          marginBottom:
            "8px",

          padding:
            "0 4px",

          fontSize:
            "10px",
        }}
      >
        {ohlc ? (
          <>
            <span
              style={{
                color:
                  "#71869c",
              }}
            >
              {formatCrosshairTime(
                ohlc.time,
                interval
              )}
            </span>

            <span>
              O{" "}
              <strong>
                {ohlc.open.toFixed(
                  2
                )}
              </strong>
            </span>

            <span>
              H{" "}
              <strong>
                {ohlc.high.toFixed(
                  2
                )}
              </strong>
            </span>

            <span>
              L{" "}
              <strong>
                {ohlc.low.toFixed(
                  2
                )}
              </strong>
            </span>

            <span>
              C{" "}
              <strong>
                {ohlc.close.toFixed(
                  2
                )}
              </strong>
            </span>

            <span
              style={{
                color:
                  ohlc.changePercent >=
                  0
                    ? "#00c853"
                    : "#ff1744",

                fontWeight:
                  700,
              }}
            >
              {ohlc.changePercent >=
              0
                ? "+"
                : ""}
              {ohlc.changePercent.toFixed(
                2
              )}
              %
            </span>
          </>
        ) : (
          <span
            style={{
              color:
                "#71869c",
            }}
          >
            No candle data
          </span>
        )}
      </div>

      <div
        ref={
          target
        }

        className=
          "w-full"

        aria-label={
          `Candlestick chart for ${interval} candles with EMA 20 and volume`
        }
      />
    </div>
  );
}