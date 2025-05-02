import MetaTrader5 as mt5
import pandas as pd
from ta import add_all_ta_features
from ta.utils import dropna
from sklearn.ensemble import RandomForestClassifier
from joblib import dump

# 1. Attach to MT5 & fetch multi‑TF bars
if not mt5.initialize():
    print("❌ Could not attach to MT5:", mt5.last_error())
    mt5.shutdown()
    exit()

rates1h  = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H1,  0, 2000)
rates4h  = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H4,  0, 500)
rates30m = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_M30, 0, 4000)
mt5.shutdown()

# 2. Build pandas DataFrames
df1h  = pd.DataFrame(rates1h).assign(time=lambda d: pd.to_datetime(d['time'],unit='s')).set_index('time')[['open','high','low','close','tick_volume']]
df4h  = pd.DataFrame(rates4h).assign(time=lambda d: pd.to_datetime(d['time'],unit='s')).set_index('time')[['open','high','low','close','tick_volume']].add_suffix('_4h').resample('1H').ffill()
df30m = pd.DataFrame(rates30m).assign(time=lambda d: pd.to_datetime(d['time'],unit='s')).set_index('time')[['open','high','low','close','tick_volume']].add_suffix('_30m').resample('1H').last().ffill()

# 3. Merge & engineer TA features
df = df1h.join([df4h, df30m], how='inner')
parts = []
for suf in ['', '_4h', '_30m']:
    cols = [f'open{suf}', f'high{suf}', f'low{suf}', f'close{suf}', f'tick_volume{suf}']
    sub = dropna(df[cols])
    ta  = add_all_ta_features(sub, open=cols[0], high=cols[1], low=cols[2], close=cols[3], volume=cols[4], fillna=True).add_suffix(suf)
    parts.append(ta)
df_feat = pd.concat(parts, axis=1).dropna()

# 4. Create target & align
df_feat['target'] = (df['close'].shift(-1) > df['close']).astype(int)
df_feat.dropna(inplace=True)

# 5. Train & save the RandomForest
X = df_feat.drop('target', axis=1)
y = df_feat['target']
model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
model.fit(X, y)
dump(model, 'multi_tf_rf.pkl')
print("✅ Trained model saved to multi_tf_rf.pkl")

