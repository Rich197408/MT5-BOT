import pandas as pd
from .detect import (
    load_csv,
    detect_fvg,
    detect_order_blocks,
    detect_breaker_blocks,
    detect_bos_choch,
)

def run_backtest():
    """
    Runs 1:2 RR backtest (e.g. 40‐pip SL, 80‐pip TP),
    tagging each signal type and session.
    """
    # load both timeframes
    data30 = load_csv("XAUUSD_30m.csv")
    data60 = load_csv("XAUUSD_1h.csv")

    for label, df in [("30 m TF", data30), ("1 h TF", data60)]:
        # gather all signals
        signals = pd.concat([
            detect_fvg(df).assign(signal="FVG"),
            detect_order_blocks(df).assign(signal="OB"),
            detect_breaker_blocks(df).assign(signal="BB"),
            detect_bos_choch(df).assign(signal=lambda d: d["type"].str.upper()),
        ], ignore_index=True)

        # simulate trades at each signal bar:
        wins = 0
        for _, row in signals.iterrows():
            # find entry index
            idx = df.index[df["time"] == row["time"]].tolist()
            if not idx:
                continue
            i = idx[0]
            sl = df.loc[i, "c"] - 0.0040  if row["type"].startswith("bull") else df.loc[i, "c"] + 0.0040
            tp = df.loc[i, "c"] + 0.0080  if row["type"].startswith("bull") else df.loc[i, "c"] - 0.0080

            # look ahead until SL or TP hit
            outcome = None
            for j in range(i+1, min(i+50, len(df))):
                if row["type"].startswith("bullish") and df.loc[j, "l"] <= sl:
                    outcome = False; break
                if row["type"].startswith("bullish") and df.loc[j, "h"] >= tp:
                    outcome = True; break
                if row["type"].startswith("bearish") and df.loc[j, "h"] >= sl:
                    outcome = False; break
                if row["type"].startswith("bearish") and df.loc[j, "l"] <= tp:
                    outcome = True; break
            if outcome:
                wins += 1

        total = len(signals)
        win_rate = wins / total * 100 if total else 0
        print(f"\n=== {label} ===")
        print(f"Signals: {total}, Win rate: {win_rate:.1f}%\n")


if __name__ == "__main__":
    run_backtest()
