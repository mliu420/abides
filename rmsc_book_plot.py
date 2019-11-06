import pandas as pd
pd.set_option('display.max_colwidth', -1)
pd.set_option('display.float_format', lambda x: '%.3f' % x)
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import sys
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()


def plotPriceLevelVolume(orderbook_df):
    def delist(list_of_lists):
        return [x for b in list_of_lists for x in b]
    price_cols = delist([[f"ask_price_{level}", f"bid_price_{level}"] for level in range(1, 6)])
    size_cols = delist([[f"ask_size_{level}", f"bid_size_{level}"] for level in range(1, 6)])
    fig, ax = plt.subplots(nrows=1, ncols=1)
    fig.set_size_inches(35, 15)
    ax.set_title("Orderbook Price Level Volume", size=22)
    ax.set_xlabel("Time", size=24, fontweight='bold')
    ax.set_ylabel("Price (CENTS)", size=24, fontweight='bold')
    ax.set_facecolor("white")
    mid_price = (orderbook_df.ask_price_1 + orderbook_df.bid_price_1) / 2
    mid_price = mid_price.ffill()
    myFmt = DateFormatter("%H:%M")
    ax.xaxis.set_major_formatter(myFmt)
    ax.plot(orderbook_df.timestamp, mid_price, color='black')
    for price_col, size_col in zip(price_cols, size_cols):
        im = ax.scatter(x=orderbook_df.timestamp, y=orderbook_df[price_col].astype(float), c=orderbook_df[size_col], s=0.7, cmap=plt.cm.jet, alpha=0.7)
    cbar = fig.colorbar(im, ax=ax, label='volume')
    cbar.ax.get_yaxis().labelpad = 20
    cbar.ax.set_ylabel('Size', rotation=270, fontsize=20, fontweight='bold')

if len(sys.argv) < 2:
    print("Usage: python rmsc_book_plot.py <Order Book DataFrame file>")
    sys.exit()

book_file = sys.argv[1]

orderbook_df = pd.read_pickle(f'{book_file}')
orderbook_df = orderbook_df.reset_index().rename({'index' : 'timestamp'}, axis=1)

plotPriceLevelVolume(orderbook_df)
#plt.show()
plt.savefig('OrderBook.png')
