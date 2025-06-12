import MetaTrader5 as mt5
import pandas as pd
import os
from datetime import datetime

# 1) Initialize and connect to MT5. Make sure MT5 is running and logged in.
if not mt5.initialize():
    print("MT5 initialize() failed")
    mt5.shutdown()
    exit()

# 2) Define symbol and time range.
symbol = "XAUUSD"
# Ensure the terminal has that symbol in Market Watch.
utc_from = datetime(2025, 1, 1)
utc_to   = datetime(2025, 6, 5, 23, 59)  # up to end of June 5

# 3) Request 5 minute bars
rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, utc_from, utc_to)
if rates is None or len(rates) == 0:
    print("No data returned. Check symbol or time range.")
    mt5.shutdown()
    exit()

# 4) Build DataFrame
df5 = pd.DataFrame(rates)
# 'time' is a Unix timestamp in seconds. Convert to datetime.
df5['time'] = pd.to_datetime(df5['time'], unit='s')
df5 = df5.set_index('time')
# Keep only open, high, low, close (volume is optional)
df5 = df5[['open', 'high', 'low', 'close', 'tick_volume']]

# 5) Save to CSV in the same folder
output_path = os.path.join(os.getcwd(), "XAUUSD_5m.csv")
df5.to_csv(output_path)
print(f"Saved {len(df5)} bars to {output_path}")

# 6) Clean up
mt5.shutdown()
