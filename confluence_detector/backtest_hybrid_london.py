#!/usr/bin/env python
import pandas as pd
from confluence_detector.detect import (
    load_csv,
    detect_fvg,
    detect_order_blocks,
    detect_breaker_blocks,
    get_session,
)

def compute_atr(df, period=14):
    df["prev_c"] = df["c"].shift(1)
    tr1 = df["h"] - df["l"]
    tr2 = (df["h"] - df["prev_c"]).abs()
    tr3 = (df["l"] - df["prev_c"]).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def run_backtest_london_1h():
    # only 1 h timeframe
    df = load_csv("XAUUSD_1h.csv")
    atr = compute_atr(df)

    # collect signals
    sigs = pd.concat([
        detect_fvg(df),
        detect_order_blocks(df),
        detect_breaker_blocks(df),
    ], ignore_index=True)

    # keep London only
    sigs = sigs[sigs["session"] == "london"]

    # map ATR to each signal time
    atr_series = pd.Series(atr.values, index=df["time"])
    sigs["atr"] = sigs["time"].map(atr_series)
    # convert to pips (1 pip = 0.1)
    sigs["atr_pips"] = sigs["atr"] / 0.1

    # SL = max(ATR,35), TP = 2×SL
    sigs["sl_pips"] = sigs["atr_pips"].apply(lambda x: max(x, 35))
    sigs["tp_pips"] = sigs["sl_pips"] * 2

    wins = 0
    total = 0

    for _, row in sigs.iterrows():
        idx = df.index[df["time"] == row["time"]][0]
        entry = df.at[idx, "c"]
        dir_ = 1 if row["type"] == "bullish" else -1

        sl_price = entry - dir_ * row["sl_pips"] * 0.1
        tp_price = entry + dir_ * row["tp_pips"] * 0.1

        result = None
        for j in range(idx + 1, len(df)):
            h, l = df.at[j, "h"], df.at[j, "l"]
            if dir_ == 1:
                if l <= sl_price:
                    result = False; break
                if h >= tp_price:
                    result = True; break
            else:
                if h >= sl_price:
                    result = False; break
                if l <= tp_price:
                    result = True; break

        if result is not None:
            wins += result
            total += 1

    wr = wins / total * 100 if total else 0
    print(f"=== 1 h TF (London only, hybrid ATR/35-pip SL → TP=2×SL) ===")
    print(f"Signals tested: {len(sigs)}, Trades: {total}, Win rate: {wr:.1f}%")

if __name__ == "__main__":
    run_backtest_london_1h()
