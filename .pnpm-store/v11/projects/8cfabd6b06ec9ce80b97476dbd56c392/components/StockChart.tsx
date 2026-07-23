"use client";

import { useEffect, useRef } from "react";
import { ColorType, createChart } from "lightweight-charts";

export type Candle = { time: number; open: number; high: number; low: number; close: number; volume: number };

function ema(values: Candle[], period = 20) {
  const multiplier = 2 / (period + 1);
  let previous = values[0]?.close ?? 0;
  return values.map((item) => {
    previous = (item.close - previous) * multiplier + previous;
    return { time: item.time, value: previous };
  });
}

export default function StockChart({ data }: { data: Candle[] }) {
  const target = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!target.current) return;
    const chart = createChart(target.current, {
      autoSize: true,
      height: 430,
      layout: { background: { type: ColorType.Solid, color: "#0b120d" }, textColor: "#8ba28f" },
      grid: { vertLines: { color: "#142317" }, horzLines: { color: "#142317" } },
      rightPriceScale: { borderColor: "#1c3321" },
      timeScale: { borderColor: "#1c3321", timeVisible: true },
    });
    const candles = chart.addCandlestickSeries({ upColor: "#36ef75", downColor: "#f25d6b", borderVisible: false, wickUpColor: "#36ef75", wickDownColor: "#f25d6b" });
    const volume = chart.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "volume", color: "#1c9c4a" });
    volume.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    const movingAverage = chart.addLineSeries({ color: "#f5c451", lineWidth: 2, title: "EMA 20" });
    candles.setData(data);
    volume.setData(data.map((item) => ({ time: item.time, value: item.volume, color: item.close >= item.open ? "#1d8d46" : "#7f3540" })));
    movingAverage.setData(ema(data));
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [data]);

  return <div ref={target} className="w-full" aria-label="Candlestick chart with EMA 20 and volume" />;
}
