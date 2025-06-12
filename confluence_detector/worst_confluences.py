#!/usr/bin/env python
import pandas as pd
from confluence_detector.detect import load_csv, detect_fvg, detect_order_blocks, detect_breaker_blocks

def worst_confluences(df, name):
    """Compute win‐rate per confluence type and return the 10 worst."""
    # collect all signals
    sigs = pd.concat([
        detect_fvg(df).assign(signal="FVG"),
        detect_order_blocks(df).assign(signal="OB"),
        detect_breaker_blocks(df).assign(signal="BB"),
    ], ignore_index=True)

    # backtest each one with your 1:2 RR logic
    results = []
    for typ, group in sigs.groupby("signal"):
        wins = 0
        for _, row in group.iterrows():
            price = df.set_index("time").loc[row["time"], "c"]
            sl = price - 0.35 if row["type"] == "bullish" else price + 0.35
            tp = price + 0.70 if row["type"] == "bullish" else price - 0.70
            window = df[df["time"] > row["time"]].head(20)  # look 20 bars ahead
            if row["type"] == "bullish":
                if (window["h"] >= tp).any():
                    wins += 1
            else:
                if (window["l"] <= tp).any():
                    wins += 1
        n = len(group)
        results.append((name, typ, n, wins / n if n else None))

    res_df = pd.DataFrame(results, columns=["TF","signal","n","win_rate"])
    return res_df.sort_values("win_rate").head(10)

def main():
    df30 = load_csv("confluence_detector/XAUUSD_30m.csv")
    df60 = load_csv("confluence_detector/XAUUSD_1h.csv")

    print("\nWorst 10 confluences on 30 m TF:")
    print(worst_confluences(df30, "30 m").to_string(index=False))

    print("\nWorst 10 confluences on 1 h TF:")
    print(worst_confluences(df60, "1 h").to_string(index=False))

if __name__ == "__main__":
    main()
