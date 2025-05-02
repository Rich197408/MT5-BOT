import MetaTrader5 as mt5
import pandas as pd

# 1. Attach to MT5 (must have MT5 open & logged in)
if not mt5.initialize():
    print("❌ Could not attach to MT5:", mt5.last_error())
    mt5.shutdown()
    exit()

# 2. Fetch the last 2000 one‑hour EURUSD bars
rates = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H1, 0, 2000)
mt5.shutdown()

# 3. Check and convert to DataFrame
if rates is None or len(rates) == 0:
    print("⚠️ No data fetched.")
    exit()

df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)

# 4. Save the key columns to CSV
out_path = "EURUSD_1h.csv"
df[['open','high','low','close','tick_volume']].to_csv(out_path)
print(f"✅ Saved {len(df)} bars to {out_path}")



