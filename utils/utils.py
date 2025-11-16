import decimal


def adjust_precision_and_amount(exchange, symbol, amount):
    """
    Automatically adjusts order amount to match exchange precision and limits.

    Parameters:
        - exchange: CCXT exchange instance.
        - symbol: Trading pair (e.g., 'BTC/USDT').
        - amount: Raw order amount.

    Returns:
        - float: Adjusted order amount.

    Raises:
        - ValueError: If precision or amount is invalid.
    """
    try:
        # ✅ Validate the amount
        if amount is None or not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError(f"Invalid amount for precision adjustment: {amount}")
        
        # ✅ Fetch market details
        market = exchange.market(symbol)
        precision = market.get('precision', {}).get('amount', None)
        min_amount = market.get('limits', {}).get('amount', {}).get('min', None)
        max_amount = market.get('limits', {}).get('amount', {}).get('max', None)
        
        if precision is None:
            raise ValueError(f"Precision information missing for symbol {symbol}. Market data: {market}")
        
        if not isinstance(precision, int):
            precision = int(precision)
        
        # ✅ Adjust amount precision using Decimal
        adjusted_amount = decimal.Decimal(str(amount)).quantize(
            decimal.Decimal(f'1e-{precision}'),
            rounding=decimal.ROUND_DOWN
        )
        
        adjusted_amount = float(adjusted_amount)  # Convert back to float for CCXT compatibility
        
        # ✅ Validate against min/max limits
        if min_amount and adjusted_amount < min_amount:
            raise ValueError(f"Adjusted amount {adjusted_amount} is below minimum limit {min_amount}.")
        if max_amount and adjusted_amount > max_amount:
            raise ValueError(f"Adjusted amount {adjusted_amount} exceeds maximum limit {max_amount}.")
        
        return adjusted_amount

    except decimal.InvalidOperation as e:
        raise ValueError(f"Decimal conversion error: {e}. Amount: {amount}")
    except Exception as e:
        raise ValueError(f"Failed to adjust amount and precision: {e}")


def adjust_price(exchange, symbol, price):
    """
    Automatically adjusts order price to match exchange precision.

    Parameters:
        - exchange: CCXT exchange instance.
        - symbol: Trading pair (e.g., 'BTC/USDT').
        - price: Raw order price.

    Returns:
        - float: Adjusted order price.

    Raises:
        - ValueError: If precision or price is invalid.
    """
    try:
        # ✅ Validate price
        if price is None or not isinstance(price, (int, float)) or price <= 0:
            raise ValueError(f"Invalid price for precision adjustment: {price}")
        
        # ✅ Fetch market details
        market = exchange.market(symbol)
        precision = market.get('precision', {}).get('price', None)
        
        if precision is None:
            raise ValueError(f"Price precision missing for symbol {symbol}. Market data: {market}")
        
        if not isinstance(precision, int):
            precision = int(precision)
        
        # ✅ Adjust price precision using Decimal
        adjusted_price = decimal.Decimal(str(price)).quantize(
            decimal.Decimal(f'1e-{precision}'),
            rounding=decimal.ROUND_DOWN
        )
        
        adjusted_price = float(adjusted_price)  # Convert back to float for CCXT compatibility
        
        return adjusted_price

    except decimal.InvalidOperation as e:
        raise ValueError(f"Decimal conversion error: {e}. Price: {price}")
    except Exception as e:
        raise ValueError(f"Failed to adjust price precision: {e}")
