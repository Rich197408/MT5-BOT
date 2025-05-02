from fetch_eurusd_attach import fetch_mt5_ohlcv
from features import engineer_features

# 1. Fetch raw data for EURUSD at 1h
df_raw = fetch_mt5_ohlcv("EURUSD", "1h", 500)
if df_raw.empty:
    print("No raw data fetched for EURUSD @ 1h")
    exit()

# 2. Engineer features from that DataFrame
df_features = engineer_features(df_raw)

# 3. Display sample feature names and values
print("Sample feature columns:", df_features.columns.tolist()[:10])
print(df_features[['close', 'volume_adi', 'momentum_rsi']].tail())
