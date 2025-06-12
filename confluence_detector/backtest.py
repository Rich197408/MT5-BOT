# confluence_detector/backtest.py

import pandas as pd
from .detect import load_csv, detect_fvg, detect_order_blocks, detect_breaker_blocks

# ── PARAMETERS ─────────────────────────────────────────────────────────────────
SL_PIPS = 35      # stop-loss in pips
TP_PIPS = 70      # take-profit in pips
PIP_VAL  = 0.1    # on XAUUSD, 1 pip = 0.1 price units

# ── SIMULATION ─────────────────────────────────────────────────────────────────
def simulate_signal(df, idx, direction):
    entry = df.at[idx, "c"]
    sl = entry - SL_PIPS * PIP_VAL if direction == "bullish" else entry + SL_PIPS * PIP_VAL
    tp = entry + TP_PIPS * PIP_VAL if direction == "bullish" else entry - TP_PIPS * PIP_VAL

    for j in range(idx + 1, len(df)):
        low, high = df.at[j, "l"], df.at[j, "h"]
        # TP first
        if (direction == "bullish" and high >= tp) or (direction == "bearish" and low <= tp):
            return True
        # then SL
        if (direction == "bullish" and low <= sl)  or (direction == "bearish" and high >= sl):
            return False
    return False  # no hit = loss

# ── BACKTEST ───────────────────────────────────────────────────────────────────
def run_backtest():
    for label, fname in (("30 m", "XAUUSD_30m.csv"), ("1 h", "XAUUSD_1h.csv")):
        df      = load_csv(fname)
        fvg     = detect_fvg(df).assign(kind="FVG")
        ob      = detect_order_blocks(df).assign(kind="OB")
        bb      = detect_breaker_blocks(df).assign(kind="BB")
        signals = pd.concat([fvg, ob, bb], ignore_index=True)

        wins = 0
        for _, sig in signals.iterrows():
            idxs = df.index[df["time"] == sig["time"]]
            if idxs.empty:
                continue
            if simulate_signal(df, idxs[0], sig["type"]):
                wins += 1

        total = len(signals)
        # ←–– fixed inner quotes to single-quotes so the f-string parses
        print(f"\n=== {label} TF ===")
        print(f"Signals: FVG={(signals['kind']=='FVG').sum()}, "
              f"OB={(signals['kind']=='OB').sum()}, "
              f"BB={(signals['kind']=='BB').sum()}")
        print(f"Trades: {total}, Win rate: {wins/total*100:.1f}%")

if __name__ == "__main__":
    run_backtest()
