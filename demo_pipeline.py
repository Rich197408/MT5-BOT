import MetaTrader5 as mt5
import pandas as pd
from ta import add_all_ta_features
from ta.utils import dropna

# 1. Attach to the already-running MT5 terminal
if not mt5.initialize():
    print("❌ Could not attach to MT5, error code:", mt5.last_error())
    mt5.shutdown()
    exit()
print("✅ Attached to MT5")

# 2. Fetch function
def fetch_ohlcv(symbol, timeframe, n_bars=500):
    tf_map = {
        "30m": mt5.TIMEFRAME_M30,
        "1h":  mt5.TIMEFRAME_H1,
        "4h":  mt5.TIMEFRAME_H4,
        "1d":  mt5.TIMEFRAME_D1,
    }
    rates = mt5.copy_rates_from_pos(symbol, tf_map[timeframe], 0, n_bars)
    if rates is None or len(rates) == 0:
        return pd.DataFrame()
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df.set_index('time')[['open','high','low','close','tick_volume']]

# 3. Pull raw data
symbol = "EURUSD"
timeframe = "1h"
df_raw = fetch_ohlcv(symbol, timeframe, 500)
if df_raw.empty:
    print(f"⚠️ No data fetched for {symbol} @ {timeframe}")
    mt5.shutdown()
    exit()
print(f"🔹 Fetched {len(df_raw)} bars for {symbol} @ {timeframe}")

# 4. Feature engineering
df_clean = dropna(df_raw)
df_feat  = add_all_ta_features(
    df_clean,
    open="open", high="high", low="low",
    close="close", volume="tick_volume",
    fillna=True
)

# 5. Display results
print("\nSample feature columns:", df_feat.columns.tolist()[:8])
print("\nLast 5 rows:\n", df_feat[['close','volume_adi','momentum_rsi']].tail())

# 6. Clean up
mt5.shutdown()
