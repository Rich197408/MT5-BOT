import time
import MetaTrader5 as mt5

# 1) Attach to the already-running MT5 terminal
ok = mt5.initialize()
print("initialize() ->", ok, mt5.last_error())

time.sleep(1)

# 2) Log in (if MT5 isn't already logged in)
ok2 = mt5.login(92214559, "E_HrX6Wp", "MetaQuotes-Demo")
print("login()      ->", ok2, mt5.last_error())

time.sleep(1)

# 3) Try selecting EURUSD
sel = mt5.symbol_select("EURUSD", True)
print("symbol_select('EURUSD') ->", sel, mt5.last_error())

# 4) Try selecting XAUUSD
sel2 = mt5.symbol_select("XAUUSD", True)
print("symbol_select('XAUUSD') ->", sel2, mt5.last_error())

mt5.shutdown()
