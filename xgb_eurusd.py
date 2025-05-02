import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from ta import add_all_ta_features
from ta.utils import dropna
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit, cross_val_score

# 1. Attach & fetch data
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

# 2. Engineer features & target
df = dropna(df)
df_feat = add_all_ta_features(
    df,
    open="open", high="high", low="low",
    close="close", volume="tick_volume",
    fillna=True
)
df_feat['target'] = (df_feat['close'].shift(-1) > df_feat['close']).astype(int)
df_feat.dropna(inplace=True)

# 3. Split (80/20)
split = int(len(df_feat) * 0.8)
train = df_feat.iloc[:split]
test  = df_feat.iloc[split:]
X_train, y_train = train.drop('target', axis=1), train['target']
X_test,  y_test  = test.drop('target', axis=1),  test['target']

# 4. Initialize XGBoost
model = XGBClassifier(
    use_label_encoder=False,
    eval_metric='logloss',
    n_estimators=200,
    max_depth=5,
    learning_rate=0.1,
    n_jobs=-1,
    random_state=42
)

# 5. Cross‑validate
tscv = TimeSeriesSplit(n_splits=5)
cv_scores = cross_val_score(model, X_train, y_train, cv=tscv, scoring='accuracy')
print(f"XGB CV accuracy: {np.mean(cv_scores):.3f} ± {np.std(cv_scores):.3f}")

# 6. Train & test
model.fit(X_train, y_train)
test_acc = model.score(X_test, y_test)
print(f"Test accuracy: {test_acc:.3f}")

# 7. Quick backtest
preds = model.predict(X_test)
rets = test['close'].pct_change().shift(-1).iloc[:-1]
strategy_ret = (preds[:-1] * rets).add(1).cumprod() - 1
bh_ret       = rets.add(1).cumprod() - 1
print(f"Strategy return: {strategy_ret.iloc[-1]:.2%}, Buy‑Hold: {bh_ret.iloc[-1]:.2%}")

