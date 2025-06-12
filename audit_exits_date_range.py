#!/usr/bin/env python3
import MetaTrader5 as mt5
import argparse
from datetime import datetime, date, time, timedelta

SYMBOL = "XAUUSD"

def parse_offset(s: str) -> timedelta:
    sign = 1 if s.startswith("+") else -1
    h, m = map(int, s[1:].split(":"))
    return sign * timedelta(hours=h, minutes=m)

def main():
    parser = argparse.ArgumentParser(
        description="Audit XAUUSD EXIT deals over a date range (local time)"
    )
    parser.add_argument("--start-date", dest="start", required=True,
                        help="Start date (inclusive), format YYYY-MM-DD")
    parser.add_argument("--end-date",   dest="end",   required=True,
                        help="End   date (inclusive), format YYYY-MM-DD")
    parser.add_argument("--utc-offset", dest="off", default="+00:00",
                        help="Your local offset from UTC (e.g. +03:00)")
    args = parser.parse_args()

    # Parse dates
    start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_date   = datetime.strptime(args.end,   "%Y-%m-%d").date()
    # Local datetimes from midnight of start_date to 23:59:59 of end_date
    local_start = datetime.combine(start_date, time.min)
    local_end   = datetime.combine(end_date,   time.max)
    offset      = parse_offset(args.off)
    # Convert to UTC
    utc_start = local_start - offset
    utc_end   = local_end   - offset

    # Initialize MT5
    if not mt5.initialize():
        print("❌ MT5 initialize() failed:", mt5.last_error())
        return

    # Fetch deals in UTC window
    deals = mt5.history_deals_get(utc_start, utc_end) or []
    # Keep only EXIT deals for XAUUSD
    exits = [d for d in deals
             if d.symbol == SYMBOL and d.entry != mt5.DEAL_ENTRY_IN]

    print(f"\nEXIT deals for {SYMBOL}")
    print(f"  Local dates: {args.start}→{args.end}  (00:00→23:59)")
    print(f"  UTC window : {utc_start} → {utc_end}  (using offset {args.off})\n")

    if not exits:
        print("  ❗ No EXIT deals found in that range.\n")
    else:
        print(f"{'UTC TIME':<20} {'LOCAL TIME':<20} {'TICKET':<10} {'SIDE':<6} {'LOTS':<5} {'PRICE':<8} {'PROFIT':<8}")
        for d in exits:
            utc_ts   = datetime.utcfromtimestamp(d.time)
            local_ts = utc_ts + offset
            side     = "BUY" if d.type == mt5.ORDER_TYPE_BUY else "SELL"
            print(f"{utc_ts:%Y-%m-%d %H:%M:%S}  "
                  f"{local_ts:%Y-%m-%d %H:%M:%S}  "
                  f"{d.ticket:<10}  "
                  f"{side:<6}  "
                  f"{d.volume:>5.2f}  "
                  f"{d.price:>8.2f}  "
                  f"{d.profit:>8.2f}")

    mt5.shutdown()

if __name__ == "__main__":
    main()
