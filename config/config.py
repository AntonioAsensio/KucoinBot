import os
#from dotenv import load_dotenv

#load_dotenv()

# API_KEY = os.getenv('KUCOIN_API_KEY')
# API_SECRET = os.getenv('KUCOIN_API_SECRET')
# API_PASSWORD = os.getenv('KUCOIN_API_PASSWORD')

# SYMBOLS = ['PNDR/USDT', 'GRIFFAIN/USDT', 'LAI/USDT', 'WSDM/USDT', 'XTAG/USDT']  # Add more pairs here
# SYMBOLS = ['OPAI/USDT', 'XTAG/USDT', 'SCPT/USDT', 'WSDM/USDT', 'NOTAI/USDT', 'ICE/USDT', 'DOAI/USDT']  # Add more pairs here
SYMBOLS = ['OPAI/USDT']
# SYMBOLS = ['OPAI/USDT']  # Add more pairs here
TIMEFRAMES = ['1m', '5m', '15m' '1h']  # Different timeframes
TRADE_AMOUNT_PERCENTAGE = 0.1  # 10% of available balance per trade
LOG_FILE = 'logs/trading.log'
ORDER_LOG = 'orders/orders.csv'
