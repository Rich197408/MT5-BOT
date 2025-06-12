import MetaTrader5 as mt5
import pandas as pd
import os
from datetime import datetime, timedelta

# ─── CONFIG ────────────────────────────────────────────────────────────────────
MT5_PATH    = r"C:\Program Files\MetaTrader 5\terminal64.exe"
ACCOUNT     = 92214559
PASSWORD    = "E_HrX6Wp"
SERVER      = "MetaQuotes-Demo"
SYMBOL      = "XAUUSD"
DATA_DIR    = "confluence_detector"
YEARS_BACK  = 2

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize and login
if not mt5.initialize(path=MT5_PATH):
    raise RuntimeError(f"MT5 init failed, error code: {mt5.last_error()}")
if not mt5.login(ACCOUNT, password=PASSWORD, server=SERVER):
    raise RuntimeError(f"MT5 login failed, error code: {mt5.last_error()}")

# Helper to fetch and save CSV
def fetch_and_save(timeframe, filename):
    utc_to = datetime.utcnow()
    utc_from = utc_to - timedelta(days=YEARS_BACK * 365)
    rates = mt5.copy_rates_range(SYMBOL, timeframe, utc_from, utc_to)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"No data fetched for {timeframe}")
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    # reorder columns to match backtester
    df = df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]
    df.columns = ['time','o','h','l','c','v']
    df.to_csv(os.path.join(DATA_DIR, filename), index=False, header=False)
    print(f"Saved {len(df)} bars to {filename}")

# Fetch 15m and 4h
fetch_and_save(mt5.TIMEFRAME_M15, "XAUUSD_15m.csv")
fetch_and_save(mt5.TIMEFRAME_H4,  "XAUUSD_4h.csv")

mt5.shutdown()

print("Data fetch complete. Now rerun your backtest script to include 15m and 4h timeframes.")
