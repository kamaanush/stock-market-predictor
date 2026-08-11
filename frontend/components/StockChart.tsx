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
        value: previous,
      };
    },
  );
}

function formatIstTime(
  timestamp: number,
  interval: string,
) {
  const date =
    new Date(timestamp * 1000);

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
        hour: "2-digit",
        minute: "2-digit",
        second:
          interval === "15s"
            ? "2-digit"
            : undefined,
        hour12: false,
      },
    ).format(date);
  }

  return new Intl.DateTimeFormat(
    "en-IN",
    {
      timeZone:
        "Asia/Kolkata",
      day: "2-digit",
      month: "short",
    },
  ).format(date);
}

function formatIstCrosshairTime(
  timestamp: number,
  interval: string,
) {
  const date =
    new Date(timestamp * 1000);

  return new Intl.DateTimeFormat(
    "en-IN",
    {
      timeZone:
        "Asia/Kolkata",
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second:
        interval === "15s"
          ? "2-digit"
          : undefined,
      hour12: false,
    },
  ).format(date);
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
      null,
    );

  const visibleRangeRef =
    useRef<{
      from: number;
      to: number;
    } | null>(null);

  useEffect(() => {
    if (!target.current) {
      return;
    }

    const chart =
      createChart(
        target.current,
        {
          autoSize: true,
          height: 430,

          layout: {
            background: {
              type:
                ColorType.Solid,
              color:
                "#0b120d",
            },
            textColor:
              "#8ba28f",
          },

          grid: {
            vertLines: {
              color:
                "#142317",
            },
            horzLines: {
              color:
                "#142317",
            },
          },

          rightPriceScale: {
            borderColor:
              "#1c3321",
          },

          timeScale: {
            borderColor:
              "#1c3321",

            timeVisible: true,

            secondsVisible:
              interval ===
              "15s",

            tickMarkFormatter: (
              time: number,
              _tickMarkType: TickMarkType,
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

            rightOffset: 4,
            barSpacing:
              interval === "15s"
                ? 8
                : interval === "1m"
                  ? 7
                  : interval === "5m"
                    ? 8
                    : 9,
          },

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

    const candles =
      chart
        .addCandlestickSeries({
          upColor:
            "#36ef75",
          downColor:
            "#f25d6b",
          borderVisible:
            false,
          wickUpColor:
            "#36ef75",
          wickDownColor:
            "#f25d6b",
        });

    const volume =
      chart
        .addHistogramSeries({
          priceFormat: {
            type: "volume",
          },
          priceScaleId:
            "volume",
          color:
            "#1c9c4a",
        });

    volume
      .priceScale()
      .applyOptions({
        scaleMargins: {
          top: 0.8,
          bottom: 0,
        },
      });

    const movingAverage =
      chart
        .addLineSeries({
          color:
            "#f5c451",
          lineWidth: 2,
          title:
            "EMA 20",
        });

    const normalizedData =
      data.map(
        (item) => ({
          ...item,
          time:
            item.time as UTCTimestamp,
        }),
      );

    candles.setData(
      normalizedData,
    );

    volume.setData(
      normalizedData.map(
        (item) => ({
          time: item.time,
          value:
            item.volume,
          color:
            item.close >=
            item.open
              ? "#1d8d46"
              : "#7f3540",
        }),
      ),
    );

    movingAverage.setData(
      ema(data),
    );

    const timeScale =
      chart.timeScale();

    const savedRange =
      visibleRangeRef.current;

    if (savedRange) {
      timeScale.setVisibleLogicalRange(
        savedRange,
      );
    } else {
      timeScale.fitContent();
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
        visibleRangeRef.current = {
          from: range.from,
          to: range.to,
        };
      }
    };

    timeScale.subscribeVisibleLogicalRangeChange(
      handleVisibleRangeChange,
    );

    return () => {
      timeScale.unsubscribeVisibleLogicalRangeChange(
        handleVisibleRangeChange,
      );

      chart.remove();
    };
  }, [
    data,
    interval,
  ]);

  return (
    <div
      ref={target}
      className="w-full"
      aria-label={`Candlestick chart for ${interval} candles with EMA 20 and volume`}
    />
  );
}