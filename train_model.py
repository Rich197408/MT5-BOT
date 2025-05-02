import MetaTrader5 as mt5
import pandas as pd
from ta import add_all_ta_features
from ta.utils import dropna
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
import numpy as np

# 1. Attach to MT5
if not mt5.initialize():
    print("❌ Could not attach to MT5:", mt5.last_error())
    mt5.shutdown()
    exit()

# 2. Fetch raw 1h EURUSD bars
rates = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H1, 0, 2000)
mt5.shutdown()
if rates is None or len(rates)==0:
    print("⚠️ No data fetched.")
    exit()
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)
df = df[['open','high','low','close','tick_volume']]

# 3. Engineer features + target
df_clean = dropna(df)
df_feat  = add_all_ta_features(
    df_clean,
    open="open", high="high", low="low",
    close="close", volume="tick_volume",
    fillna=True
)
# binary target: next-bar close > current
df_feat['target'] = (df_feat['close'].shift(-1) > df_feat['close']).astype(int)
df_feat = df_feat.dropna()

# 4. Train/test split (80/20 chronological)
split = int(len(df_feat)*0.8)
train = df_feat.iloc[:split]
test  = df_feat.iloc[split:]
X_train = train.drop('target', axis=1)
y_train = train['target']
X_test  = test.drop('target', axis=1)
y_test  = test['target']

# 5. Cross-validate and train RandomForest
model = RandomForestClassifier(n_estimators=100, random_state=42)
tscv  = TimeSeriesSplit(n_splits=5)
scores = cross_val_score(model, X_train, y_train, cv=tscv, scoring='accuracy')
print(f'CV accuracy: {np.mean(scores):.3f} ± {np.std(scores):.3f}')

model.fit(X_train, y_train)
test_acc = model.score(X_test, y_test)
print(f'Test accuracy: {test_acc:.3f}')

# 6. Quick backtest: go long when predict 1
preds = model.predict(X_test)
rets = test['close'].pct_change().shift(-1).iloc[:-1]
strategy = (preds[:-1] * rets).add(1).cumprod() - 1
bh = rets.add(1).cumprod() - 1
print(f"Strategy return: {strategy.iloc[-1]:.2%}, Buy&Hold: {bh.iloc[-1]:.2%}")
