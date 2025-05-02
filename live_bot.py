#!/usr/bin/env python3
import argparse
import sys
import time
import datetime

import joblib
import pandas as pd
import MetaTrader5 as mt5

from fetch_eurusd_attach import fetch_mt5_ohlcv
from ta.utils import dropna
from ta import add_all_ta_features

from strategies import SMCStrategy, ICTStrategy, SwingStrategy, SignalEngine

# ─── CONFIG ────────────────────────────────────────────────
MODEL_PATH   = "multi_tf_rf.pkl"
SYMBOL       = "XAUUSD"
MAGIC        = 123456
LOGIN        = 92214559
PASSWORD     = "E_HrX6Wp"
SERVER       = "MetaQuotes-Demo"

# Multi-strategy setup
STRATEGIES = [
    SMCStrategy(SYMBOL),
    ICTStrategy(SYMBOL),
    SwingStrategy(SYMBOL),
]
WEIGHTS    = [0.33, 0.33, 0.34]

# Raise these for maximum selectivity
THRESHOLD  = 0.8   # require at least 80% weighted agreement among strategies
CUTOFF     = 0.9   # require at least 90% ML model confidence

engine = SignalEngine(STRATEGIES, WEIGHTS, threshold=THRESHOLD)

def is_market_open() -> bool:
    """Return True if today is Mon-Fri UTC."""
    return datetime.datetime.utcnow().weekday() < 5

def build_multi_tf_features(symbol=SYMBOL) -> pd.DataFrame:
    df1  = fetch_mt5_ohlcv(symbol, "1h",   2000)
    df4  = fetch_mt5_ohlcv(symbol, "4h",    500).resample("1H").ffill().add_suffix("_4h")
    df30 = fetch_mt5_ohlcv(symbol, "30m",  4000).resample("1H").last().ffill().add_suffix("_30m")
    df   = df1.join([df4, df30], how="inner").dropna()

    def k(o, h, l, c, v):
        return dict(open=o, high=h, low=l, close=c, volume=v, fillna=True)

    f1  = add_all_ta_features(dropna(df), **k("open","high","low","close","tick_volume")).add_suffix("_1h")
    f4  = add_all_ta_features(dropna(df), **k("open_4h","high_4h","low_4h","close_4h","tick_volume_4h")).add_suffix("_4h")
    f30 = add_all_ta_features(dropna(df), **k("open_30m","high_30m","low_30m","close_30m","tick_volume_30m")).add_suffix("_30m")

    return f1.join([f4, f30], how="inner").dropna()

def execute_trade(signal: str, confidence: float) -> None:
    time.sleep(1)

    if not mt5.symbol_select(SYMBOL, True):
        print("ERROR: symbol_select failed:", mt5.last_error())
        return

    info = mt5.symbol_info(SYMBOL)
    if not info:
        print(f"ERROR: '{SYMBOL}' not in Market Watch.")
        return

    if mt5.positions_get(symbol=SYMBOL):
        print("Position already open—skipping.")
        return

    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick:
        print(f"ERROR: no tick for {SYMBOL}")
        return

    lot   = 1.0 if confidence >= 0.85 else 0.5
    price = tick.ask if signal == "BUY" else tick.bid
    pt    = info.point
    sl    = price - 25 * pt if signal == "BUY" else price + 25 * pt
    tp    = price + 50 * pt if signal == "BUY" else price - 50 * pt

    req = {
        "action":    mt5.TRADE_ACTION_DEAL,
        "symbol":    SYMBOL,
        "volume":    lot,
        "type":      mt5.ORDER_TYPE_BUY if signal == "BUY" else mt5.ORDER_TYPE_SELL,
        "price":     price,
        "sl":        sl,
        "tp":        tp,
        "deviation": 10,
        "magic":     MAGIC,
        "comment":   "mlbot"
    }
    res = mt5.order_send(req)
    if res.retcode != mt5.TRADE_RETCODE_DONE:
        print("Order failed:", res)
    else:
        print(f"Order #{res.order} placed: {signal} {lot}@{price:.2f} SL={sl:.2f} TP={tp:.2f}")

def main_once(force: bool = False) -> None:
    if not force and not is_market_open():
        print("Market closed—skipping.")
        return

    if not mt5.initialize():
        print("ERROR: could not attach to MT5:", mt5.last_error())
        return
    if not mt5.login(LOGIN, PASSWORD, SERVER):
        print("ERROR: login failed:", mt5.last_error())
        mt5.shutdown()
        return

    print("MT5 attached & logged in")
    time.sleep(1)

    df_feat = build_multi_tf_features()

    # per‐strategy and aggregate
    ts = df_feat.index[-1]
    signal, conf = engine.aggregate(df_feat)
    print(f"{ts} -> {signal} @ {conf:.0%} combined")

    # only fire on very strong consensus **and** high model confidence
    if signal in ("BUY", "SELL") and conf >= CUTOFF:
        execute_trade(signal, conf)
    else:
        print(f"Skipping trade: need signal in BUY/SELL with conf ≥{CUTOFF:.0%}")

    mt5.shutdown()
    print("MT5 shutdown.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once",  action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.once:
        main_once(force=args.force)
        sys.exit(0)
    else:
        while True:
            main_once()
            time.sleep(3600)
# módosítás teszt miatt
