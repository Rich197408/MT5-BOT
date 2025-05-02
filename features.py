import pandas as pd
from ta import add_all_ta_features
from ta.utils import dropna

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes a DataFrame indexed by datetime with columns
    ['open','high','low','close','tick_volume'] and returns
    a DataFrame with technical indicators plus a 'target' column.
    """
    df = dropna(df)
    df_ta = add_all_ta_features(
        df,
        open="open", high="high", low="low",
        close="close", volume="tick_volume",
        fillna=True
    )
    df_ta["target"] = (df_ta["close"].shift(-1) > df_ta["close"]).astype(int)
    return df_ta.iloc[:-1].dropna()

if __name__ == "__main__":
    from fetch_eurusd_attach import fetch_mt5_ohlcv
    df_raw = fetch_mt5_ohlcv("EURUSD", "1h", 500)
    df_feat = engineer_features(df_raw)
    print(df_feat.shape, df_feat.columns)
