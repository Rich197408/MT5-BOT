# confluence_detector/backtest_fixed.py
import pandas as pd
from .detect import load_csv, detect_fvg, detect_order_blocks, detect_breaker_blocks, get_session

# ─── PARAMETERS ───────────────────────────────────────────────────────────
SL_PIPS = 40
TP_PIPS = 80

def run_backtest():
    for tf_name, fname in [("30 m TF", "XAUUSD_30m.csv"), ("1 h TF", "XAUUSD_1h.csv")]:
        df = load_csv(fname)
        # gather all signals into one DataFrame
        fvg = detect_fvg(df)
        ob  = detect_order_blocks(df)
        bb  = detect_breaker_blocks(df)
        signals = pd.concat([fvg, ob, bb], ignore_index=True)
        signals = signals.sort_values("time").reset_index(drop=True)

        wins = 0
        total = 0

        # iterate through each signal and simulate 1-bar-ahead entry
        for idx, sig in signals.iterrows():
            t0 = sig.time
            kind = sig.type
            sess = sig.session

            # find the next bar
            future = df[df.time > t0]
            if future.empty:
                continue
            bar1 = future.iloc[0]
            entry = bar1.c
            if kind == "bullish":
                sl = entry - SL_PIPS * 0.1
                tp = entry + TP_PIPS * 0.1
            else:
                sl = entry + SL_PIPS * 0.1
                tp = entry - TP_PIPS * 0.1

            # scan forward until SL or TP is hit
            hit = None
            for _, nb in future.iterrows():
                if kind == "bullish":
                    if nb.l <= sl:
                        hit = False
                        break
                    if nb.h >= tp:
                        hit = True
                        break
                else:
                    if nb.h >= sl:
                        hit = False
                        break
                    if nb.l <= tp:
                        hit = True
                        break

            if hit is None:
                continue
            wins += int(hit)
            total += 1

        win_rate = wins / total * 100 if total else 0
        print(f"=== {tf_name} ===")
        print(f"Signals: {len(signals)}, Trades: {total}, Win rate: {win_rate:.1f}%\n")


if __name__ == "__main__":
    run_backtest()
