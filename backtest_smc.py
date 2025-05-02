#!/usr/bin/env python3
import pandas as pd
from strategies import SMCStrategy

# ─── CONFIG ──────────────────────────────────────────────────
CSV_1H  = "EURUSD_1h.csv"
CSV_4H  = "EURUSD_4h.csv"
CSV_30M = "EURUSD_30m.csv"

START = "2024-12-20"
END   = None   # up to last

def load_csv(path: str) -> pd.DataFrame:
    """Load CSV with time index."""
    return pd.read_csv(path, parse_dates=["time"], index_col="time")

def make_multi_tf_df() -> pd.DataFrame:
    # 1h with suffix "_1h"
    df1h = load_csv(CSV_1H).add_suffix("_1h")
    # fix index name
    df1h.index.name = "time"
    # 4h → resample to 1H, suffix "_4h"
    df4h = (
        load_csv(CSV_4H)
        .resample("1H").ffill()
        .add_suffix("_4h")
    )
    df4h.index.name = "time"
    # 30m → resample to 1H (take last), suffix "_30m"
    df30m = (
        load_csv(CSV_30M)
        .resample("1H").last().ffill()
        .add_suffix("_30m")
    )
    df30m.index.name = "time"

    # join on their common 1H index
    df = df1h.join([df4h, df30m], how="inner")
    return df.loc[START:END]

def main():
    df = make_multi_tf_df()
    strat = SMCStrategy("EURUSD")

    print(f"{'Timestamp':<20}  Signal  Confidence")
    print("-"*45)
    for ts in df.index:
        slice_up_to_t = df.loc[:ts]
        sig, conf = strat.generate_signal(slice_up_to_t)
        if sig != "NEUTRAL":
            print(f"{ts:%Y-%m-%d %H:%M}  {sig:<5}   {conf:.2f}")
    print("\nDone.")

if __name__ == "__main__":
    main()
