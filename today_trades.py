#!/usr/bin/env python
import MetaTrader5 as mt5
import datetime

# ─── CONFIG ────────────────────────────────────────────────────────────────────
MT5_PATH   = r"C:\Program Files\MetaTrader 5\terminal64.exe"
ACCOUNT    = 92214559
PASSWORD   = "E_HrX6Wp"
SERVER     = "MetaQuotes-Demo"
SYMBOL     = "XAUUSD"
# ────────────────────────────────────────────────────────────────────────────────

def init_mt5():
    if not mt5.initialize(path=MT5_PATH):
        raise RuntimeError("MT5 initialize() failed")
    if not mt5.login(ACCOUNT, PASSWORD, SERVER):
        raise RuntimeError("MT5 login() failed")

def fetch_today_deals(symbol: str):
    now = datetime.datetime.now()
    start_of_day = datetime.datetime(now.year, now.month, now.day)
    from_ts = int(start_of_day.timestamp())
    to_ts   = int(now.timestamp())

    deals = mt5.history_deals_get(from_ts, to_ts)
    if deals is None:
        return []
    return [d for d in deals if d.symbol == symbol]

def main():
    init_mt5()
    deals = fetch_today_deals(SYMBOL)
    if not deals:
        print("No deals for today.")
        return

    print(f"Total deals for {SYMBOL} today: {len(deals)}\n")
    for d in sorted(deals, key=lambda x: x.time):
        t = datetime.datetime.fromtimestamp(d.time).strftime("%H:%M:%S")
        side = "BUY" if d.type == mt5.ORDER_TYPE_BUY else "SELL"
        vol  = d.volume
        price = d.price
        comment = d.comment or ""
        print(f"{t} | {side:<4} | vol={vol:.2f} | price={price:.2f} | tag='{comment}'")

if __name__ == "__main__":
    main()
