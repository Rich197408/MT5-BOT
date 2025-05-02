import pandas as pd
import pytest
from strategies import SMCStrategy

# helper to build a tiny ohlc DataFrame
def make_df(times, opens, closes):
    return pd.DataFrame({
        'open_30m': opens,
        'close_30m': closes,
        'open_1h':  opens,
        'close_1h': closes,
        'open_4h':  opens,
        'close_4h': closes,
    }, index=pd.to_datetime(times))

@pytest.mark.parametrize("opens,closes,expected", [
    # all three bullish flips on the last bar
    ([2,1,1], [1,2,2], "BUY"),
    # all three bearish flips on the last bar
    ([1,2,2], [2,1,1], "SELL"),
    # mixed flips → NEUTRAL
    ([2,1,2], [1,2,1], "NEUTRAL"),
])
def test_smc_strategy(opens, closes, expected):
    times = ["2025-01-01 00:00", "2025-01-01 00:30", "2025-01-01 01:00"]
    df = make_df(times, opens, closes)
    sig, conf = SMCStrategy("XAUUSD").generate_signal(df)
    assert sig == expected
    # only BUY/SELL returns conf=1.0
    if sig in ("BUY", "SELL"):
        assert conf == 1.0
    else:
        assert conf == 0.0
