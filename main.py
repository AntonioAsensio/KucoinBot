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
from pathlib import Path


def main(): 

    KUCOIN_API_KEY = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    KUCOIN_API_SECRET = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    KUCOIN_API_PASSWORD = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'

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

    orders_file_path = Path("orders") / "SSLHybrid_orders.txt"


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
        most_recent_sell_TradeID = most_recent_sell['order']
        # most_recent_sell_TradeID = most_recent_sell['orderId']
        #find all orders with same tradeID
        calculated_value = 0
        for trade in sell_orders:
            print("////////////////")
            print(trade)
            print("////////////////")
            if trade['order'] == most_recent_sell_TradeID:
                calculated_value += trade['cost']

        print(f"calculated_value = {calculated_value}")
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
        # average_price = most_recent_sell['price']
        # calculated_value = filled_amount * average_price

        usdt_balance = order_manager.get_balance('USDT')
        
        if usdt_balance > calculated_value:
            returnAmount = (calculated_value / df['close'].iloc[-1] * 1) # good
        if usdt_balance <= calculated_value:
            returnAmount = (usdt_balance / df['close'].iloc[-1] * 1) # good


        return returnAmount

    
    while True:
            try:
                for symbol in SYMBOLS:

                    # _test_Delete = GetSymbolLastSold (symbol)
                    # print(_test_Delete)
                    action_time = datetime.now()
                    print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")
                    print(f"\n**********{action_time} **  {symbol}**********\n")
                    df = data_fetcher.fetch_ohlcv(symbol, '5m', limit=90)

                    strategy = SSLHybrid(atr_period=14, atr_multiplier=1, baseline_length=60)
                    strategy = SSLHybrid(
                        atr_period=14,
                        atr_multiplier=1,
                        baseline_length=60,
                        ssl2_length=5,
                        exit_length=15
                        )

                    # df = strategy.calculate_indicators(df)
                    action = strategy.process_signals(df)
                    
                    if action == 'buy':
                        print("Action is BUY")
                        usdt_balance = order_manager.get_balance('USDT')
                        owned_amount = order_manager.get_balance(symbol.split('/')[0])
                        
                        print(f" owned_amount= {owned_amount}")

                        if usdt_balance > 5.0 and owned_amount < 10.0: # hack

                            unrounded_amount = GetSymbolLastSold (symbol)
                            
                            # amount = usdt_balance / df['close'].iloc[-1] * 0.1
                            # unrounded_amount = (usdt_balance / df['close'].iloc[-1] * 1) # good
                            # unrounded_amount = (30 / df['close'].iloc[-1] * 1) # kack
                            amount = round(unrounded_amount, 6)
                            order_manager.place_market_order(symbol,'buy',amount)

                            # tot = owned_amount * df['close'].iloc[-1]*amount
                            # order_buy = f"\n{action_time},{symbol},buy,{amount},{df['close'].iloc[-1],{tot}}"
                            order_buy = f"\n{action_time},{symbol},buy,{amount},{df['close'].iloc[-1]}"
                            # orders_file = open(r"D:\_KRYPTO_\KUCOIN_BOT\orders\SSLHybrid_orders.txt","a")
                            orders_file = open(orders_file_path,"a")
                            orders_file.write(order_buy)
                            orders_file.close()

                            print(f"\n {action_time} BUYING!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

                    elif action == 'sell':
                        print("Action is SELL")
                        owned_amount = order_manager.get_balance(symbol.split('/')[0])
                        if owned_amount > 0:
                            order_manager.place_market_order(symbol, 'sell', owned_amount)
                            # order_manager.place_market_order(symbol, 'sell', 10) # Hack for Opai

                            # tot = owned_amount * df['close'].iloc[-1]
                            # order_sell = f"\n{action_time},{symbol},sell,{owned_amount},{df['close'].iloc[-1]}, {tot}"
                            order_sell = f"\n{action_time},{symbol},sell,{owned_amount},{df['close'].iloc[-1]}"
                            # orders_file = open(r"D:\_KRYPTO_\KUCOIN_BOT\orders\SSLHybrid_orders.txt","a")
                            orders_file = open(orders_file_path,"a")
                            orders_file.write(order_sell)
                            orders_file.close()

                            print(f"{action_time} SELLING!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    else:
                        print(f"\nNo action for {symbol}.\n~~~~~~~~~~~~~~~~~~~~~~~~~~\n")
                print("Scan done, wating 1 mins")
                print("========================================================================= \n")

                time.sleep(60)

            except Exception as e:
                print(f"Error: {e}")
                time.sleep(120)


    

    #===============

    # data_fetcher = DataFetcher(exchange)
    # order_manager = OrderManager(exchange, ORDER_LOG)
    # while True:
    #         try:
    #             for symbol in SYMBOLS:
    #                 print(f"\n--- Trading symbol: {symbol} ---")
    #                 print(datetime.now())
                    
    #                 # Fetch OHLCV data
    #                 df = data_fetcher.fetch_ohlcv(symbol, timeframe='15m')
    #                 if df.empty:
    #                     print("Failed to fetch OHLCV data.")
    #                     continue

    #                 # Apply trading strategy
    #                 scalpingStrategy = ScalpingStrategy()
    #                 action = scalpingStrategy.run(df)
    #                 print(f"Strategy Decision: {action}")

    #                 if action == 'buy':
    #                     usdt_balance = order_manager.get_balance('USDT')
    #                     owned_amount = order_manager.get_owned_amount(symbol)


    #                     if usdt_balance > 10 & owned_amount < 0.5:  # Ensure a minimum trade size, and making sure you do not buy if you have not sold
    #                         # amount = (usdt_balance * TRADE_AMOUNT_PERCENTAGE) / df['close'].iloc[-1]
    #                         # amount = (usdt_balance * TRADE_AMOUNT_PERCENTAGE) / df['close'].iloc[-1]
    #                         amount = 10 / df['close'].iloc[-1]
    #                         print(f"Placing market BUY order for {symbol} with amount {amount:.6f}")
    #                         print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    #                         order_manager.place_order(symbol, 'buy', amount)
    #                     else:
    #                         print("Insufficient USDT balance for BUY.")


    #                 elif action == 'sell':
    #                     owned_amount = order_manager.get_owned_amount(symbol)
    #                     if owned_amount > 0.5:
    #                         print(f"Placing market SELL order for {symbol} with amount {owned_amount:.6f}")
    #                         print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    #                         order_manager.place_order(symbol, 'sell', owned_amount)
    #                     else:
    #                         print(f"No owned amount of {symbol.split('/')[0]} available to SELL.")

    #                 else:
    #                     print("No action taken (HOLD).")
    #                     print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")


    #             print("Scan done, wating 5 mins")
    #             print("=========================================================================")

    #             time.sleep(300)
        
    #         except Exception as e:
    #             print(f"Error: {e}")
    #             time.sleep(120)



if __name__ == "__main__":
    main()
