import time
import threading
import datetime as dt
import pytz
import MetaTrader5 as mt5

# Your existing config here…
ACCOUNT_LOGIN    = 92214559
ACCOUNT_PASSWORD = "E_HrX6Wp"
ACCOUNT_SERVER   = "MetaQuotes-Demo"
SYMBOL           = "XAUUSD"
BROKER_TZ        = "Etc/GMT-1"

def trading_loop():
    mt5.initialize()
    mt5.login(ACCOUNT_LOGIN, ACCOUNT_PASSWORD, ACCOUNT_SERVER)
    print(">>> MT5 initialized and logged in")

    # just print heartbeat every 5s
    while True:
        now = dt.datetime.utcnow().replace(tzinfo=pytz.UTC)
        print(f"{now.isoformat()} — heartbeat")
        time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=trading_loop, daemon=True).start()
    # keep main thread alive
    while True:
        time.sleep(1)
