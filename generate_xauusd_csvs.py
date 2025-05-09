#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import MetaTrader5 as mt5

def save_xauusd_csvs():
    if not mt5.initialize():
        print("ERROR: MT5 initialize() failed:", mt5.last_error())
        return
    symbol = "XAUUSD"
    print(f"Fetching {symbol} data from MT5...")

    # 1h data
    rates_1h = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 2000)
    df_1h = pd.DataFrame(rates_1h)
    df_1h['time'] = pd.to_datetime(df_1h['time'], unit='s')
    df_1h.set_index('time', inplace=True)
    df_1h[['open','high','low','close','tick_volume']].to_csv("XAUUSD_1h.csv")
    print(" → Saved XAUUSD_1h.csv")

    # 4h data
    rates_4h = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 500)
    df_4h = pd.DataFrame(rates_4h)
    df_4h['time'] = pd.to_datetime(df_4h['time'], unit='s')
    df_4h.set_index('time', inplace=True)
    df_4h[['open','high','low','close','tick_volume']].to_csv("XAUUSD_4h.csv")
    print(" → Saved XAUUSD_4h.csv")

    # 30m data
    rates_30m = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M30, 0, 4000)
    df_30m = pd.DataFrame(rates_30m)
    df_30m['time'] = pd.to_datetime(df_30m['time'], unit='s')
    df_30m.set_index('time', inplace=True)
    df_30m[['open','high','low','close','tick_volume']].to_csv("XAUUSD_30m.csv")
    print(" → Saved XAUUSD_30m.csv")

    mt5.shutdown()
    print("All CSVs written successfully.")

if __name__ == "__main__":
    save_xauusd_csvs()
