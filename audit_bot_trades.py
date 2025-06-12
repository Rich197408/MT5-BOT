# audit_bot_trades.py

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import os

# ───── CONFIG ─────────────────────────────────────────────────────────────
SYMBOL       = "XAUUSD"
MAGIC        = 123456

# assume these CSVs live next to this script:
TF_PATHS     = {
    "30m": "XAUUSD_30m.csv",
    "1h":  "XAUUSD_1h.csv"
}

ATR_LEN      = 14
ACTIVE_HOURS = set(range(7,24))
# ────────────────────────────────────────────────────────────────────────────

def detect_fvg(df):
    out = {}
    for i in range(2, len(df)):
        if df.at[i-2,'high'] < df.at[i,'low']:
            out[i] = "bullish"
        elif df.at[i-2,'low'] > df.at[i,'high']:
            out[i] = "bearish"
    return out

def detect_ob(df):
    out = {}
    for i in range(1, len(df)-1):
        prev, cur, nxt = df.loc[i-1], df.loc[i], df.loc[i+1]
        if prev['close'] < prev['open'] and nxt['close'] > cur['close']:
            out[i] = "bullish"
        elif prev['close'] > prev['open'] and nxt['close'] < cur['close']:
            out[i] = "bearish"
    return out

def audit():
    # 1) fetch open positions
    if not mt5.initialize():
        print("Error: MT5 init failed")
        return
    positions = mt5.positions_get(symbol=SYMBOL) or []
    mt5.shutdown()

    # build DataFrame of bot positions
    rows = []
    for p in positions:
        if p.magic != MAGIC:
            continue
        rows.append({
            "ticket":   p.ticket,
            "side":     "BUY" if p.type==mt5.ORDER_TYPE_BUY else "SELL",
            "lots":     p.volume,
            "entry":    p.price_open,
            "entry_ts": datetime.fromtimestamp(p.time)
        })
    if not rows:
        print("No open positions for bot.")
        return
    dfp = pd.DataFrame(rows)

    audits = []
    for tf_label, filename in TF_PATHS.items():
        if not os.path.isfile(filename):
            print(f"CSV not found: {filename}")
            continue

        # load CSV
        df = pd.read_csv(filename, parse_dates=['time'])
        df.rename(columns={'open':'open','high':'high','low':'low','close':'close'}, inplace=True)

        # compute ATR14 & median
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = (df[['high','prev_close']].max(axis=1) - 
                    df[['low','prev_close']].min(axis=1))
        df['atr'] = df['tr'].rolling(ATR_LEN).mean()
        atr_med = df['atr'].median()

        # detect patterns
        fvg = detect_fvg(df)
        ob  = detect_ob(df)

        # audit each open trade
        for _, pos in dfp.iterrows():
            # find the bar whose timestamp is the last one ≤ entry time
            mask = df['time'] <= pos['entry_ts']
            if not mask.any():
                continue
            bar = df.loc[mask, :].iloc[-1]
            idx = bar.name

            # only consider bars in London/NY hours
            hr = bar['time'].hour
            if hr not in ACTIVE_HOURS:
                sess = "off-hours"
            else:
                sess = "active"

            audits.append({
                "ticket":      pos['ticket'],
                "tf":          tf_label,
                "bar_time":    bar['time'],
                "session":     sess,
                "atr":         round(bar['atr'], 4),
                "atr_med":     round(atr_med, 4),
                "fvg":         fvg.get(idx, ""),
                "ob":          ob.get(idx, ""),
                "confluence":  (1 if idx in fvg else 0) + (1 if idx in ob else 0)
            })

    df_audit = pd.DataFrame(audits)
    if df_audit.empty:
        print("No matching bars found for open trades.")
    else:
        print("\n=== Audit of Open Trades ===")
        print(df_audit.to_string(index=False))

if __name__ == "__main__":
    audit()
