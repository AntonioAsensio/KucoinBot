import ccxt
# from config.config import (
#     API_KEY, API_SECRET, API_PASSWORD, SYMBOLS, TIMEFRAMES,
#     TRADE_AMOUNT_PERCENTAGE, ORDER_LOG
# )
from config.config import (
    SYMBOLS, TIMEFRAMES,
    TRADE_AMOUNT_PERCENTAGE, ORDER_LOG
)
import ccxt
from modules.data_fetcher import DataFetcher
from modules.order_manager import OrderManager
# from modules.ScalpingStrategy_2 import ScalpingStrategy
from modules.SSL_HYBRID import SSLHybrid
import time
from datetime import datetime



KUCOIN_API_KEY = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxx'
KUCOIN_API_SECRET = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxx'
KUCOIN_API_PASSWORD = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxx'

# Initialize the exchange
# exchange = ccxt.kucoin({
#     'apiKey': API_KEY,
#     'secret': API_SECRET,
#     'password': API_PASSWORD,
#     'enableRateLimit': True,
# })

exchange = ccxt.kucoin({
    'apiKey': KUCOIN_API_KEY,
    'secret': KUCOIN_API_SECRET,
    'password': KUCOIN_API_PASSWORD,
    'enableRateLimit': True,
})

data_fetcher = DataFetcher(exchange)
order_manager = OrderManager(exchange, ORDER_LOG)


def GetSymbolLastSold (symbol):
    # Fetch the user's trades for the given symbol
    trades = exchange.fetch_my_trades(symbol)
    # print(trades)
    
    # Filter for completed sell market orders
    sell_orders = [
        trade for trade in trades
        # if trade['side'] == 'sell' and trade['type'] == 'market' and trade['status'] == 'closed'
        if trade['side'] == 'sell' and trade['type'] == 'market'
    ]
    
    if not sell_orders:
        print("No completed sell market orders found for the given symbol.")
        return None

    # Sort by timestamp to get the most recent sell order
    most_recent_sell = sorted(sell_orders, key=lambda x: x['timestamp'], reverse=True)[0]

    # Most recent sell tradeID
    most_recent_sell_TradeID = most_recent_sell['id']
    #find all orders with same tradeID
    filled_amount = 0
    for trade in sell_orders:
        print("////////////////")
        print(trade)
        print("////////////////")
        if trade['id'] == most_recent_sell_TradeID:
            filled_amount += trade['amount']


    # market = exchange.market(symbol)
    # precision = market.get('precision', {}).get('amount', None)
    # min_amount = market.get('limits', {}).get('amount', {}).get('min', None)
    # max_amount = market.get('limits', {}).get('amount', {}).get('max', None)
    # if most_recent_sell < min_amount:
    #     most_recent_sell = most_recent_sell = sorted(sell_orders, key=lambda x: x['timestamp'], reverse=True)[1]
    # print("=============================================")
    # print(most_recent_sell)
    # print("=============================================")
    
    # Calculate the value: filled amount * average price
    # filled_amount = most_recent_sell['amount']
    average_price = most_recent_sell['price']
    calculated_value = filled_amount * average_price

    usdt_balance = order_manager.get_balance('USDT')

    if usdt_balance > calculated_value:
        returnAmount = (calculated_value / df['close'].iloc[-1] * 1) # good
    if usdt_balance <= calculated_value:
        returnAmount = (usdt_balance / df['close'].iloc[-1] * 1) # good


    return returnAmount

for symbol in SYMBOLS:
    unrounded_amount = GetSymbolLastSold (symbol)
    print(unrounded_amount)