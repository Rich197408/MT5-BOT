import backtrader as bt
import pandas as pd
from bt_strategy import MLStrategy

# 1. Read your CSV into a pandas DataFrame
df = pd.read_csv(
    'EURUSD_1h.csv',
    parse_dates=['time'],
    index_col='time'
)

# 2. Initialize Cerebro
cerebro = bt.Cerebro()

# 3. Create a Backtrader data feed from the DataFrame
data = bt.feeds.PandasData(
    dataname=df,
    open='open',
    high='high',
    low='low',
    close='close',
    volume='tick_volume',
    timeframe=bt.TimeFrame.Minutes,
    compression=60
)
cerebro.adddata(data)

# 4. Add your strategy
cerebro.addstrategy(MLStrategy, model_path='multi_tf_rf.pkl')

# 5. Set broker parameters
cerebro.broker.setcash(10000)
cerebro.broker.setcommission(commission=0.0002)

# 6. Run and plot
print('Starting Portfolio Value:', cerebro.broker.getvalue())
cerebro.run()
print('Final Portfolio Value:   ', cerebro.broker.getvalue())
cerebro.plot()
