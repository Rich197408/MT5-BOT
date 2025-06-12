import time
import threading
import datetime as dt
import pytz
import pandas as pd
import MetaTrader5 as mt5

ACCOUNT_LOGIN    = 92214559
ACCOUNT_PASSWORD = "E_HrX6Wp"
ACCOUNT_SERVER   = "MetaQuotes-Demo"
SYMBOL           = "XAUUSD"
BROKER_TZ        = "Etc/GMT-1"

def trading_loop():
    mt5.initialize()
    mt5.login(ACCOUNT_LOGIN, ACCOUNT_PASSWORD, ACCOUNT_SERVER)
    print(">>> MT5 initialized & logged in")

    while True:
        now = dt.datetime.utcnow().replace(tzinfo=pytz.UTC)
        print(f"{now.isoformat()} — fetching bars…")

        # Fetch the last 5 bars on 30m and 1h
        bars30 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M30, 0, 5)
        bars1h = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1,  0, 5)
        df30 = pd.DataFrame(bars30)
        df1h = pd.DataFrame(bars1h)

        # Localize timestamps to your broker TZ, convert to UTC
        for df, tf in [(df30, "30m"), (df1h, "1h")]:
            df["time"] = (
                pd.to_datetime(df["time"], unit="s")
                  .dt.tz_localize(BROKER_TZ)
                  .dt.tz_convert("UTC")
            )
            df.set_index("time", inplace=True)
            print(f"--- Last 30m bars (UTC) ---" if tf=="30m" else "--- Last 1h bars (UTC) ---")
            print(df[["open","high","low","close"]].tail(2))

        time.sleep(5)

if __name__=="__main__":
    trading_loop()
