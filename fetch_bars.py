#!/usr/bin/env python3
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

# ───── CONFIG ─────────────────────────────────────────────────────────────
MT5_PATH      = r"C:\Program Files\MetaTrader 5\terminal64.exe"
LOGIN_ACCOUNT = 92214559
LOGIN_PASS    = "E_HrX6Wp"
LOGIN_SERVER  = "MetaQuotes-Demo"
SYMBOL        = "XAUUSD"
FROM_DATE     = datetime(2025, 5, 21, 0, 0)
TO_DATE       = datetime(2025, 5, 23, 0, 0)
# ────────────────────────────────────────────────────────────────────────────

mt5.initialize(path=MT5_PATH)
mt5.login(LOGIN_ACCOUNT, LOGIN_PASS, LOGIN_SERVER)
mt5.symbol_select(SYMBOL, True)

for tf_name, tf_const in [("30m", mt5.TIMEFRAME_M30), ("1h", mt5.TIMEFRAME_H1)]:
    rates = mt5.copy_rates_range(SYMBOL, tf_const, FROM_DATE, TO_DATE)
    if rates is None or len(rates)==0:
        print(f"No data for {tf_name}")
        continue

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    filename = f"XAUUSD_{tf_name}_2025-05-21_22.csv"
    df.to_csv(filename, index=False)
    print(f"Saved {len(df)} bars to {filename}")

mt5.shutdown()
