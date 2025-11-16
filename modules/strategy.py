# modules/strategy.py

def trading_strategy(ohlcv_data):
    """
    Placeholder for user-defined trading strategy.

    Parameters:
    - ohlcv_data (pd.DataFrame): Historical OHLCV data for the symbol.

    Returns:
    - str: 'buy' or 'sell' or 'hold'
    """
    # Example strategy: Buy if the last candle is green, Sell if it's red
    if ohlcv_data['close'].iloc[-1] > ohlcv_data['open'].iloc[-1]:
        return 'buy'
    elif ohlcv_data['close'].iloc[-1] < ohlcv_data['open'].iloc[-1]:
        return 'sell'
    return 'hold'
