import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pandas as pd

SYMBOL  = "XAUUSD"
MAGIC   = 1234501
ATR_LEN = 14

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
        prev,cur,nxt = df.iloc[i-1], df.iloc[i], df.iloc[i+1]
        if prev.close < prev.open and nxt.close > cur.close:
            out[i] = "bullish"
        elif prev.close > prev.open and nxt.close < cur.close:
            out[i] = "bearish"
    return out

def audit():
    if not mt5.initialize():
        print("MT5 init failed"); return
    pos = [p for p in mt5.positions_get(symbol=SYMBOL) or []
           if p.magic==MAGIC]
    mt5.shutdown()
    if not pos:
        print("No live bot positions"); return

    last = max(pos, key=lambda p: p.time)
    entry_ts = datetime.fromtimestamp(last.time)
    print("Last trade:", last.ticket, last.type, entry_ts)

    for tf_name, tf in [("30m", mt5.TIMEFRAME_M30),
                        ("1h",  mt5.TIMEFRAME_H1)]:
        # grab 100 bars around entry_ts
        bars = mt5.copy_rates_range(SYMBOL, tf,
                 entry_ts - timedelta(hours=2),
                 entry_ts + timedelta(hours=2))
        df = pd.DataFrame(bars)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        # compute ATR
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high','prev_close']].max(axis=1) - \
                   df[['low','prev_close']].min(axis=1)
        df['atr'] = df['tr'].rolling(ATR_LEN).mean()
        atr_med = df['atr'].median()

        fvg = detect_fvg(df)
        ob  = detect_ob(df)

        # find bar idx just ≤ entry_ts
        idx = df[df['time']<=entry_ts].index.max()
        bar = df.loc[idx]
        print(f"\n[{tf_name}] Bar @ {bar.time}")
        print(f" O={bar.open}, H={bar.high}, L={bar.low}, C={bar.close}")
        print(f" ATR={bar.atr:.3f} (med={atr_med:.3f})")
        print(" FVG:", fvg.get(idx))
        print(" OB:",  ob.get(idx))
        print(" Confluence:", (1 if idx in fvg else 0)+(1 if idx in ob else 0))

if __name__=="__main__":
    audit()
