from utils.utils import adjust_precision_and_amount, adjust_price
import logging
from pathlib import Path


class OrderManager:
    def __init__(self, exchange, order_log):
        self.exchange = exchange
        self.order_log = order_log
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            # filename='logs/trading.log',
            filename  = Path("logs") / "trading.log",

            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def get_balance(self, currency='USDT'):
        try:
            balance = self.exchange.fetch_balance()
            return balance['free'].get(currency, 0)
        except Exception as e:
            logging.error(f"Error fetching balance: {e}")
            return 0

    def place_market_order(self, symbol, side, amount):
        """
        Places a market order after automatically adjusting amount precision.
        """
        try:
            # adjusted_amount = adjust_precision_and_amount(self.exchange, symbol, amount)
            adjusted_amount = adjust_precision_and_amount(self.exchange, symbol, amount)
            # adjusted_price = adjust_price(self.exchange, symbol, price)
            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=adjusted_amount
            )
            self.log_order(order)
            return order
        except Exception as e:
            logging.error(f"Error placing {side} order for {symbol}: {e}")
            return None

    def place_limit_order(self, symbol, side, amount, price):
        """
        Places a limit order after automatically adjusting amount and price precision.
        """
        try:
            adjusted_amount = adjust_precision_and_amount(self.exchange, symbol, amount)
            adjusted_price = adjust_price(self.exchange, symbol, price)
            order = self.exchange.create_order(
                symbol=symbol,
                type='limit',
                side=side,
                amount=adjusted_amount,
                price=adjusted_price
            )
            self.log_order(order)
            return order
        except Exception as e:
            logging.error(f"Error placing {side} limit order for {symbol}: {e}")
            return None

    def log_order(self, order):
        try:
            with open(self.order_log, mode='a') as file:
                file.write(
                    f"{order['timestamp']},{order['type']},{order['symbol']},{order['amount']},"
                    f"{order.get('price', 'N/A')},{order['status']},{order['id']}\n"
                )
        except Exception as e:
            logging.error(f"Error logging order: {e}")
