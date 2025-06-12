#!/usr/bin/env python3
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta, timezone

# ───── CONFIG ─────────────────────────────────────────────────────────────
MT5_PATH      = r"C:\Program Files\MetaTrader 5\terminal64.exe"
LOGIN_ACCOUNT = 92214559
LOGIN_PASS    = "E_HrX6Wp"
LOGIN_SERVER  = "MetaQuotes-Demo"
SYMBOL        = "XAUUSD"
MAGIC         = 1234501
# ────────────────────────────────────────────────────────────────────────────

# 1) Initialize & login
if not mt5.initialize(path=MT5_PATH):
    raise RuntimeError("MT5 initialize() failed")
if not mt5.login(LOGIN_ACCOUNT, LOGIN_PASS, LOGIN_SERVER):
    raise RuntimeError("MT5 login() failed")

# 2) Build a UTC window covering the last 60 minutes
now_utc      = datetime.now(timezone.utc)
one_hour_ago = now_utc - timedelta(hours=1)

# 3) Fetch *all* deals (entry + exit) in that window
deals = mt5.history_deals_get(one_hour_ago, now_utc) or []

# 4) Filter for your bot’s magic and only XAUUSD
rows = []
for d in deals:
    if d.magic == MAGIC and d.symbol == SYMBOL:
        deal_time = datetime.fromtimestamp(d.time, tz=timezone.utc)
        rows.append({
            "time_utc":  deal_time.strftime("%H:%M:%S"),
            "ticket":    d.ticket,
            "type":      "ENTRY" if d.entry==mt5.DEAL_ENTRY_IN else "EXIT",
            "side":      "BUY"  if d.type==mt5.ORDER_TYPE_BUY  else "SELL",
            "lots":      d.volume,
            "price":     d.price,
            "profit":    d.profit
        })

df = pd.DataFrame(rows)
if df.empty:
    print("No bot deals (entry or exit) in the last hour.")
else:
    print("Bot deals in the last hour (UTC):")
    print(df.to_string(index=False))

mt5.shutdown()
