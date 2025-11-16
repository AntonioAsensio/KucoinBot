import ccxt
import pandas as pd
from datetime import datetime
import time

class DataFetcher:
    def __init__(self, exchange):
        self.exchange = exchange

    def fetch_ohlcv(self, symbol, timeframe='5m', limit=60):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"Error fetching OHLCV data: {e}")
            return pd.DataFrame()
