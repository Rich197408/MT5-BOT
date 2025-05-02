#!/usr/bin/env python3
# backtest_ict.py

import pandas as pd
from strategies import ICTStrategy

# ─── CONFIG ────────────────────────────────────────────
CSV_15M = "EURUSD_15m.csv"
CSV_30M = "EURUSD_30m.csv"
CSV_1H  = "EURUSD_1h.csv"
CSV_4H  = "EURUSD_4h.csv"

# Backtest window (inclusive)
START = "2024-12-20"
END   = pd.Timestamp.utcnow().strftime("%Y-%m-%d")

# Target frequency for alignment
COMMON_FREQ = "1H"


def load_and_suffix(path: str, tf: str, resample_freq: str) -> pd.DataFrame:
    """
    Load CSV at `path` (with columns time, open, high, low, close, volume),
    parse time → datetime index, rename OHLC → OHLC_{tf},
    then resample to `resample_freq` via last‐value / forward‐fill.
    """
    df = pd.read_csv(path, parse_dates=["time"], index_col="time")
    df = df.loc[START:END, ["open", "high", "low", "close"]]
    # rename
    df = df.rename(
        columns={
            "open":  f"open_{tf}",
            "high":  f"high_{tf}",
            "low":   f"low_{tf}",
            "close": f"close_{tf}",
        }
    )
    # resample + forward fill
    df = df.resample(resample_freq).last().ffill()
    return df


def main():
    # load & suffix each timeframe
    df15 = load_and_suffix(CSV_15M, "15m", COMMON_FREQ)
    df30 = load_and_suffix(CSV_30M, "30m", COMMON_FREQ)
    df1h = load_and_suffix(CSV_1H,  "1h",  COMMON_FREQ)
    df4h = load_and_suffix(CSV_4H,  "4h",  COMMON_FREQ)

    # join them side by side
    df_all = df15.join([df30, df1h, df4h], how="inner")

    strat = ICTStrategy("EURUSD")

    print(f"{'Timestamp':<20}  Signal  Confidence")
    print("-" * 42)

    # iterate row by row
    for ts, row in df_all.iterrows():
        # slice up to current ts
        slice_up_to_t = df_all.loc[:ts]
        sig, conf = strat.generate_signal(slice_up_to_t)
        print(f"{ts.strftime('%Y-%m-%d %H:%M')}  {sig:<5}   {conf:.2f}")

    print("\nDone.")


if __name__ == "__main__":
    main()
