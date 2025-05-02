# export_all_csv.py

from fetch_eurusd_attach import fetch_mt5_ohlcv

def export_tf(symbol: str, tf: str, count: int, filename: str):
    """
    Fetch 'count' bars of 'symbol' at timeframe 'tf' and save to 'filename'.
    """
    print(f"⏳ Fetching {symbol} @ {tf} ({count} bars)...", end=" ")
    df = fetch_mt5_ohlcv(symbol, tf, count)
    df.to_csv(filename, index=True, date_format="%Y-%m-%d %H:%M:%S")
    print("✅ Saved", filename)

def main():
    SYMBOL = "EURUSD"
    tasks = [
        # (timeframe, #bars, output CSV)
        ("4h",   500,  "EURUSD_4h.csv"),
        ("1h",   2000, "EURUSD_1h.csv"),
        ("30m",  4000, "EURUSD_30m.csv"),
        ("15m",  8000, "EURUSD_15m.csv"),  # <— newly added
    ]

    for tf, cnt, fname in tasks:
        export_tf(SYMBOL, tf, cnt, fname)

if __name__ == "__main__":
    main()



