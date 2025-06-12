# mt5_status.py

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

# ───── CONFIG ──────────────────────────────────────────────────────────
SYMBOL = "XAUUSD"   # adjust or fetch all symbols
# ────────────────────────────────────────────────────────────────────────

def fetch_open_positions():
    """Connects to MT5 and retrieves current open positions."""
    if not mt5.initialize():
        print("Error: MT5 initialization failed")
        return None
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions is None:
        print("Error: Could not retrieve positions or no open positions.")
        mt5.shutdown()
        return None
    # convert to DataFrame
    data = [p._asdict() for p in positions]
    df = pd.DataFrame(data)
    mt5.shutdown()
    return df

def main():
    df = fetch_open_positions()
    if df is not None and not df.empty:
        # select relevant columns
        cols = ["ticket", "symbol", "type", "volume", "price_open", "sl", "tp", "profit"]
        print(f"Open positions as of {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:")
        print(df[cols].to_string(index=False))
    else:
        print("No open positions found.")

if __name__ == "__main__":
    main()

