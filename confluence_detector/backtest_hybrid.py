#!/usr/bin/env python
import pandas as pd
from confluence_detector.detect import load_csv, detect_fvg, detect_order_blocks, detect_breaker_blocks

def compute_atr(df, period=14):
    # True Range components
    df['prev_c'] = df['c'].shift(1)
    tr1 = df['h'] - df['l']
    tr2 = (df['h'] - df['prev_c']).abs()
    tr3 = (df['l'] - df['prev_c']).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def run_backtest_hybrid():
    for tf, fname in [("30 m", "XAUUSD_30m.csv"), ("1 h", "XAUUSD_1h.csv")]:
        df = load_csv(fname)
        atr = compute_atr(df)

        # gather all signals into one DataFrame
        sigs = pd.concat([
            detect_fvg(df),
            detect_order_blocks(df),
            detect_breaker_blocks(df)
        ], ignore_index=True)

        # look up ATR at each signal time
        atr_map = pd.Series(atr.values, index=df['time'])
        sigs['atr'] = sigs['time'].map(atr_map)

        # convert ATR in price‐units to pips (1 pip = 0.1 in XAUUSD)
        sigs['atr_pips'] = sigs['atr'] / 0.1

        # SL = max(ATR,p35), TP = 2×SL
        sigs['sl_pips'] = sigs['atr_pips'].apply(lambda x: max(x, 35))
        sigs['tp_pips'] = sigs['sl_pips'] * 2

        wins = 0
        total = 0

        for _, row in sigs.iterrows():
            # find the bar index where this signal occurred
            idx = df.index[df['time'] == row['time']][0]
            entry = df.at[idx, 'c']
            direction = 1 if row['type'] == 'bullish' else -1

            sl_price = entry - direction * row['sl_pips'] * 0.1
            tp_price = entry + direction * row['tp_pips'] * 0.1

            # walk forward until SL or TP is hit
            result = None
            for j in range(idx+1, len(df)):
                h, l = df.at[j, 'h'], df.at[j, 'l']
                if direction == 1:
                    if l <= sl_price:
                        result = False
                        break
                    if h >= tp_price:
                        result = True
                        break
                else:
                    if h >= sl_price:
                        result = False
                        break
                    if l <= tp_price:
                        result = True
                        break

            if result is not None:
                wins += result
                total += 1

        win_rate = (wins / total * 100) if total else 0
        print(f"=== {tf} TF (hybrid ATR/35-pip SL → TP=2×SL) ===")
        print(f"Signals tested: {len(sigs)}, Trades: {total}, Win rate: {win_rate:.1f}%\n")

if __name__ == "__main__":
    run_backtest_hybrid()
