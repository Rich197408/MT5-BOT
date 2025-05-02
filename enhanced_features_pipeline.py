import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from ta import add_all_ta_features
from ta.utils import dropna
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit, cross_val_score

# 1. Attach & fetch
if not mt5.initialize():
    print("❌ Could not attach to MT5:", mt5.last_error())
    mt5.shutdown()
    exit()
rates = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H1, 0, 2000)
mt5.shutdown()

df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)
df = df[['open','high','low','close','tick_volume']]

# 2. Hand‑crafted features
df['ret_1']      = df['close'].pct_change(1)
df['ret_2']      = df['close'].pct_change(2)
df['ret_3']      = df['close'].pct_change(3)
df['ma_3']       = df['close'].rolling(3).mean()
df['ma_10']      = df['close'].rolling(10).mean()
df['vola_5']     = df['ret_1'].rolling(5).std()
df['vola_15']    = df['ret_1'].rolling(15).std()
df['hour']       = df.index.hour
df['dayofweek']  = df.index.dayofweek

# 3. Generic TA features (with suffix to avoid duplicate names)
df_clean = dropna(df)
df_ta = add_all_ta_features(
    df_clean, open="open", high="high", low="low",
    close="close", volume="tick_volume", fillna=True
).add_suffix("_ta")

# 4. Combine and drop any NaNs
df_feat = pd.concat([df, df_ta], axis=1).dropna()

# 5. Create binary target on the *single* close column
df_feat['target'] = (df_feat['close'].shift(-1) > df_feat['close']).astype(int)
df_feat.dropna(inplace=True)

# 6. Split chronologically
split = int(len(df_feat) * 0.8)
train = df_feat.iloc[:split]
test  = df_feat.iloc[split:]
X_train, y_train = train.drop('target', axis=1), train['target']
X_test,  y_test  = test.drop('target', axis=1),  test['target']

# 7. Train & CV
model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
tscv  = TimeSeriesSplit(n_splits=5)
scores= cross_val_score(model, X_train, y_train, cv=tscv, scoring='accuracy')
print(f"CV accuracy (enhanced features): {np.mean(scores):.3f} ± {np.std(scores):.3f}")

# 8. Final test eval
model.fit(X_train, y_train)
test_acc = model.score(X_test, y_test)
print(f"Test accuracy (enhanced features): {test_acc:.3f}")

# 9. Quick backtest
preds = model.predict(X_test)
rets = test['close'].pct_change().shift(-1).iloc[:-1]
strat = (preds[:-1] * rets).add(1).cumprod() - 1
bh    = rets.add(1).cumprod() - 1
print(f"Strategy return: {strat.iloc[-1]:.2%}, Buy‑Hold: {bh.iloc[-1]:.2%}")


