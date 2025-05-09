#!/usr/bin/env python3
import pandas as pd
from fetch_eurusd_attach import fetch_mt5_ohlcv
from strategies import SMCStrategy, ICTStrategy, SwingStrategy, SignalEngine
import datetime

# ─── CONFIG ─────────────────────────────────────────────────────────────
SYMBOL    = "XAUUSD"
WEIGHTS   = [0.4, 0.3, 0.3]
THRESHOLD = 0.6
# ──────────────────────────────────────────────────────────────────────────

def build_multi_tf_features(symbol: str) -> pd.DataFrame:
    df1 = fetch_mt5_ohlcv(symbol, "1h",   24)[["open","high","low","close"]].add_suffix("_1h")
    df4 = fetch_mt5_ohlcv(symbol, "4h",    6)[["open","high","low","close"]].add_suffix("_4h").resample("1h").ffill()
    df30 = fetch_mt5_ohlcv(symbol, "30m",  48)[["open","high","low","close"]].add_suffix("_30m").resample("1h").last().ffill()
    df15 = fetch_mt5_ohlcv(symbol, "15m",  96)[["open","high","low","close"]].add_suffix("_15m").resample("1h").last().ffill()
    return df1.join([df4, df30, df15], how="inner").dropna()

def main():
    # build the DataFrame of the last 24 hours
    df = build_multi_tf_features(SYMBOL).tail(24)

    # instantiate each strategy
    smc   = SMCStrategy(SYMBOL)
    ict   = ICTStrategy(SYMBOL)
    swing = SwingStrategy(SYMBOL)
    engine = SignalEngine([smc, ict, swing], WEIGHTS, threshold=THRESHOLD)

    print(f"{'Time':<16}  {'SMC':<8} {'ICT':<8} {'Swing':<8} {'Combo':<8} {'Conf'}")
    print("-"*60)

    for ts in df.index:
        slice_df = df.loc[:ts]
        s_smc, _   = smc.generate_signal(slice_df)
        s_ict, _   = ict.generate_signal(slice_df)
        s_swing,_  = swing.generate_signal(slice_df)
        combo, conf= engine.aggregate(slice_df)
        print(f"{ts:%Y-%m-%d %H:%M}  {s_smc:<8} {s_ict:<8} {s_swing:<8} {combo:<8} {conf:.2f}")

if __name__=="__main__":
    main()
