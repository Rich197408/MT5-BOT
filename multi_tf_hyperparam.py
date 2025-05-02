import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from ta import add_all_ta_features
from ta.utils import dropna
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV

# (Re‑use the fetch & build df_feat logic from multi_timeframe_pipeline.py here)

# …[insert code to attach, fetch df1h/df4h/df30m, merge + TA into df_feat]…

#  Split out train only
split = int(len(df_feat)*0.8)
train = df_feat.iloc[:split]
X_train = train.drop('target', axis=1)
y_train = train['target']

# Hyperparameter space
param_dist = {
    'n_estimators': [100,200,500],
    'max_depth':    [10,20,30, None],
    'min_samples_split': [2,5,10],
    'min_samples_leaf':  [1,2,4],
    'max_features':      ['sqrt','log2', 0.2, 0.5]
}

tscv = TimeSeriesSplit(n_splits=5)
rs = RandomizedSearchCV(
    RandomForestClassifier(random_state=42, n_jobs=-1),
    param_dist, n_iter=20, cv=tscv, scoring='accuracy',
    random_state=42, n_jobs=-1, verbose=1
)
rs.fit(X_train, y_train)

print("Best params:", rs.best_params_)
print("Best CV score:", rs.best_score_)




