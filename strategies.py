# strategies.py
import pandas as pd
from typing import List, Tuple

# ─── Order-Block flips ────────────────────────────────────────────────────
def detect_bullish_order_blocks(df: pd.DataFrame, tf: str) -> List[pd.Timestamp]:
    o, c = f"open_{tf}", f"close_{tf}"
    flips: List[pd.Timestamp] = []
    for i in range(1, len(df)):
        prev, curr = df.iloc[i-1], df.iloc[i]
        if prev[c] < prev[o] and curr[c] > curr[o]:
            flips.append(df.index[i])
    return flips

def detect_bearish_order_blocks(df: pd.DataFrame, tf: str) -> List[pd.Timestamp]:
    o, c = f"open_{tf}", f"close_{tf}"
    flips: List[pd.Timestamp] = []
    for i in range(1, len(df)):
        prev, curr = df.iloc[i-1], df.iloc[i]
        if prev[c] > prev[o] and curr[c] < curr[o]:
            flips.append(df.index[i])
    return flips

# ─── Fair-Value Gaps (3-candle gaps) ──────────────────────────────────────
def detect_fvg_bullish(df: pd.DataFrame, tf: str) -> List[pd.Timestamp]:
    """Middle candle of three where gap up: low₂ > high₀"""
    h, l = f"high_{tf}", f"low_{tf}"
    gaps: List[pd.Timestamp] = []
    for i in range(2, len(df)):
        c0, c1, c2 = df.iloc[i-2], df.iloc[i-1], df.iloc[i]
        if c1[l] > c0[h] and c2[l] > c0[h]:
            gaps.append(df.index[i-1])
    return gaps

def detect_fvg_bearish(df: pd.DataFrame, tf: str) -> List[pd.Timestamp]:
    """Middle candle of three where gap down: high₂ < low₀"""
    h, l = f"high_{tf}", f"low_{tf}"
    gaps: List[pd.Timestamp] = []
    for i in range(2, len(df)):
        c0, c1, c2 = df.iloc[i-2], df.iloc[i-1], df.iloc[i]
        if c1[h] < c0[l] and c2[h] < c0[l]:
            gaps.append(df.index[i-1])
    return gaps

# ─── Asian-session high/low (00:00–08:00 GMT) ─────────────────────────────
def prior_asia_range(df: pd.DataFrame, tf: str) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """
    Returns (high_ts, low_ts) of the most recent completed Asian session
    (the 00:00–08:00 GMT bar range), on timeframe tf.
    """
    # group into dates, take bars between 00:00 and 07:00 UTC
    df = df.copy()
    df["date"] = df.index.tz_convert("UTC").date
    # drop today’s partial if trading within Asia hours
    last_date = df["date"].iloc[-1]
    # select prior date
    target = last_date if df.index[-1].hour < 8 else last_date - pd.Timedelta(days=1)
    session = df[(df["date"] == target) & (df.index.hour < 8)]
    if session.empty:
        return None, None
    high_ts = session["high_" + tf].idxmax()
    low_ts  = session["low_"  + tf].idxmin()
    return high_ts, low_ts

# ─── Strategy classes ─────────────────────────────────────────────────────
class SMCStrategy:
    """Smart-Money Concepts with OB + FVG + Asia Range on 1h & 4h."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.tfs = ["1h", "4h"]

    def generate_signal(self, df_feat: pd.DataFrame) -> Tuple[str, float]:
        ts = df_feat.index[-1]
        score = 0
        total = 0

        for tf in self.tfs:
            sub = df_feat[[f"open_{tf}", f"high_{tf}", f"low_{tf}", f"close_{tf}"]]

            # 1) OB flips
            if ts in detect_bullish_order_blocks(sub, tf):
                score += 1
            elif ts in detect_bearish_order_blocks(sub, tf):
                score -= 1
            total += 1

            # 2) FVG
            if ts in detect_fvg_bullish(sub, tf):
                score += 1
            elif ts in detect_fvg_bearish(sub, tf):
                score -= 1
            total += 1

            # 3) Asia session
            high_ts, low_ts = prior_asia_range(df_feat, tf)
            if ts == low_ts:
                score += 1  # bounce off Asia low
            elif ts == high_ts:
                score -= 1  # rejection at Asia high
            total += 1

        # final decision
        if total == 0:
            return "NEUTRAL", 0.0
        conf = abs(score) / total
        if score > 0:
            return "BUY", conf
        if score < 0:
            return "SELL", conf
        return "NEUTRAL", 0.0


class ICTStrategy:
    """Inner Circle Trader stub (extend as you wish)."""

    def __init__(self, symbol: str):
        self.symbol = symbol

    def generate_signal(self, df_feat: pd.DataFrame) -> Tuple[str, float]:
        return "NEUTRAL", 0.0


class SwingStrategy:
    """Swing-high/low stub (extend as you wish)."""

    def __init__(self, symbol: str):
        self.symbol = symbol

    def generate_signal(self, df_feat: pd.DataFrame) -> Tuple[str, float]:
        return "NEUTRAL", 0.0


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
        self.weights = weights
        self.threshold = threshold

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
