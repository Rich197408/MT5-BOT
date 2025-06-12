#!/usr/bin/env python
import pandas as pd

# SESSION WINDOWS (UTC)
SESSIONS = {
    "asia":     ("00:00", "08:00"),
    "london":   ("08:00", "16:00"),
    "new_york": ("14:00", "22:00"),
}

def load_csv(fname):
    """
    Load CSV that has a header row ('time,open,...') plus data.
    We skip the first row, then name columns and parse the time.
    """
    df = pd.read_csv(
        fname,
        skiprows=1,              # drop the original header row
        header=None,
        names=["time", "o", "h", "l", "c", "v"],
        parse_dates=[0],         # parse the first column into datetime
        infer_datetime_format=True,
    )
    return df

def get_session(ts):
    """Return session name for a pandas.Timestamp ts."""
    t = ts.strftime("%H:%M")
    for name, (start, end) in SESSIONS.items():
        if start <= t < end:
            return name
    return "off"

def detect_fvg(df):
    gaps = []
    for i in range(2, len(df)):
        h1, low3 = df.loc[i-2, "h"], df.loc[i, "l"]
        l1, high3 = df.loc[i-2, "l"], df.loc[i, "h"]
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

def detect_order_blocks(df):
    obs = []
    for i in range(1, len(df)-1):
        prev, cur, nxt = df.loc[i-1], df.loc[i], df.loc[i+1]
        t = cur["time"]
        typ = None
        if prev["c"] < prev["o"] and nxt["c"] > cur["c"]:
            typ = "bullish"
        elif prev["c"] > prev["o"] and nxt["c"] < cur["c"]:
            typ = "bearish"
        if typ:
            obs.append({
                "time":    t,
                "type":    typ,
                "session": get_session(t),
            })
    return pd.DataFrame(obs)

def detect_breaker_blocks(df):
    bbs = []
    for i in range(2, len(df)-2):
        # bearish breaker: high broken then retested
        if df.loc[i-2, "h"] < df.loc[i, "h"] and df.loc[i-1, "c"] < df.loc[i-1, "o"]:
            for j in (i+1, i+2):
                if df.loc[j, "l"] < df.loc[i-1, "h"]:
                    bbs.append({
                        "time":    df.loc[j, "time"],
                        "type":    "bearish",
                        "session": get_session(df.loc[j, "time"]),
                    })
        # bullish breaker: low broken then retested
        if df.loc[i-2, "l"] > df.loc[i, "l"] and df.loc[i-1, "c"] > df.loc[i-1, "o"]:
            for j in (i+1, i+2):
                if df.loc[j, "h"] > df.loc[i-1, "l"]:
                    bbs.append({
                        "time":    df.loc[j, "time"],
                        "type":    "bullish",
                        "session": get_session(df.loc[j, "time"]),
                    })
    return pd.DataFrame(bbs)
