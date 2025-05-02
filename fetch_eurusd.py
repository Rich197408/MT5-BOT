import MetaTrader5 as mt5
import pandas as pd

# 1. Path to your MT5 terminal executable
#    • Find terminal64.exe (or terminal.exe) in File Explorer under C:\Program Files\MetaTrader 5
mt5_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"  

# 2. Your FundedNext‑DEMO credentials
account  = 78764763                         # ← replace with your account number
password = "qgmIN92##"                       # ← replace with your MT5 password
server   = "FundedNext-Server4"  # ← exactly as shown in MT5’s login dialog

# 3. Initialize MT5 AND log in in one call
if not mt5.initialize(path=mt5_path, login=account, password=password, server=server):
    print("❌ Failed to initialize or log in:", mt5.last_error())
    mt5.shutdown()
    exit()

print("✅ Initialized & logged in as account #", account)

# 4. Function to fetch OHLCV data
def fetch_mt5_ohlcv(symbol, timeframe, n_bars=500):
    tf_map = {
        "30m": mt5.TIMEFRAME_M30,
        "1h":  mt5.TIMEFRAME_H1,
        "4h":  mt5.TIMEFRAME_H4,
        "1d":  mt5.TIMEFRAME_D1,
    }
    rates = mt5.copy_rates_from_pos(symbol, tf_map[timeframe], 0, n_bars)
    if rates is None:
        print(f"❌ Failed to fetch rates for {symbol} @ {timeframe}")
        return pd.DataFrame()
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df.set_index('time')[['open','high','low','close','tick_volume']]

# 5. Pull and display the last 3 bars for EURUSD at each timeframe
symbol = "EURUSD"
timeframes = ["30m", "1h", "4h", "1d"]

for tf in timeframes:
    df = fetch_mt5_ohlcv(symbol, tf, 500)
    if not df.empty:
        print(f"\n🔹 {symbol} @ {tf} last 3 bars:")
        print(df.tail(3))
    else:
        print(f"\n⚠️ No data for {symbol} @ {tf}")

# 6. Shutdown MT5 connection
mt5.shutdown()
