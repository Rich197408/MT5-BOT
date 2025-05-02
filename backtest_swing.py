#!/usr/bin/env python3
import pandas as pd
from strategies import SwingStrategy

# ─── CONFIG ──────────────────────────────────────────────────
CSV_1H  = "EURUSD_1h.csv"

START = "2024-12-20"
END   = None

def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["time"], index_col="time")
    return df

def make_df() -> pd.DataFrame:
    return load_csv(CSV_1H).loc[START:END]

def main():
    df = make_df()
    strat = SwingStrategy("EURUSD")

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
