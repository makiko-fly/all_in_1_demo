import datetime as dt
import pandas as pd
import os
from binance.client import Client
from dotenv import load_dotenv

class Scanner:
    def __init__(self, key, secret):
        print('== init client...')
        self.client = Client(key, secret)
        print('== init universe...')

    def get_latest_snapshot(self):
        tickers_data = self.client.futures_ticker()
        df = pd.DataFrame(tickers_data,
                          columns=['symbol', 'priceChange', 'priceChangePercent', 'weightedAvgPrice', 'lastPrice',
                                   'lastQty', 'openPrice', 'highPrice', 'lowPrice', 'volume', 'quoteVolume', 'openTime',
                                   'closeTime', 'firstId',  'lastId', 'count'])
        df = df[['symbol', 'lastPrice', 'priceChangePercent', 'weightedAvgPrice', 'openPrice', 'highPrice', 'lowPrice',
                 'quoteVolume', 'openTime', 'closeTime']]
        df['lastPrice'] = df['lastPrice'].astype(float)
        df['highPrice'] = df['highPrice'].astype(float)
        df['lowPrice'] = df['lowPrice'].astype(float)
        df['quoteVolume'] = df['quoteVolume'].astype(float)
        df['quoteVolume'] = df['quoteVolume'].astype(int)
        df['openTime'] = (
            df['openTime'].map(lambda x: dt.datetime.fromtimestamp(int(x) / 1000).strftime('%Y-%m-%d %H:%M:%S')))
        df['closeTime'] = (
            df['closeTime'].map(lambda x: dt.datetime.fromtimestamp(int(x) / 1000).strftime('%Y-%m-%d %H:%M:%S')))
        df = df.rename(columns={'symbol': 'Symbol', 'lastPrice': 'LastPrice', 'priceChangePercent': 'Ret',
                                'weightedAvgPrice': 'VWAP', 'openPrice': 'Open', 'highPrice': 'High', 'lowPrice': 'Low',
                                'quoteVolume': 'Amt', 'openTime': 'OpenTime', 'closeTime': 'CloseTime',
                                'lastPriceStr': 'LastPriceStr'})
        df = df.loc[df['Symbol'].str.endswith('USDT')]
        df = df.sort_values(by='Amt', ascending=False)
        df = df.iloc[:100]
        return df


cur_dir = os.path.dirname(os.path.realpath(__file__))
key = ''
secret = ''

if os.path.exists(os.path.join(cur_dir, 'local_secret.py')):
    from local_secret import tmp_data
    key = tmp_data['key']
    secret = tmp_data['secret']
else:
    key = os.environ['BINANCE_API_KEY']
    secret = os.environ['BINANCE_API_SECRET']

scanner = Scanner(key, secret)
