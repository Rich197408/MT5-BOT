# audit_closed_misfire.py

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import os

# ───── CONFIG ─────────────────────────────────────────────────────────────
SYMBOL    = "XAUUSD"
MAGIC     = 1234501           # your bot’s magic number
ATR_LEN   = 14
TF_CSV    = {
    "30m": "XAUUSD_30m.csv",
    "1h":  "XAUUSD_1h.csv"
}
# ────────────────────────────────────────────────────────────────────────────

# Detection functions
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
    # 1) Init MT5 & fetch last open deal
    if not mt5.initialize():
        print("Error: MT5 init failed")
        return

    # Look back 1 day for open deals
    to_time = datetime.now()
    from_time = to_time - timedelta(days=1)
    deals = mt5.history_deals_get(from_time, to_time) or []
    mt5.shutdown()

    # Filter to your bot's open deals
    open_deals = [d for d in deals
                  if d.symbol == SYMBOL
                  and d.magic == MAGIC
                  and d.type in (mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL)]

    if not open_deals:
        print("No recent open deals found for your bot.")
        return

    # Most recent open deal
    last = max(open_deals, key=lambda d: d.time)
    entry_ts = datetime.fromtimestamp(last.time)
    side_str = "BUY" if last.type == mt5.DEAL_TYPE_BUY else "SELL"
    print(f"\nLast open deal: ticket={last.ticket}, side={side_str}, lots={last.volume}, time={entry_ts}\n")

    # 2) Audit on each timeframe
    for label, fname in TF_CSV.items():
        if not os.path.isfile(fname):
            print(f"{label}: CSV not found: {fname}")
            continue

        df = pd.read_csv(fname, parse_dates=["time"])
        df.rename(columns={'open':'open','high':'high','low':'low','close':'close'}, inplace=True)

        # Compute ATR(14)
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high','prev_close']].max(axis=1) - df[['low','prev_close']].min(axis=1)
        df['atr'] = df['tr'].rolling(ATR_LEN).mean()
        atr_med = df['atr'].median()

        fvg = detect_fvg(df)
        ob  = detect_ob(df)

        # Find the bar whose time <= entry_ts
        mask = df['time'] <= entry_ts
        if not mask.any():
            print(f"{label}: no bar <= {entry_ts}")
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

