import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from ta import add_all_ta_features
from ta.utils import dropna
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV

# 1. Attach & fetch
if not mt5.initialize():
    print("Could not attach to MT5:", mt5.last_error())
    mt5.shutdown()
    exit()
rates = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H1, 0, 2000)
mt5.shutdown()
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)
df = df[['open','high','low','close','tick_volume']]

# 2. Engineer features + target
df = dropna(df)
df_feat = add_all_ta_features(df, open="open", high="high", low="low",
                              close="close", volume="tick_volume", fillna=True)
df_feat['target'] = (df_feat['close'].shift(-1) > df_feat['close']).astype(int)
df_feat.dropna(inplace=True)

# 3. Train/test split
split = int(len(df_feat)*0.8)
train = df_feat.iloc[:split]
X_train = train.drop('target', axis=1)
y_train = train['target']

# 4. Set up parameter grid for RandomizedSearch
param_dist = {
    'n_estimators': [100, 200, 500, 800],
    'max_depth': [None, 10, 20, 30],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4],
    'max_features': ['sqrt', 'log2', 0.2, 0.5]
}

base_model = RandomForestClassifier(random_state=42)
tscv = TimeSeriesSplit(n_splits=5)

rs = RandomizedSearchCV(
    estimator=base_model,
    param_distributions=param_dist,
    n_iter=20,                     # number of random combos to try
    cv=tscv,
    scoring='accuracy',
    n_jobs=-1,
    random_state=42,
    verbose=2
)

# 5. Run the search
rs.fit(X_train, y_train)

# 6. Report results
print("\nBest parameters found:")
print(rs.best_params_)
print(f"Best CV accuracy: {rs.best_score_:.3f}")

