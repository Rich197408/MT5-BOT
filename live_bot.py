#!/usr/bin/env python3
import argparse, sys, time, datetime, math

import MetaTrader5 as mt5
import pandas as pd

from fetch_eurusd_attach import fetch_mt5_ohlcv
from strategies import SMCStrategy, ICTStrategy, SwingStrategy, SignalEngine

# ─── CONFIG ────────────────────────────────────────────────────────────────
SYMBOL            = "XAUUSD"
LOGIN             = 92214559
PASSWORD          = "E_HrX6Wp"
SERVER            = "MetaQuotes-Demo"
MAGIC             = 123456

# Risk settings
RISK_PER_TRADE    = 0.01    # 1% of account balance per trade
SL_POINTS         = 500.0   # 500 points × 0.01 = $5 stop-loss
RR                = 2       # take-profit = SL × RR
TRAIL_TRIGGER     = 250.0   # 250 points × 0.01 = $2.50 to trail SL

# Daily P/L caps (closed trades only; reset at 00:00 UTC)
DAILY_PROFIT_TARGET = 300.0
DAILY_LOSS_LIMIT    = -800.0

# Strategy ensemble
STRATEGIES = [
    SMCStrategy(SYMBOL),
    ICTStrategy(SYMBOL),
    SwingStrategy(SYMBOL),
]
WEIGHTS  = [0.4, 0.3, 0.3]
THRESHOLD = 0.6   # require ≥60% aggregate confidence
engine    = SignalEngine(STRATEGIES, WEIGHTS, threshold=THRESHOLD)
# ─────────────────────────────────────────────────────────────────────────────

def initialize_mt5():
    if not mt5.initialize():
        print("ERROR: MT5 initialize() failed:", mt5.last_error())
        sys.exit(1)
    if not mt5.login(LOGIN, password=PASSWORD, server=SERVER):
        print("ERROR: MT5 login failed:", mt5.last_error())
        mt5.shutdown()
        sys.exit(1)

def get_closed_pl_since(start_dt: datetime.datetime) -> float:
    deals = mt5.history_deals_get(start_dt, datetime.datetime.utcnow())
    return sum(d.profit for d in deals) if deals else 0.0

def build_multi_tf_features(symbol: str) -> pd.DataFrame:
    df1h = fetch_mt5_ohlcv(symbol, "1h",   2000)[["open","high","low","close"]].add_suffix("_1h")
    df4h = fetch_mt5_ohlcv(symbol, "4h",    500)[["open","high","low","close"]].add_suffix("_4h").resample("1h").ffill()
    df30 = fetch_mt5_ohlcv(symbol, "30m",  4000)[["open","high","low","close"]].add_suffix("_30m").resample("1h").last().ffill()
    df15 = fetch_mt5_ohlcv(symbol, "15m",  8000)[["open","high","low","close"]].add_suffix("_15m").resample("1h").last().ffill()
    return df1h.join([df4h, df30, df15], how="inner").dropna()

def execute_trade(signal: str, conf: float):
    tick = mt5.symbol_info_tick(SYMBOL)
    info = mt5.symbol_info(SYMBOL)
    point = info.point
    contract_size = info.trade_contract_size

    price = tick.ask if signal=="BUY" else tick.bid
    sl_price = price - SL_POINTS*point if signal=="BUY" else price + SL_POINTS*point
    tp_price = price + SL_POINTS*RR*point if signal=="BUY" else price - SL_POINTS*RR*point

    # enforce broker's minimum stop distance
    min_dist = info.trade_stops_level * point
    if abs(price - sl_price) < min_dist:
        sl_price = price - min_dist if signal=="BUY" else price + min_dist

    # position sizing: risk 1% of balance
    sl_dist      = abs(price - sl_price)
    risk_per_lot = sl_dist * contract_size
    balance      = mt5.account_info().balance
    raw_lots     = (balance * RISK_PER_TRADE) / risk_per_lot
    step         = info.volume_step
    vol          = max(info.volume_min, min(info.volume_max,
                      math.floor(raw_lots/step)*step))

    req = {
        "action":       mt5.TRADE_ACTION_DEAL,
        "symbol":       SYMBOL,
        "volume":       vol,
        "type":         mt5.ORDER_TYPE_BUY if signal=="BUY" else mt5.ORDER_TYPE_SELL,
        "price":        price,
        "sl":           round(sl_price, info.digits),
        "tp":           round(tp_price, info.digits),    # <-- ensure TP always set
        "deviation":    10,
        "magic":        MAGIC,
        "comment":      "MCBot",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    res = mt5.order_send(req)
    if res.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"{signal} @ {price:.2f} Vol={vol:.2f} SL={sl_price:.2f} TP={tp_price:.2f}")
    else:
        print("Order failed:", res.comment)

def trail_sl_to_breakeven():
    for pos in mt5.positions_get(symbol=SYMBOL) or []:
        tick = mt5.symbol_info_tick(SYMBOL)
        info = mt5.symbol_info(SYMBOL)
        point = info.point
        entry = pos.price_open

        if pos.type == mt5.ORDER_TYPE_BUY and (tick.bid - entry) >= TRAIL_TRIGGER*point:
            # move SL to breakeven but keep the original TP
            mt5.order_send({
                "action":    mt5.TRADE_ACTION_SLTP,
                "position":  pos.ticket,
                "sl":        round(entry, info.digits),
                "tp":        round(pos.tp, info.digits),    # <-- carry forward TP
            })
        elif pos.type == mt5.ORDER_TYPE_SELL and (entry - tick.ask) >= TRAIL_TRIGGER*point:
            mt5.order_send({
                "action":    mt5.TRADE_ACTION_SLTP,
                "position":  pos.ticket,
                "sl":        round(entry, info.digits),
                "tp":        round(pos.tp, info.digits),    # <-- carry forward TP
            })

def main_loop(force_weekend: bool, test_trade: bool, run_once: bool):
    initialize_mt5()
    print("MT5 connected.")
    now = datetime.datetime.utcnow()
    sod = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if test_trade:
        execute_trade("BUY", 1.0)
        mt5.shutdown()
        return

    while True:
        now = datetime.datetime.utcnow()
        if now.date() != sod.date():
            sod = now.replace(hour=0, minute=0, second=0, microsecond=0)
            print("New UTC day, reset P/L counter.")

        closed_pl = get_closed_pl_since(sod)
        print(f"Closed P/L since {sod:%Y-%m-%d}: {closed_pl:.2f}")

        if closed_pl >= DAILY_PROFIT_TARGET:
            print("Daily profit target reached. Pausing new trades.")
        elif closed_pl <= DAILY_LOSS_LIMIT:
            print("Daily loss limit hit. Pausing new trades.")
        else:
            df_feat = build_multi_tf_features(SYMBOL)
            sig, conf = engine.aggregate(df_feat)
            print(f"{now:%Y-%m-%d %H:%M} → {sig} @ {conf:.2f}")
            if sig in ("BUY","SELL") and conf>=THRESHOLD:
                execute_trade(sig, conf)
            trail_sl_to_breakeven()

        if run_once:
            print("Exiting after one cycle (--once).")
            break

        # weekend skip
        if now.weekday()>=5 and not force_weekend:
            time.sleep(3600)
            continue

        time.sleep(900)  # 15-minute cycle

    mt5.shutdown()

if __name__=="__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--once",       action="store_true",  help="single cycle then exit")
    p.add_argument("--force",      action="store_true",  help="ignore weekend check")
    p.add_argument("--test-trade", action="store_true",  help="place one test trade")
    args = p.parse_args()

    main_loop(force_weekend=args.force,
              test_trade=args.test_trade,
              run_once=args.once)
