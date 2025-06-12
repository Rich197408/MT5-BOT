#!/usr/bin/env python
import pandas as pd
import matplotlib.pyplot as plt

def load_csv(fname):
    # read with header row, parse “time” as datetime, and coerce the rest to floats
    df = pd.read_csv(
        fname,
        header=0,
        parse_dates=['time'],
        dtype={'open': float, 'high': float, 'low': float, 'close': float, 'volume': float},
    )
    # rename columns to match our convention
    df.rename(columns={'open':'o','high':'h','low':'l','close':'c','volume':'v'}, inplace=True)
    df.set_index('time', inplace=True)
    return df

def compute_atr(df, period=14):
    high_low    = df['h'] - df['l']
    high_close  = (df['h'] - df['c'].shift()).abs()
    low_close   = (df['l'] - df['c'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def plot_atr(atr, title):
    plt.figure()
    plt.plot(atr.index, atr, linewidth=1)
    plt.title(f'{title} ATR(14)')
    plt.xlabel('Time (UTC)')
    plt.ylabel('ATR Value')
    plt.tight_layout()
    plt.show()

def main():
    # point these at your 30 m and 1 h files
    df30 = load_csv('confluence_detector/XAUUSD_30m.csv')
    df60 = load_csv('confluence_detector/XAUUSD_1h.csv')

    atr30 = compute_atr(df30)
    atr60 = compute_atr(df60)

    plot_atr(atr30, '30-Minute')
    plot_atr(atr60,  '1-Hour')

if __name__ == '__main__':
    main()
