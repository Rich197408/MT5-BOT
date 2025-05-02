# fetch_eurusd_attach.py

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

# Map our string TFs to MT5 constants
TF_MAP = {
    "1h": mt5.TIMEFRAME_H1,
    "4h": mt5.TIMEFRAME_H4,
    "30m": mt5.TIMEFRAME_M30,
    "15m": mt5.TIMEFRAME_M15,   # <— added this line
    "m1": mt5.TIMEFRAME_M1,
    "m5": mt5.TIMEFRAME_M5,
    "d1": mt5.TIMEFRAME_D1,
}

def fetch_mt5_ohlcv(symbol: str, tf: str, count: int = 500) -> pd.DataFrame:
    """
    Fetch `count` bars of OHLCV for `symbol` at timeframe `tf` ("1h", "4h", "30m", "15m", etc.)
    Returns a DataFrame indexed by UTC datetime with columns open, high, low, close, tick_volume.
    """
    if tf not in TF_MAP:
        raise ValueError(f"Unsupported timeframe: {tf}")

    # make sure MT5 is initialized
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    # fetch the bars
    rates = mt5.copy_rates_from_pos(symbol, TF_MAP[tf], 0, count)
    if rates is None:
        raise RuntimeError(f"copy_rates failed for {symbol} {tf}: {mt5.last_error()}")

    # convert to DataFrame
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df.set_index("time", inplace=True)
    df = df[["open", "high", "low", "close", "tick_volume"]]
    return df

