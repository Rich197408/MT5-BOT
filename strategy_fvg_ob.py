# strategy_fvg_ob.py

import pandas as pd
from datetime import datetime
import MetaTrader5 as mt5
from detect import detect_fvg, detect_ob

# ───── PARAMETERS ──────────────────────────────────────────────────────────
SYMBOL   = "XAUUSD"
LOTS_MAP = {1: 1.5, 2: 1.0}
SL_PIPS  = 35
TP_PIPS  = 80
PIP_SIZE = 0.1         # 0.1 price‐points per pip on XAUUSD
ATR_LEN  = 14
ACTIVE_HOURS = set(range(7,24))  # London + NY
# ─────────────────────────────────────────────────────────────────────────────

def run_fvg_ob_strategy(timeframe):
    # 1) pull last 2 000 bars
    rates = mt5.copy_rates_from(SYMBOL, timeframe, datetime.now(), 2000)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.rename(columns={'open':'o','high':'h','low':'l','close':'c'}, inplace=True)

    # 2) compute ATR14
    df['prev_close'] = df['c'].shift(1)
    df['tr'] = df[['h','prev_close']].max(axis=1) - df[['l','prev_close']].min(axis=1)
    df['atr'] = df['tr'].rolling(ATR_LEN).mean()
    atr_med = df['atr'].median()

    # 3) detect confluences
    fvg_idx = detect_fvg(df)   # returns set of bar indices
    ob_idx  = detect_ob(df)    # returns set of bar indices

    # 4) look at the last *closed* bar
    idx = len(df) - 2
    bar_time = df.at[idx,'time']

    # 5) session & ATR filter
    if bar_time.hour not in ACTIVE_HOURS:
        return
    if df.at[idx,'atr'] <= atr_med:
        return

    # 6) count confluences
    conf = (1 if idx in fvg_idx else 0) + (1 if idx in ob_idx else 0)
    if conf == 0 or conf > 2:
        return
    lot = LOTS_MAP[conf]

    # 7) decide side (assume bullish if FVG bullish, OB bullish; you'll want to extend
    #    detect_fvg/ob to also return their direction, here we assume buy for simplicity)
    price = mt5.symbol_info_tick(SYMBOL).ask
    side  = mt5.ORDER_TYPE_BUY

    # 8) compute SL/TP levels
    sl = price - SL_PIPS * PIP_SIZE
    tp = price + TP_PIPS * PIP_SIZE

    # 9) build & send order
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": lot,
        "type": side,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 10,
        "magic": 123456,
        "comment": "FVG+OB ATR filter",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(req)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order failed at {bar_time}: retcode={result.retcode}")

# Example usage in your bot.py, e.g. on each new 30 m or 1 h bar:
# from strategy_fvg_ob import run_fvg_ob_strategy
# ...
# def on_new_bar(symbol, timeframe):
#     run_fvg_ob_strategy(timeframe)
