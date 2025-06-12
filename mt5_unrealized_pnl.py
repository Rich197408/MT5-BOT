# mt5_unrealized_pnl.py

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

# ───── CONFIG ─────────────────────────────────────────────────────────────
SYMBOL    = "XAUUSD"
MAGIC     = 123456          # your bot’s magic number
PIP_VALUE = 0.1            # XAUUSD: 0.1 price = 1 pip
# ────────────────────────────────────────────────────────────────────────────

def main():
    # 1) Init MT5
    if not mt5.initialize():
        print("Error: MT5 initialization failed")
        return

    # 2) Get open positions
    all_pos = mt5.positions_get(symbol=SYMBOL)
    if not all_pos:
        print("No open positions for", SYMBOL)
        mt5.shutdown()
        return

    # 3) Fetch current bid
    tick = mt5.symbol_info_tick(SYMBOL)
    current_bid = tick.bid

    # 4) Build DataFrame
    rows = []
    for p in all_pos:
        if p.magic != MAGIC:
            continue
        side = "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL"
        entry = p.price_open
        volume = p.volume
        # pips gained: long = (bid - entry)/pip, short = (entry - bid)/pip
        pips = ((current_bid - entry) if p.type == mt5.ORDER_TYPE_BUY else (entry - current_bid)) / PIP_VALUE
        pnl  = pips * volume
        rows.append({
            "Ticket": p.ticket,
            "Side": side,
            "Lots": volume,
            "Entry": entry,
            "Pips": round(pips, 1),
            "P&L ($)": round(pnl, 2)
        })

    df = pd.DataFrame(rows)
    total_pnl = df["P&L ($)"].sum()

    # 5) Output
    print(f"\nUnrealized P&L as of {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Current Bid: {current_bid}\n")
    print(df.to_string(index=False))
    print(f"\nTotal Unrealized P&L: ${total_pnl:.2f}\n")

    mt5.shutdown()

if __name__ == "__main__":
    main()
