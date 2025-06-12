#!/usr/bin/env python3
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# ───── CONFIG ─────────────────────────────────────────────────────────────
MT5_PATH    = r"C:\Program Files\MetaTrader 5\terminal64.exe"
LOGIN_ACC   = 92214559
LOGIN_PASS  = "E_HrX6Wp"
LOGIN_SRV   = "MetaQuotes-Demo"
SYMBOL      = "XAUUSD"
TIMEFRAMES  = {
    "30m": mt5.TIMEFRAME_M30,
    "1h":  mt5.TIMEFRAME_H1,
}
SL_PIPS     = 35
TP_PIPS     = 70
BE_PIPS     = 20
LOT_SIZE    = 0.5
PIP_VALUE   = 0.1
# ────────────────────────────────────────────────────────────────────────────

def detect_fvg(df):
    zones = []
    for i in range(2, len(df)):
        if df.high.iat[i-2] < df.low.iat[i]:
            zones.append((i, df.high.iat[i-2], df.low.iat[i], "bull"))
        elif df.low.iat[i-2] > df.high.iat[i]:
            zones.append((i, df.high.iat[i], df.low.iat[i-2], "bear"))
    return zones

def detect_ob(df):
    zones = []
    for i in range(1, len(df)-1):
        prev, cur, nxt = df.iloc[i-1], df.iloc[i], df.iloc[i+1]
        if prev.close < prev.open and nxt.close > cur.close:
            zones.append((i, cur.low, cur.high, "bull"))
        elif prev.close > prev.open and nxt.close < cur.close:
            zones.append((i, cur.low, cur.high, "bear"))
    return zones

def find_retest(df, zones):
    hits = {}
    for idx, lo, hi, direction in zones:
        for j in range(idx+1, len(df)):
            if df.low.iat[j] <= hi and df.high.iat[j] >= lo:
                hits.setdefault(j, []).append(direction)
                break
    return hits

def backtest_tf(label, tf_const, start, end):
    rates = mt5.copy_rates_range(SYMBOL, tf_const, start, end)
    df    = pd.DataFrame(rates)
    if df.empty:
        return None
    df['time'] = pd.to_datetime(df['time'], unit='s')

    fvg_z = detect_fvg(df)
    ob_z  = detect_ob(df)
    ret_f = find_retest(df, fvg_z)
    ret_o = find_retest(df, ob_z)

    trades = []
    for idx in sorted(set(ret_f.keys()) & set(ret_o.keys())):
        dirs = set(ret_f[idx]) & set(ret_o[idx])
        if not dirs:
            continue
        direction = dirs.pop()
        entry     = df.at[idx, 'close']
        sl        = (entry - SL_PIPS * PIP_VALUE) if direction=='bull' else (entry + SL_PIPS * PIP_VALUE)
        tp        = (entry + TP_PIPS * PIP_VALUE) if direction=='bull' else (entry - TP_PIPS * PIP_VALUE)

        # simulate forward until SL or TP
        for j in range(idx+1, len(df)):
            hi, lo = df.high.iat[j], df.low.iat[j]
            # check SL
            if (direction=='bull' and lo <= sl) or (direction=='bear' and hi >= sl):
                trades.append(('loss', SL_PIPS))
                break
            # check TP
            if (direction=='bull' and hi >= tp) or (direction=='bear' and lo <= tp):
                # did we hit BE first?
                be_hit = False
                for k in range(idx+1, j+1):
                    h, l = df.high.iat[k], df.low.iat[k]
                    if (direction=='bull' and h >= entry + BE_PIPS*PIP_VALUE) or \
                       (direction=='bear' and l <= entry - BE_PIPS*PIP_VALUE):
                        be_hit = True
                        break
                trades.append(('win_be', 0) if be_hit else ('win_tp', TP_PIPS))
                break

    wins   = sum(1 for t,_ in trades if t.startswith('win'))
    losses = sum(1 for t,_ in trades if t=='loss')
    total  = len(trades)
    win_rate   = (wins/total*100) if total else 0.0
    weeks      = (end - start).days / 7
    weekly_pnl = ((wins*TP_PIPS - losses*SL_PIPS) / weeks) * LOT_SIZE * PIP_VALUE * 100

    return {
        "Timeframe":      label,
        "Total Trades":   total,
        "Wins":           wins,
        "Losses":         losses,
        "Win Rate (%)":   round(win_rate, 2),
        "Est Weekly PnL": round(weekly_pnl, 2),
    }

def main():
    # initialize & login
    if not mt5.initialize(path=MT5_PATH):
        print("❌ MT5 init failed:", mt5.last_error())
        return
    if not mt5.login(LOGIN_ACC, LOGIN_PASS, LOGIN_SRV):
        print("❌ MT5 login failed:", mt5.last_error())
        mt5.shutdown()
        return

    end   = datetime.now()
    start = end - relativedelta(months=6)
    results = []

    for label, tf in TIMEFRAMES.items():
        out = backtest_tf(label, tf, start, end)
        if out:
            results.append(out)

    mt5.shutdown()

    if results:
        df = pd.DataFrame(results)
        print(df.to_string(index=False))
    else:
        print("No data or signals found.")

if __name__ == "__main__":
    main()
