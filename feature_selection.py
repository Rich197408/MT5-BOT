import MetaTrader5 as mt5
import pandas as pd

# Attach to the already‑running MT5 terminal
if not mt5.initialize():
    print("❌ Failed to attach to MT5, error code =", mt5.last_error())
    mt5.shutdown()
    exit()
print("✅ Attached to running MT5")

def fetch_mt5_ohlcv(symbol, timeframe, n_bars=500):
    """
    Returns a DataFrame of the last n_bars OHLCV for symbol@timeframe.
    Assumes MT5 is already initialized/attached.
    """
    tf_map = {
        "30m": mt5.TIMEFRAME_M30,
        "1h":  mt5.TIMEFRAME_H1,
        "4h":  mt5.TIMEFRAME_H4,
        "1d":  mt5.TIMEFRAME_D1,
    }
    rates = mt5.copy_rates_from_pos(symbol, tf_map[timeframe], 0, n_bars)
    if rates is None or len(rates) == 0:
        return pd.DataFrame()
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df.set_index('time')[['open','high','low','close','tick_volume']]

