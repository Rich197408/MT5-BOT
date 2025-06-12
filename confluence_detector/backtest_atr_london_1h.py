# backtest_atr_london_1h.py
import pandas as pd
from confluence_detector.detect import (
    load_csv,
    detect_fvg,
    detect_order_blocks,
    detect_breaker_blocks,
    get_session
)

def compute_atr(df, period=14):
    # True Range components
    high_low = df['h'] - df['l']
    high_prev = (df['h'] - df['c'].shift(1)).abs()
    low_prev  = (df['l'] - df['c'].shift(1)).abs()
    tr = pd.concat([high_low, high_prev, low_prev], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()

def run_backtest_atr_london_1h(
    fname="XAUUSD_1h.csv",
    atr_period=14,
    sl_atr_mult=1.0,
    tp_atr_mult=2.0
):
    # 1) load & parse
    df = load_csv(fname)
    df['session'] = df['time'].apply(get_session)
    atr = compute_atr(df, period=atr_period)
    df = df.assign(atr=atr)

    # 2) detect all signals
    fvg = detect_fvg(df)
    ob  = detect_order_blocks(df)
    bb  = detect_breaker_blocks(df)
    signals = pd.concat([fvg, ob, bb], ignore_index=True)

    # 3) filter down to London session only
    sig = signals[signals['session']=="london"].copy()
    sig = sig.merge(df.set_index('time')[['o','h','l','c','atr']], how='left', left_on='time', right_index=True)

    # 4) simulate each trade
    wins = 0
    total = 0

    for _, row in sig.iterrows():
        entry = row['c']
        sl = entry - row['atr'] * sl_atr_mult if row['type']=="bullish" else entry + row['atr'] * sl_atr_mult
        tp = entry + row['atr'] * tp_atr_mult if row['type']=="bullish" else entry - row['atr'] * tp_atr_mult

        # slice forward to find first hit
        future = df[df['time'] > row['time']]
        hit = None
        for _, f in future.iterrows():
            if row['type']=="bullish":
                if f['l'] <= sl:
                    hit = 'SL'; break
                if f['h'] >= tp:
                    hit = 'TP'; break
            else:
                if f['h'] >= sl:
                    hit = 'SL'; break
                if f['l'] <= tp:
                    hit = 'TP'; break
        if hit=='TP':
            wins += 1
        total += 1

    # 5) output
    win_rate = wins/total*100 if total else 0.0
    print(f"\n=== 1 h TF (London only, ATR SL={sl_atr_mult}×ATR, TP={tp_atr_mult}×ATR) ===")
    print(f"Signals tested: {total:,}")
    print(f"Win rate: {win_rate:.1f}%  ({wins:,} wins out of {total:,})\n")

if __name__=="__main__":
    run_backtest_atr_london_1h()
