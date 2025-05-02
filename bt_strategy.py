import backtrader as bt
import joblib
import pandas as pd
from features import engineer_features

class MLStrategy(bt.Strategy):
    params = dict(
        model_path='multi_tf_rf.pkl',  # path to your trained model
        warmup_bars=500                # minimum bars before first prediction
    )

    def __init__(self):
        # Load your pretrained multi‑TF RandomForest model
        self.model = joblib.load(self.params.model_path)
        # Buffer for incoming bars
        self.buf = []

    def next(self):
        # 1. Append the current bar to the buffer
        dt = self.datas[0].datetime.datetime(0)
        bar = {
            'time': dt,
            'open': self.datas[0].open[0],
            'high': self.datas[0].high[0],
            'low': self.datas[0].low[0],
            'close': self.datas[0].close[0],
            'tick_volume': self.datas[0].volume[0],
        }
        self.buf.append(bar)

        # 2. Only start predicting once we have enough bars
        if len(self.buf) < self.params.warmup_bars:
            return

        # 3. Build a DataFrame and compute features
        df = pd.DataFrame(self.buf).set_index('time')
        df_feat = engineer_features(df)
        if df_feat.empty:
            return

        # 4. Take only the last row for prediction
        X = df_feat.iloc[[-1]].drop(columns=['target'], errors='ignore')

        # 5. Predict and trade
        pred = self.model.predict(X)[0]
        if pred == 1 and not self.position:
            self.buy()
        elif pred == 0 and self.position:
            self.close()





