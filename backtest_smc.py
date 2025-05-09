#!/usr/bin/env python3
import argparse
import pandas as pd
from collections import Counter
from strategies import SMCStrategy

# ─── CONFIG ────────────────────────────────────────────────────────────────
CSV_1H   = "XAUUSD_1h.csv"
CSV_4H   = "XAUUSD_4h.csv"
CSV_30M  = "XAUUSD_30m.csv"
# ─────────────────────────────────────────────────────────────────────────────

def load_csv(path: str) -> pd.DataFrame:
    return (
        pd.read_csv(path, parse_dates=["time"], index_col="time")
          .sort_index()
    )

def make_multi_tf_df() -> pd.DataFrame:
    df1h = load_csv(CSV_1H).add_suffix("_1h")
    df1h.index.name = "time"

    df4h = (
        load_csv(CSV_4H)
        .resample("1h").ffill()
        .add_suffix("_4h")
    )
    df4h.index.name = "time"

    df30m = (
        load_csv(CSV_30M)
        .resample("1h").last().ffill()
        .add_suffix("_30m")
    )
    df30m.index.name = "time"

    # Join on the 1h index
    return df1h.join([df4h, df30m], how="inner")

def main(min_conf: float, limit: int):
    df = make_multi_tf_df()

    # Apply limit for speed
    if limit and limit > 0:
        df = df.tail(limit)

    start, end = df.index[0], df.index[-1]
    total_bars = len(df)
    print(f"Loaded {total_bars} bars from {start:%Y-%m-%d %H:%M} to {end:%Y-%m-%d %H:%M}")

    strat = SMCStrategy("XAUUSD")

    # Counter for all non-neutral confidences
    dist = Counter()

    header_printed = False
    for idx, ts in enumerate(df.index, start=1):
        # simple progress indicator
        if idx % 50 == 0 or idx == total_bars:
            print(f"Processing {idx}/{total_bars} bars…", end="\r")

        df_slice = df.iloc[:idx]
        sig, conf = strat.generate_signal(df_slice)
        if sig != "NEUTRAL":
            # record this confidence
            dist[conf] += 1

            # if it meets your min_conf filter, print it
            if conf >= min_conf:
                if not header_printed:
                    print("\n\n{:<20}  {:<6} {}".format("Timestamp", "Signal", "Conf"))
                    print("-"*40)
                    header_printed = True
                print(f"{ts:%Y-%m-%d %H:%M}  {sig:<6} {conf:.3f}")

    # Summary of printed signals
    if not header_printed:
        print(f"\nNo signals ≥{min_conf:.3f} confidence in those {total_bars} bars.")
    else:
        print("\nDone printing filtered signals.\n")

    # Distribution of ALL non-neutral confidences
    if dist:
        print("Signal Confidence Distribution (all non-neutral):")
        print("{:<10} {:>8}".format("Confidence", "Count"))
        print("-"*20)
        for c in sorted(dist):
            print(f"{c:<10.3f} {dist[c]:>8}")
    else:
        print("No non-neutral signals detected at all (dist is empty).")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Backtest SMCStrategy on XAUUSD")
    p.add_argument("--min-conf", type=float, default=0.0,
                   help="Only print signals with confidence ≥ this (0.0–1.0)")
    p.add_argument("--limit",    type=int,   default=200,
                   help="Only process the last N hourly bars (speed)")
    args = p.parse_args()
    main(args.min_conf, args.limit)
