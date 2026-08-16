"use client";

import {
  useEffect,
  useRef,
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


// ==================================================
// EMA
// ==================================================

function ema(
  values: Candle[],
  period = 20,
) {
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

        value:
          previous,
      };
    },
  );
}


// ==================================================
// TIME FORMAT
// ==================================================

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
      },
    ).format(
      date
    );
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
      },
    ).format(
      date
    );
  }


  if (
    interval === "1W"
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
      },
    ).format(
      date
    );
  }


  return new Intl.DateTimeFormat(
    "en-IN",
    {
      timeZone:
        "Asia/Kolkata",

      month:
        "short",

      year:
        "2-digit",
    },
  ).format(
    date
  );
}


// ==================================================
// CROSSHAIR FORMAT
// ==================================================

function formatIstCrosshairTime(
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


  if (
    intraday
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
      },
    ).format(
      date
    );
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
    },
  ).format(
    date
  );
}


// ==================================================
// BAR SPACING
// ==================================================

function getBarSpacing(
  interval: string,
) {
  switch (
    interval
  ) {
    case "15s":
      return 10;

    case "1m":
      return 9;

    case "5m":
      return 10;

    case "15m":
      return 11;

    case "1D":
      return 12;

    case "1W":
      return 14;

    case "1M":
      return 16;

    default:
      return 10;
  }
}


// ==================================================
// CHART
// ==================================================

export default function StockChart({
  data,
  interval = "5m",
}: {
  data: Candle[];
  interval?: string;
}) {

  const target =
    useRef<
      HTMLDivElement
    >(
      null
    );


  const visibleRangeRef =
    useRef<{
      from: number;
      to: number;
    } | null>(
      null
    );


  useEffect(
    () => {

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


            // ======================================
            // BACKGROUND
            // ======================================

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


            // ======================================
            // GRID
            // ======================================

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


            // ======================================
            // PRICE SCALE
            // ======================================

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


            // ======================================
            // TIME SCALE
            // ======================================

           timeScale: {
  borderColor: "#1d3525",

  timeVisible: true,

  secondsVisible:
    interval === "15s",

  rightOffset: 6,

  barSpacing:
    interval === "15s"
      ? 10
      : interval === "1m"
        ? 12
        : interval === "5m"
          ? 14
          : interval === "15m"
            ? 16
            : interval === "1D"
              ? 18
              : interval === "1W"
                ? 20
                : interval === "1M"
                  ? 22
                  : 12,

  minBarSpacing: 8,

  fixLeftEdge: false,

  fixRightEdge: false,

  lockVisibleTimeRangeOnResize:
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
        interval,
      );
    }

    return "";
  },
},


            // ======================================
            // CROSSHAIR
            // ======================================

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


            // ======================================
            // LOCALIZATION
            // ======================================

            localization: {
              timeFormatter: (
                time: number,
              ) => {

                if (
                  typeof time ===
                  "number"
                ) {
                  return formatIstCrosshairTime(
                    time,
                    interval,
                  );
                }

                return "";
              },
            },
          },
        );


      // ============================================
      // ANGEL ONE STYLE CANDLES
      // ============================================

const candles =
  chart.addCandlestickSeries({
    upColor: "#00c853",
    downColor: "#ff1744",

    borderVisible: true,
    borderUpColor: "#00c853",
    borderDownColor: "#ff1744",

    wickUpColor: "#00c853",
    wickDownColor: "#ff1744",

    priceLineVisible: true,
    lastValueVisible: true,

    priceFormat: {
      type: "price",
      precision: 2,
      minMove: 0.05,
    },
  });


      // ============================================
      // VOLUME
      // ============================================

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


      // ============================================
      // EMA 20
      // ============================================

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


      // ============================================
      // NORMALIZE DATA
      // ============================================

      const normalizedData =
        data.map(
          (
            item
          ) => ({
            ...item,

            time:
              item.time as
                UTCTimestamp,
          }),
        );


      // ============================================
      // SET CANDLE DATA
      // ============================================

      candles.setData(
        normalizedData,
      );


      // ============================================
      // SET VOLUME DATA
      // ============================================

      volume.setData(
        normalizedData.map(
          (
            item
          ) => ({
            time:
              item.time,

            value:
              item.volume,

            color:
              item.close >=
              item.open
                ? "rgba(0,179,134,0.45)"
                : "rgba(235,91,91,0.45)",
          }),
        ),
      );


      // ============================================
      // EMA
      // ============================================

      movingAverage.setData(
        ema(
          data
        ),
      );


      const timeScale =
        chart.timeScale();


      const savedRange =
        visibleRangeRef
          .current;


      if (
        savedRange
      ) {
        timeScale
          .setVisibleLogicalRange(
            savedRange,
          );
      } else {

        if (
          data.length >
          80
        ) {

          timeScale
            .setVisibleLogicalRange({
              from:
                data.length -
                70,

              to:
                data.length +
                5,
            });

        } else {

          timeScale
            .fitContent();
        }
      }


      // ============================================
      // SAVE ZOOM POSITION
      // ============================================

      const handleVisibleRangeChange =
        (
          range:
            | {
                from:
                  number;

                to:
                  number;
              }
            | null,
        ) => {

          if (
            range
          ) {
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
          handleVisibleRangeChange,
        );


      return () => {

        timeScale
          .unsubscribeVisibleLogicalRangeChange(
            handleVisibleRangeChange,
          );

        chart.remove();
      };

    },
    [
      data,
      interval,
    ],
  );


  return (
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
  );
}