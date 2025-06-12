import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

# ─── CONFIG ────────────────────────────────────────────────────────────────────
MT5_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"
ACCOUNT   = 92214559
PASSWORD  = "E_HrX6Wp"
SERVER    = "MetaQuotes-Demo"
# ────────────────────────────────────────────────────────────────────────────────

def main():
    # 1) start MT5 and login
    if not mt5.initialize(path=MT5_PATH):
        print("❌ MT5 initialize() failed")
        return
    if not mt5.login(ACCOUNT, password=PASSWORD, server=SERVER):
        print("❌ MT5 login failed")
        mt5.shutdown()
        return
    print("✅ MT5 initialized & logged in")

    # 2) define time window
    utc_to   = datetime.utcnow()
    utc_from = utc_to - timedelta(days=365*2)  # last 2 years

    # 3) fetch 15 m bars
    rates = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M15, utc_from, utc_to)
    mt5.shutdown()

    # 4) convert to DataFrame & timestamp
    df15 = pd.DataFrame(rates)
    df15['time'] = pd.to_datetime(df15['time'], unit='s')

    # 5) save CSV
    out_file = "confluence_detector/XAUUSD_15m.csv"
    df15.to_csv(out_file, index=False)
    print(f"✅ Saved {len(df15)} bars to {out_file}")

if __name__ == "__main__":
    main()
