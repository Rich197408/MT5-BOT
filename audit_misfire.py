# audit_misfire.py

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import os

# ───── CONFIG ─────────────────────────────────────────────────────────────
SYMBOL    = "XAUUSD"
MAGIC     = 1234501           # ← updated to match your bot's magic from open positions
ATR_LEN   = 14
TF_CSV    = {
    "30m": "XAUUSD_30m.csv",
    "1h":  "XAUUSD_1h.csv"
}
# ────────────────────────────────────────────────────────────────────────────

def detect_fvg(df):
    out = {}
    for i in range(2, len(df)):
        if df.high.iat[i-2] < df.low.iat[i]:
            out[i] = "bullish"
        elif df.low.iat[i-2] > df.high.iat[i]:
            out[i] = "bearish"
    return out

def detect_ob(df):
    out = {}
    for i in range(1, len(df)-1):
        prev, cur, nxt = df.iloc[i-1], df.iloc[i], df.iloc[i+1]
        if prev.close < prev.open and nxt.close > cur.close:
            out[i] = "bullish"
        elif prev.close > prev.open and nxt.close < cur.close:
            out[i] = "bearish"
    return out

def main():
    # 1) Fetch all open XAUUSD positions
    if not mt5.initialize():
        print("Error: MT5 init failed")
        return
    all_pos = mt5.positions_get(symbol=SYMBOL) or []
    mt5.shutdown()

    if not all_pos:
        print("No open positions for", SYMBOL)
        return

    # Print all open positions
    print("Open Positions:")
    for p in all_pos:
        side = "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL"
        print(f"  ticket={p.ticket}, magic={p.magic}, side={side}, lots={p.volume}, entry={p.price_open}")

    # Filter to your bot's magic
    bot_pos = [p for p in all_pos if p.magic == MAGIC]
    if not bot_pos:
        print(f"\nNo positions found with magic={MAGIC}. Check magic number!")
        return

    # Use the most recent bot position
    last = max(bot_pos, key=lambda p: p.time)
    entry_ts = datetime.fromtimestamp(last.time)
    side_str = "BUY" if last.type == mt5.ORDER_TYPE_BUY else "SELL"
    print(f"\nLast bot trade: ticket={last.ticket}, side={side_str}, lots={last.volume}, time={entry_ts}\n")

    # 2) Audit on each timeframe
    for label, fname in TF_CSV.items():
        if not os.path.isfile(fname):
            print(f"CSV missing: {fname}")
            continue

        df = pd.read_csv(fname, parse_dates=["time"])
        df.rename(columns={'open':'open','high':'high','low':'low','close':'close'}, inplace=True)

        # Compute ATR14
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high','prev_close']].max(axis=1) - df[['low','prev_close']].min(axis=1)
        df['atr'] = df['tr'].rolling(ATR_LEN).mean()
        atr_med = df['atr'].median()

        fvg = detect_fvg(df)
        ob  = detect_ob(df)

        # locate bar at or before entry_ts
        mask = df['time'] <= entry_ts
        if not mask.any():
            print(f"{label}: no bar ≤ {entry_ts}")
            continue

        bar = df.loc[mask].iloc[-1]
        idx = bar.name

        print(f"[{label}] Bar @ {bar.time}")
        print(f"  O={bar.open:.2f}, H={bar.high:.2f}, L={bar.low:.2f}, C={bar.close:.2f}")
        print(f"  ATR={bar.atr:.4f} (median={atr_med:.4f})")
        print(f"  FVG? {fvg.get(idx, False)}")
        print(f"  OB?  {ob.get(idx, False)}")
        conf = (1 if idx in fvg else 0) + (1 if idx in ob else 0)
        print(f"  Confluence count = {conf}\n")

if __name__ == "__main__":
    main()

