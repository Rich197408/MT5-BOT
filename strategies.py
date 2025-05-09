# strategies.py

import pandas as pd
from typing import List, Tuple

# ─── Detectors ───────────────────────────────────────────────────────────────

def detect_bullish_order_blocks(df: pd.DataFrame, tf: str) -> List[pd.Timestamp]:
    if df.shape[0] < 2:
        return []
    o, c = f"open_{tf}", f"close_{tf}"
    flips = []
    for i in range(1, len(df)):
        prev, curr = df.iloc[i-1], df.iloc[i]
        # bearish → bullish
        if prev[c] < prev[o] and curr[c] > curr[o]:
            flips.append(df.index[i])
    return flips

def detect_bearish_order_blocks(df: pd.DataFrame, tf: str) -> List[pd.Timestamp]:
    if df.shape[0] < 2:
        return []
    o, c = f"open_{tf}", f"close_{tf}"
    flips = []
    for i in range(1, len(df)):
        prev, curr = df.iloc[i-1], df.iloc[i]
        # bullish → bearish
        if prev[c] > prev[o] and curr[c] < curr[o]:
            flips.append(df.index[i])
    return flips

def detect_fvg_bullish(df: pd.DataFrame, tf: str) -> List[pd.Timestamp]:
    """Bullish FVG when bar₂.low > bar₀.high  (zone = [bar₀.high, bar₂.low])."""
    if df.shape[0] < 3:
        return []
    h0 = f"high_{tf}"
    l2 = f"low_{tf}"
    gaps = []
    for i in range(2, len(df)):
        first, middle, third = df.iloc[i-2], df.iloc[i-1], df.iloc[i]
        if third[l2] > first[h0]:
            gaps.append(df.index[i])
    return gaps

def detect_fvg_bearish(df: pd.DataFrame, tf: str) -> List[pd.Timestamp]:
    """Bearish FVG when bar₂.high < bar₀.low  (zone = [bar₂.high, bar₀.low])."""
    if df.shape[0] < 3:
        return []
    l0 = f"low_{tf}"
    h2 = f"high_{tf}"
    gaps = []
    for i in range(2, len(df)):
        first, middle, third = df.iloc[i-2], df.iloc[i-1], df.iloc[i]
        if third[h2] < first[l0]:
            gaps.append(df.index[i])
    return gaps

def detect_liquidity_bullish(df: pd.DataFrame, tf: str) -> List[pd.Timestamp]:
    """5-bar swing-low fractal: bar low is lowest of two before & two after."""
    if df.shape[0] < 5:
        return []
    l = f"low_{tf}"
    zones = []
    for i in range(2, len(df)-2):
        window = df[l].iloc[i-2:i+3]
        if df[l].iloc[i] == window.min():
            zones.append(df.index[i])
    return zones

def detect_liquidity_bearish(df: pd.DataFrame, tf: str) -> List[pd.Timestamp]:
    """5-bar swing-high fractal: bar high is highest of two before & two after."""
    if df.shape[0] < 5:
        return []
    h = f"high_{tf}"
    zones = []
    for i in range(2, len(df)-2):
        window = df[h].iloc[i-2:i+3]
        if df[h].iloc[i] == window.max():
            zones.append(df.index[i])
    return zones

def prior_asia_range(df: pd.DataFrame, tf: str) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """
    Returns the timestamps of the prior Asia session high (00:00–08:00 UTC) 
    and low, treating the index as UTC-naive.
    """
    if df.shape[0] == 0:
        return None, None
    dates = df.index.date
    last_date = dates[-1]
    # if current bar-hour < 8, the last completed Asia is yesterday
    if df.index.hour[-1] < 8:
        target = last_date - pd.Timedelta(days=1)
    else:
        target = last_date
    session = df[(df.index.date == target) & (df.index.hour < 8)]
    if session.empty:
        return None, None
    high_ts = session[f"high_{tf}"].idxmax()
    low_ts  = session[f"low_{tf}"].idxmin()
    return high_ts, low_ts

# ─── Strategy Classes ──────────────────────────────────────────────────────

class SMCStrategy:
    """Smart-Money Concepts on 1h & 4h: OB, FVG, Liquidity & Asia-Range."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.tfs = ["1h", "4h"]

    def generate_signal(self, df_feat: pd.DataFrame) -> Tuple[str, float]:
        ts = df_feat.index[-1]
        score = 0
        total = 0

        for tf in self.tfs:
            sub = df_feat[[f"open_{tf}", f"high_{tf}", f"low_{tf}", f"close_{tf}"]]

            # OB flips
            total += 1
            if ts in detect_bullish_order_blocks(sub, tf):
                score += 1
            elif ts in detect_bearish_order_blocks(sub, tf):
                score -= 1

            # FVG
            total += 1
            if ts in detect_fvg_bullish(sub, tf):
                score += 1
            elif ts in detect_fvg_bearish(sub, tf):
                score -= 1

            # Liquidity Pools
            total += 1
            if ts in detect_liquidity_bullish(sub, tf):
                score += 1
            elif ts in detect_liquidity_bearish(sub, tf):
                score -= 1

            # Asia-range
            total += 1
            high_ts, low_ts = prior_asia_range(df_feat, tf)
            if ts == low_ts:
                score += 1
            elif ts == high_ts:
                score -= 1

        if total == 0 or score == 0:
            return "NEUTRAL", 0.0
        conf = abs(score) / total
        return ("BUY", conf) if score > 0 else ("SELL", conf)


class ICTStrategy:
    """
    Inner Circle Trader: retest-based entries on OB, FVG & Asia-range.
    Retraces are counted on 15m & 30m only.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.tfs = ["15m", "30m", "1h", "4h"]

    def generate_signal(self, df_feat: pd.DataFrame) -> Tuple[str, float]:
        ts = df_feat.index[-1]
        score = 0
        total = 0

        for tf in self.tfs:
            sub = df_feat[[f"open_{tf}", f"high_{tf}", f"low_{tf}", f"close_{tf}"]]

            # 1) OB retest (only on 15m & 30m)
            if tf in ("15m", "30m"):
                flips_bull = detect_bullish_order_blocks(sub, tf)
                flips_bear = detect_bearish_order_blocks(sub, tf)
                last_flip = [t for t in flips_bull + flips_bear if t < ts]
                if last_flip:
                    last_ts = max(last_flip)
                    idx = sub.index.get_loc(last_ts)
                    prev = sub.iloc[idx-1]
                    low_z, high_z = prev[f"low_{tf}"], prev[f"high_{tf}"]
                    row = sub.loc[ts]
                    total += 1
                    if last_ts in flips_bull and row["low_"+tf] <= low_z:
                        score += 1
                    elif last_ts in flips_bear and row["high_"+tf] >= high_z:
                        score -= 1

            # 2) FVG retest (only on 15m & 30m)
            if tf in ("15m", "30m"):
                gaps_bull = detect_fvg_bullish(sub, tf)
                gaps_bear = detect_fvg_bearish(sub, tf)
                last_gap = [t for t in gaps_bull + gaps_bear if t < ts]
                if last_gap:
                    gts = max(last_gap)
                    idx = sub.index.get_loc(gts)
                    first, third = sub.iloc[idx-2], sub.iloc[idx]
                    z_low, z_high = first[f"high_{tf}"], third[f"low_{tf}"]
                    row = sub.loc[ts]
                    total += 1
                    if gts in gaps_bull and row["low_"+tf] <= z_low:
                        score += 1
                    elif gts in gaps_bear and row["high_"+tf] >= z_high:
                        score -= 1

            # 3) Asia-range retest on every TF
            total += 1
            high_ts, low_ts = prior_asia_range(df_feat, tf)
            if ts == low_ts:
                score += 1
            elif ts == high_ts:
                score -= 1

        if total == 0 or score == 0:
            return "NEUTRAL", 0.0
        conf = abs(score) / total
        return ("BUY", conf) if score > 0 else ("SELL", conf)


class SwingStrategy:
    """
    Swing-high/low liquidity entries + Asia-range confluence.
    Retraces are counted on 15m & 30m only.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.tfs = ["15m", "30m", "1h", "4h"]

    def generate_signal(self, df_feat: pd.DataFrame) -> Tuple[str, float]:
        ts = df_feat.index[-1]
        score = 0
        total = 0

        for tf in self.tfs:
            sub = df_feat[[f"open_{tf}", f"high_{tf}", f"low_{tf}", f"close_{tf}"]]

            # Liquidity fractal retest (15m & 30m only)
            if tf in ("15m", "30m"):
                lows = detect_liquidity_bullish(sub, tf)
                highs = detect_liquidity_bearish(sub, tf)
                last_liq = [t for t in lows + highs if t < ts]
                if last_liq:
                    lts = max(last_liq)
                    row = sub.loc[ts]
                    total += 1
                    if lts in lows and row["low_"+tf] <= sub.loc[lts][f"low_{tf}"]:
                        score += 1
                    elif lts in highs and row["high_"+tf] >= sub.loc[lts][f"high_{tf}"]:
                        score -= 1

            # Asia-range retest on every TF
            total += 1
            high_ts, low_ts = prior_asia_range(df_feat, tf)
            if ts == low_ts:
                score += 1
            elif ts == high_ts:
                score -= 1

        if total == 0 or score == 0:
            return "NEUTRAL", 0.0
        conf = abs(score) / total
        return ("BUY", conf) if score > 0 else ("SELL", conf)


class SignalEngine:
    """Aggregate multiple strategies with weights & threshold."""

    def __init__(self,
                 strategies: List,
                 weights: List[float],
                 threshold: float):
        if len(strategies) != len(weights):
            raise ValueError("strategies & weights length mismatch")
        if abs(sum(weights) - 1.0) > 1e-6:
            raise ValueError("weights must sum to 1.0")
        self.strategies = strategies
        self.weights    = weights
        self.threshold  = threshold

    def aggregate(self, df_feat: pd.DataFrame) -> Tuple[str, float]:
        total = 0.0
        for strat, w in zip(self.strategies, self.weights):
            sig, conf = strat.generate_signal(df_feat)
            if sig == "BUY":
                total += conf * w
            elif sig == "SELL":
                total -= conf * w
        final_conf = abs(total)
        if total >= self.threshold:
            return "BUY", final_conf
        if total <= -self.threshold:
            return "SELL", final_conf
        return "NEUTRAL", final_conf
