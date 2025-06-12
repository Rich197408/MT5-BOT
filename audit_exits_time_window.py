#!/usr/bin/env python3
import MetaTrader5 as mt5
import argparse
from datetime import datetime, date, time, timedelta

SYMBOL = "XAUUSD"

def parse_hhmm(s: str) -> time:
    return datetime.strptime(s, "%H:%M").time()

def parse_offset(s: str) -> timedelta:
    sign = 1 if s.startswith("+") else -1
    h, m = map(int, s[1:].split(":"))
    return sign * timedelta(hours=h, minutes=m)

def main():
    parser = argparse.ArgumentParser(
        description="Audit XAUUSD EXIT deals in a local-time window"
    )
    parser.add_argument("--date", dest="dt", required=True,
                        help="Date to audit, YYYY-MM-DD")
    parser.add_argument("--from", dest="t0", required=True,
                        help="Start time HH:MM (local)")
    parser.add_argument("--to", dest="t1", required=True,
                        help="End   time HH:MM (local)")
    parser.add_argument("--utc-offset", dest="off", default="+00:00",
                        help="Your local offset from UTC (e.g. +03:00)")
    args = parser.parse_args()

    # build local datetime range
    audit_date = datetime.strptime(args.dt, "%Y-%m-%d").date()
    local_start = datetime.combine(audit_date, parse_hhmm(args.t0))
    local_end   = datetime.combine(audit_date, parse_hhmm(args.t1))
    offset      = parse_offset(args.off)
    utc_start   = local_start - offset
    utc_end     = local_end   - offset

    # init MT5
    if not mt5.initialize():
        print("❌ MT5 initialize() failed:", mt5.last_error())
        return

    # fetch all deals in UTC window
    deals = mt5.history_deals_get(utc_start, utc_end) or []
    # filter to EXIT deals on XAUUSD
    exits = [
        d for d in deals
        if d.symbol == SYMBOL and d.entry != mt5.DEAL_ENTRY
    ]

    print()
    print(f"Exit deals for {SYMBOL}")
    print(f"  local {args.t0} → {args.t1}  (UTC {utc_start.time():%H:%M} → {utc_end.time():%H:%M})")
    print(f"  date  {args.dt}  (offset {args.off})\n")

    if not exits:
        print("  ❗ No EXIT deals found in that window.\n")
    else:
        print(f"{'LOCAL TIME':<20} {'TICKET':<10} {'SIDE':<6} {'LOTS':<5} {'PRICE':<8} {'PROFIT':<8}")
        for d in exits:
            utc_ts   = datetime.utcfromtimestamp(d.time)
            local_ts = utc_ts + offset
            side     = "BUY" if d.type == mt5.ORDER_TYPE_BUY else "SELL"
            print(f"{local_ts:%Y-%m-%d %H:%M:%S}  "
                  f"{d.ticket:<10}  "
                  f"{side:<6}  "
                  f"{d.volume:>5.2f}  "
                  f"{d.price:>8.2f}  "
                  f"{d.profit:>8.2f}")

    mt5.shutdown()

if __name__ == "__main__":
    main()
