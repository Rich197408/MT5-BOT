#!/usr/bin/env python
import pandas as pd
from datetime import datetime

# ─── SESSION WINDOWS (UTC) ────────────────────────────────────────────────────
SESSIONS = {
    "asia":     ("00:00", "08:00"),
    "london":   ("08:00", "16:00"),
    "new_york": ("14:00", "22:00"),
}


def load_csv(fname: str) -> pd.DataFrame:
    """
    Load a CSV with header row "time,open,high,low,close,volume".
    Skip that row, parse 'time' → datetime, and return sorted DF.
    """
    df = pd.read_csv(
        fname,
        skiprows=1,
        header=None,
        names=["time", "o", "h", "l", "c", "v"],
        dtype={"o": float, "h": float, "l": float, "c": float, "v": float},
    )
    df["time"] = pd.to_datetime(df["time"], errors="raise")
    return df.sort_values("time").reset_index(drop=True)


def get_session(ts: datetime) -> str:
    tstr = ts.strftime("%H:%M")
    for name, (start, end) in SESSIONS.items():
        if start <= tstr < end:
            return name
    return "off"


def detect_fvg(df: pd.DataFrame) -> pd.DataFrame:
    gaps = []
    for i in range(2, len(df)):
        h1, low3 = df.loc[i - 2, "h"], df.loc[i, "l"]
        l1, high3 = df.loc[i - 2, "l"], df.loc[i, "h"]
        t3 = df.loc[i, "time"]
        typ = None
        if h1 < low3:
            typ = "bullish"
        elif l1 > high3:
            typ = "bearish"
        if typ:
            gaps.append({
                "time":    t3,
                "type":    typ,
                "session": get_session(t3),
            })
    return pd.DataFrame(gaps)


def detect_order_blocks(df: pd.DataFrame) -> pd.DataFrame:
    obs = []
    for i in range(1, len(df) - 1):
        prev, cur, nxt = df.loc[i - 1], df.loc[i], df.loc[i + 1]
        t = cur["time"]
        typ = None
        if (prev["c"] < prev["o"]) and (nxt["c"] > cur["c"]):
            typ = "bullish"
        elif (prev["c"] > prev["o"]) and (nxt["c"] < cur["c"]):
            typ = "bearish"
        if typ:
            obs.append({
                "time":    t,
                "type":    typ,
                "session": get_session(t),
            })
    return pd.DataFrame(obs)


def detect_breaker_blocks(df: pd.DataFrame) -> pd.DataFrame:
    bbs = []
    for i in range(2, len(df) - 2):
        # bearish breaker: prior high broken then retested low
        if (df.loc[i - 2, "h"] < df.loc[i, "h"]) and (df.loc[i - 1, "c"] < df.loc[i - 1, "o"]):
            for j in (i + 1, i + 2):
                if df.loc[j, "l"] < df.loc[i - 1, "h"]:
                    bbs.append({
                        "time":    df.loc[j, "time"],
                        "type":    "bearish",
                        "session": get_session(df.loc[j, "time"]),
                    })
        # bullish breaker: prior low broken then retested high
        if (df.loc[i - 2, "l"] > df.loc[i, "l"]) and (df.loc[i - 1, "c"] > df.loc[i - 1, "o"]):
            for j in (i + 1, i + 2):
                if df.loc[j, "h"] > df.loc[i - 1, "l"]:
                    bbs.append({
                        "time":    df.loc[j, "time"],
                        "type":    "bullish",
                        "session": get_session(df.loc[j, "time"]),
                    })
    return pd.DataFrame(bbs)


def detect_bos_choch(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detects:
      - BOS bullish/bearish when new swing high/low breaks prior swing high/low
      - CHOCH bullish/bearish when direction flips after a BOS
    """
    signals = []
    last_swh = last_swl = None
    last_signal = None

    # find swing highs/lows
    for i in range(1, len(df) - 1):
        high = df.loc[i, "h"]
        low = df.loc[i, "l"]
        t = df.loc[i, "time"]

        # swing high
        if high > df.loc[i - 1, "h"] and high > df.loc[i + 1, "h"]:
            if last_swh and high > last_swh:
                signals.append({"time": t, "type": "bos_bullish", "session": get_session(t)})
                if last_signal == "bos_bearish":
                    signals.append({"time": t, "type": "choch_bullish", "session": get_session(t)})
                last_signal = "bos_bullish"
            last_swh = high

        # swing low
        if low < df.loc[i - 1, "l"] and low < df.loc[i + 1, "l"]:
            if last_swl and low < last_swl:
                signals.append({"time": t, "type": "bos_bearish", "session": get_session(t)})
                if last_signal == "bos_bullish":
                    signals.append({"time": t, "type": "choch_bearish", "session": get_session(t)})
                last_signal = "bos_bearish"
            last_swl = low

    return pd.DataFrame(signals)


def main():
    df30 = load_csv("XAUUSD_30m.csv")
    df60 = load_csv("XAUUSD_1h.csv")

    for name, df in [("30 m", df30), ("1 h", df60)]:
        print(f"{name} bars loaded: {len(df)}")
        print(" → FVG:", len(detect_fvg(df)))
        print(" → OB :", len(detect_order_blocks(df)))
        print(" → BB :", len(detect_breaker_blocks(df)))
        print(" → BOS/CHOCH:", len(detect_bos_choch(df)))
        print()


if __name__ == "__main__":
    main()
