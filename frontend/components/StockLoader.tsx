"use client";

export default function StockLoader() {
  return (
    <div className="flex min-h-[430px] w-full items-center justify-center">
      <div className="flex flex-col items-center gap-5">

        {/* Stock candlestick loader */}
        <div className="flex h-16 items-end gap-2">

          <div className="flex h-10 flex-col items-center justify-center animate-pulse">
            <div className="h-3 w-[2px] bg-emerald-400" />
            <div className="h-5 w-2 rounded-sm bg-emerald-400" />
            <div className="h-2 w-[2px] bg-emerald-400" />
          </div>

          <div className="flex h-14 flex-col items-center justify-center animate-pulse">
            <div className="h-3 w-[2px] bg-red-400" />
            <div className="h-7 w-2 rounded-sm bg-red-400" />
            <div className="h-2 w-[2px] bg-red-400" />
          </div>

          <div className="flex h-16 flex-col items-center justify-center animate-pulse">
            <div className="h-4 w-[2px] bg-emerald-400" />
            <div className="h-8 w-2 rounded-sm bg-emerald-400" />
            <div className="h-2 w-[2px] bg-emerald-400" />
          </div>

          <div className="flex h-12 flex-col items-center justify-center animate-pulse">
            <div className="h-2 w-[2px] bg-red-400" />
            <div className="h-6 w-2 rounded-sm bg-red-400" />
            <div className="h-3 w-[2px] bg-red-400" />
          </div>

          <div className="flex h-16 flex-col items-center justify-center animate-pulse">
            <div className="h-3 w-[2px] bg-emerald-400" />
            <div className="h-9 w-2 rounded-sm bg-emerald-400" />
            <div className="h-3 w-[2px] bg-emerald-400" />
          </div>

        </div>

        {/* Spinner */}
        <div
          className="
            h-7
            w-7
            animate-spin
            rounded-full
            border-2
            border-emerald-950
            border-t-emerald-400
            border-r-emerald-400
          "
        />

      </div>
    </div>
  );
}