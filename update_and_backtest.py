# fetch_and_backtest_full_range.py

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import MetaTrader5 as mt5

# ============================
# CONFIGURATION
# ============================
SYMBOL       = "XAUUSD"

# Define your start and end dates here (UTC)
START_STR = "2024-11-05 20:00:00"
END_STR   = None  # set to None = fetch up to current time

# Convert to python datetime (naive, then localize to UTC for MT5)
START_DT = datetime.strptime(START_STR, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
END_DT   = datetime.now(timezone.utc) if END_STR is None else datetime.strptime(END_STR, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

# Timeframes
TFS = {
    "30m": mt5.TIMEFRAME_M30,
    "1h":  mt5.TIMEFRAME_H1
}

# Risk parameters (exactly as your live bot/backtests use)
SL_PIPS          = 35    # 35 pips = 3.5 price units
TP_PIPS          = 70    # 70 pips = 7.0 price units
BE_PIPS          = 20    # at +20 pips, move SL → entry + 1 pip
PARTIAL_PIPS     = 40    # at +40 pips, exit 80%
PARTIAL_RATIO    = 0.8
TRAIL_START_PIPS = 50    # at +50, start trailing
TRAIL_DIST_PIPS  = 20    # trailing distance = 20 pips
PIP_SIZE         = 0.1   # on XAUUSD, 1 pip = 0.1 price
PIP_VALUE        = 10    # $10 per pip per 1 lot

# ============================
# 1) INITIALIZE MT5
# ============================
if not mt5.initialize():
    print("Error: MT5 initialization failed")
    sys.exit(1)

# ============================
# 2) FETCH FULL RANGE OF BARS
# ============================
def fetch_full_range(symbol, timeframe, dt_from, dt_to):
    """
    Fetches bars for [dt_from … dt_to] using copy_rates_range.
    Returns a DataFrame with columns ["time","open","high","low","close","tick_volume", ...].
    """
    bars = mt5.copy_rates_range(symbol, timeframe, dt_from, dt_to)
    if bars is None or len(bars) == 0:
        return pd.DataFrame(columns=["time","open","high","low","close","tick_volume","spread","real_volume"])
    df = pd.DataFrame(bars)
    # MT5 returns time in seconds-since-epoch → convert to datetime
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    # Drop timezone info to keep “naive” for everything else
    df["time"] = df["time"].dt.tz_convert(None)
    return df

print(f"Fetching XAUUSD 30 m bars from {START_DT} to {END_DT}…")
df_30m = fetch_full_range(SYMBOL, TFS["30m"], START_DT, END_DT)
print(f"  → {len(df_30m)} bars fetched.")

print(f"Fetching XAUUSD 1 h bars from {START_DT} to {END_DT}…")
df_1h  = fetch_full_range(SYMBOL, TFS["1h"], START_DT, END_DT)
print(f"  → {len(df_1h)} bars fetched.")

mt5.shutdown()

# ============================
# 3) SAVE TO CSV
# ============================
df_30m.to_csv("XAUUSD_30m_full.csv", index=False)
df_1h.to_csv("XAUUSD_1h_full.csv",   index=False)
print("Saved to XAUUSD_30m_full.csv and XAUUSD_1h_full.csv.")

# ============================
# 4) DETECTION FUNCTIONS
# ============================
def detect_fvg(df):
    zones = []
    for i in range(2, len(df)):
        # Bullish FVG: bar[i-2].high < bar[i].low
        if df.high.iat[i-2] < df.low.iat[i]:
            zones.append((i, df.low.iat[i], df.high.iat[i-2], "bull"))
        # Bearish FVG: bar[i-2].low > bar[i].high
        elif df.low.iat[i-2] > df.high.iat[i]:
            zones.append((i, df.high.iat[i], df.low.iat[i-2], "bear"))
    return zones

def detect_ob(df):
    zones = []
    for i in range(1, len(df)-1):
        prev = df.iloc[i-1]
        cur  = df.iloc[i]
        nxt  = df.iloc[i+1]
        # Bullish OB: prev bearish and next bullish closing above cur.close
        if prev.close < prev.open and nxt.close > cur.close:
            zones.append((i, cur.low, cur.high, "bull"))
        # Bearish OB: prev bullish and next bearish closing below cur.close
        elif prev.close > prev.open and nxt.close < cur.close:
            zones.append((i, cur.low, cur.high, "bear"))
    return zones

def find_retests(df, fvg_zones, ob_zones):
    hits = {}
    zones = {}
    # Group zones by their bar index
    for idx, lo, hi, dr in fvg_zones + ob_zones:
        zones.setdefault(idx, []).append((lo, hi, dr))
    for idx, lst in zones.items():
        # Only keep indexes where we have both FVG+OB (len(lst) ≥ 2)
        if len(lst) < 2 or idx + 1 >= len(df):
            continue
        lo, hi, dr = lst[0]
        bar_next = df.iloc[idx+1]
        if dr == "bull":
            if not (bar_next.high >= lo and bar_next.high <= hi):
                continue
        else:
            if not (bar_next.low <= hi and bar_next.low >= lo):
                continue
        # Strict: bar_close must also lie inside [lo…hi]
        if not (lo <= bar_next.close <= hi):
            continue
        hits[idx+1] = dr
    return hits

# ============================
# 5) BACKTEST ENGINE
# ============================
def run_backtest(df, label):
    trades = wins = losses = 0
    weekly_pnl = {}

    fvg_zones = detect_fvg(df)
    ob_zones  = detect_ob(df)
    hits      = find_retests(df, fvg_zones, ob_zones)

    for idx, direction in sorted(hits.items()):
        entry_price = df.close.iat[idx]
        trades += 1

        # (1) Place initial SL/TP
        sl_price = (entry_price - SL_PIPS * PIP_SIZE) if direction == "bull" else (entry_price + SL_PIPS * PIP_SIZE)
        tp_price = (entry_price + TP_PIPS * PIP_SIZE) if direction == "bull" else (entry_price - TP_PIPS * PIP_SIZE)

        be_moved       = False
        partial_taken  = False
        trail_active   = False
        trail_stop     = None
        remaining_lots = 1.0

        for j in range(idx+1, len(df)):
            bar = df.iloc[j]
            low  = bar.low
            high = bar.high
            ts   = bar.time

            # a) Stop-Loss hit?
            if (direction == "bull" and low <= sl_price) or (direction == "bear" and high >= sl_price):
                pnl = -((abs(sl_price - entry_price) / PIP_SIZE) * PIP_VALUE * remaining_lots)
                losses += 1
                wk = pd.to_datetime(ts).to_period("W").start_time
                weekly_pnl.setdefault(wk, 0.0)
                weekly_pnl[wk] += pnl
                break

            # b) Take-Profit hit?
            if (direction == "bull" and high >= tp_price) or (direction == "bear" and low <= tp_price):
                pnl = ((abs(tp_price - entry_price) / PIP_SIZE) * PIP_VALUE * remaining_lots)
                wins += 1
                wk = pd.to_datetime(ts).to_period("W").start_time
                weekly_pnl.setdefault(wk, 0.0)
                weekly_pnl[wk] += pnl
                break

            # c) Move SL to BE+1 at +20 pips
            if not be_moved and (
                (direction == "bull" and high >= entry_price + BE_PIPS * PIP_SIZE) or
                (direction == "bear" and low <= entry_price - BE_PIPS * PIP_SIZE)
            ):
                be_moved = True
                sl_price = entry_price + (PIP_SIZE if direction == "bull" else -PIP_SIZE)

            # d) Partial exit at +40 pips
            if not partial_taken and (
                (direction == "bull" and high >= entry_price + PARTIAL_PIPS * PIP_SIZE) or
                (direction == "bear" and low <= entry_price - PARTIAL_PIPS * PIP_SIZE)
            ):
                partial_taken = True
                pnl_part = ((PARTIAL_PIPS / PIP_SIZE) * PIP_VALUE * PARTIAL_RATIO)
                wk = pd.to_datetime(ts).to_period("W").start_time
                weekly_pnl.setdefault(wk, 0.0)
                weekly_pnl[wk] += pnl_part
                remaining_lots = remaining_lots * (1 - PARTIAL_RATIO)
                # Move SL on remainder to BE+1
                sl_price = entry_price + (PIP_SIZE if direction == "bull" else -PIP_SIZE)

            # e) Trailing on remainder once +50 pips
            if partial_taken and not trail_active and (
                (direction == "bull" and high >= entry_price + TRAIL_START_PIPS * PIP_SIZE) or
                (direction == "bear" and low <= entry_price - TRAIL_START_PIPS * PIP_SIZE)
            ):
                trail_active = True
                trail_stop = (high - TRAIL_DIST_PIPS * PIP_SIZE) if direction == "bull" else (low + TRAIL_DIST_PIPS * PIP_SIZE)

            if trail_active:
                if direction == "bull":
                    new_trail = df.high.iat[j] - TRAIL_DIST_PIPS * PIP_SIZE
                    if new_trail > trail_stop:
                        trail_stop = new_trail
                    if bar.low <= trail_stop:
                        pnl = ((trail_stop - entry_price) / PIP_SIZE) * PIP_VALUE * remaining_lots
                        wins += 1
                        wk = pd.to_datetime(ts).to_period("W").start_time
                        weekly_pnl.setdefault(wk, 0.0)
                        weekly_pnl[wk] += pnl
                        break
                else:
                    new_trail = df.low.iat[j] + TRAIL_DIST_PIPS * PIP_SIZE
                    if new_trail < trail_stop:
                        trail_stop = new_trail
                    if bar.high >= trail_stop:
                        pnl = ((entry_price - trail_stop) / PIP_SIZE) * PIP_VALUE * remaining_lots
                        wins += 1
                        wk = pd.to_datetime(ts).to_period("W").start_time
                        weekly_pnl.setdefault(wk, 0.0)
                        weekly_pnl[wk] += pnl
                        break

    total_weeks    = len(weekly_pnl)
    avg_weekly_pnl = np.mean(list(weekly_pnl.values())) if total_weeks else 0.0
    win_rate       = (wins / trades * 100) if trades else 0.0
    avg_trades_wk  = trades / (((df["time"].max() - df["time"].min()).days) / 7)

    print(f"{label} | Trades: {trades:3d} | Avg Trades/Wk: {avg_trades_wk:5.2f} | "
          f"Win Rate: {win_rate:5.2f}% | Avg Weekly PnL: ${avg_weekly_pnl:7.2f}")
    return avg_weekly_pnl

# ============================
# 6) RUN BACKTEST ON BOTH TIMEFRAMES & COMBINE
# ============================
print("\n--- Strict Intrabar FVG+OB Backtest on Full Range ---\n")
p30 = run_backtest(df_30m, "30 m")
p1  = run_backtest(df_1h,  " 1 h")
print("-------------------------------------------------------")
print(f"COMBINED Avg Weekly PnL: ${p30 + p1:7.2f}\n")
