import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from ta import add_all_ta_features
from ta.utils import dropna
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectFromModel
from sklearn.model_selection import TimeSeriesSplit, cross_val_score

# 1. Attach to MT5
if not mt5.initialize():
    print("❌ Could not attach to MT5:", mt5.last_error())
    mt5.shutdown()
    exit()
print("✅ Attached to MT5")

# 2. Fetch last 2000 one‑hour EURUSD bars
rates = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H1, 0, 2000)
mt5.shutdown()
if rates is None or len(rates) == 0:
    print("⚠️ No data fetched.")
    exit()
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)
df = df[['open','high','low','close','tick_volume']]

# 3. Engineer TA features
df_clean = dropna(df)
df_feat  = add_all_ta_features(
    df_clean,
    open="open", high="high", low="low",
    close="close", volume="tick_volume",
    fillna=True
)
# 4. Create binary target: next bar up/down
df_feat['target'] = (df_feat['close'].shift(-1) > df_feat['close']).astype(int)
df_feat.dropna(inplace=True)

# 5. Split data chronologically (80/20)
split = int(len(df_feat) * 0.8)
train = df_feat.iloc[:split]
test  = df_feat.iloc[split:]
X_train, y_train = train.drop('target', axis=1), train['target']
X_test,  y_test  = test.drop('target', axis=1),  test['target']

# 6. Baseline random forest to get importances
base = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
base.fit(X_train, y_train)
importances = pd.Series(base.feature_importances_, index=X_train.columns).sort_values(ascending=False)
print("\nTop 20 features by importance:")
print(importances.head(20))

# 7. Automatic selection (top 50% by importance)
selector = SelectFromModel(base, threshold='median', prefit=True)
Xtr_sel = selector.transform(X_train)
Xte_sel = selector.transform(X_test)
selected = X_train.columns[selector.get_support()]
print(f"\nSelected {len(selected)} features:")
print(selected.tolist())

# 8. Retrain & re‑evaluate on selected features
sel_model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
tscv = TimeSeriesSplit(n_splits=5)
scores = cross_val_score(sel_model, Xtr_sel, y_train, cv=tscv, scoring='accuracy')
print(f"\nCV accuracy (selected features): {np.mean(scores):.3f} ± {np.std(scores):.3f}")
sel_model.fit(Xtr_sel, y_train)
test_acc = sel_model.score(Xte_sel, y_test)
print(f"Test accuracy (selected features): {test_acc:.3f}")
