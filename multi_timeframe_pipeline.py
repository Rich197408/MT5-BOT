import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from ta import add_all_ta_features
from ta.utils import dropna
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit, cross_val_score

# 1. Attach to MT5
if not mt5.initialize():
    print("❌ Could not attach to MT5:", mt5.last_error())
    mt5.shutdown()
    exit()

# 2. Fetch raw bars
#    - 1h: 2000 bars
#    - 4h:  500 bars
#    - 30m: 4000 bars
df1h  = pd.DataFrame(mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H1,  0, 2000))
df4h  = pd.DataFrame(mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H4,  0, 500))
df30m = pd.DataFrame(mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_M30, 0, 4000))
mt5.shutdown()

# 3. Convert timestamps
for df in (df1h, df4h, df30m):
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)

# 4. Rename & resample
df1h  = df1h[['open','high','low','close','tick_volume']]

df4h = df4h[['open','high','low','close','tick_volume']]\
       .rename(columns=lambda c: f"{c}_4h")\
       .resample('1H').ffill()

df30m = df30m[['open','high','low','close','tick_volume']]\
        .rename(columns=lambda c: f"{c}_30m")\
        .resample('1H').last().ffill()

# 5. Merge on the 1 h index
df = df1h.join([df4h, df30m], how='inner')

# 6. Compute TA features on each block of columns
#    We'll loop through suffixes '', '_4h', '_30m'
feat_dfs = []
for suffix in ['', '_4h', '_30m']:
    cols = [f"open{suffix}", f"high{suffix}", f"low{suffix}", f"close{suffix}", f"tick_volume{suffix}"]
    sub = df[cols].copy()
    # dropna then add TA (it will create many new cols named e.g. close_mfi)
    sub_clean = dropna(sub)
    sub_ta = add_all_ta_features(
        sub_clean,
        open=cols[0], high=cols[1], low=cols[2],
        close=cols[3], volume=cols[4],
        fillna=True
    )
    # rename TA cols to include the suffix
    sub_ta = sub_ta.add_suffix(suffix)
    feat_dfs.append(sub_ta)

# 7. Concatenate all TA features
df_feat = pd.concat(feat_dfs, axis=1).dropna()

# 8. Build the target & split
df_feat['target'] = (df['close'].shift(-1) > df['close']).astype(int)
df_feat.dropna(inplace=True)

split = int(len(df_feat) * 0.8)
train = df_feat.iloc[:split]
test  = df_feat.iloc[split:]
X_train, y_train = train.drop('target', axis=1), train['target']
X_test,  y_test  = test.drop('target', axis=1),  test['target']

# 9. Train & evaluate baseline RF
model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
tscv = TimeSeriesSplit(n_splits=5)
cv_scores = cross_val_score(model, X_train, y_train, cv=tscv, scoring='accuracy')
print(f"CV accuracy (multi‑TF RF): {np.mean(cv_scores):.3f} ± {np.std(cv_scores):.3f}")

model.fit(X_train, y_train)
test_acc = model.score(X_test, y_test)
print(f"Test accuracy (multi‑TF RF): {test_acc:.3f}")
# 10. Quick backtest of signals vs. buy‑&‑hold
preds = model.predict(X_test)
rets  = test['close'].pct_change().shift(-1).iloc[:-1]
strat = (preds[:-1] * rets).add(1).cumprod() - 1
bh    = rets.add(1).cumprod() - 1

print(f"Strategy return: {strat.iloc[-1]:.2%}")
print(f"Buy‑&‑Hold return: {bh.iloc[-1]:.2%}")



