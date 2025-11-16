import ccxt
import pandas as pd
import numpy as np
import time
from tqdm import tqdm

# User-configurable parameters
MIN_VOLUME = 100000  # Minimum 24h trading volume
MIN_VOLATILITY = 2.5  # Minimum volatility percentage
BB_PERIOD = 20  # Bollinger Bands period
LONG_TICK = '4h'  # Timeframe for initial squeeze detection
SHORT_TICK = '1h'  # Timeframe for confirming breakout direction

# Initialize CCXT KuCoin API client
exchange = ccxt.kucoin()

def fetch_with_retry(func, *args, max_retries=5, delay=exchange.rateLimit / 1000, **kwargs):
    """Fetch data with retries on rate limit errors."""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except ccxt.ExchangeError as e:
            if '429000' in str(e):
                print(f"Rate limit hit. Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
            else:
                raise
    raise Exception("Max retries exceeded")

def get_market_data(symbol, timeframe, limit=100):
    """Fetch historical market data for a given symbol and timeframe."""
    candles = fetch_with_retry(exchange.fetch_ohlcv, symbol, timeframe, limit=limit)
    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df.astype(float)
    return df

def compute_rsi(series, period=14):
    """Compute Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_volume_indicators(df):
    """Compute Accumulation/Distribution Index as a volume-based indicator."""
    money_flow_multiplier = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
    money_flow_volume = money_flow_multiplier * df['volume']
    df['acc_dist'] = money_flow_volume.cumsum()
    return df

def bollinger_bands(series, period=BB_PERIOD, std_dev=2):
    """Compute Bollinger Bands."""
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper_band = sma + (std_dev * std)
    lower_band = sma - (std_dev * std)
    return upper_band, lower_band

def detect_bollinger_squeeze(df):
    """Detect Bollinger Squeeze condition."""
    upper_band, lower_band = bollinger_bands(df['close'])
    df['bb_width'] = (upper_band - lower_band) / lower_band
    return df['bb_width'].iloc[-1] < df['bb_width'].rolling(50).min().iloc[-1]

def determine_breakout_direction(df):
    """Determine breakout direction using RSI and Acc/Dist Index."""
    df = compute_volume_indicators(df)
    rsi = compute_rsi(df['close'])
    
    price_trending_up = df['close'].iloc[-1] > df['close'].iloc[-5]
    rsi_trending_up = rsi.iloc[-1] > rsi.iloc[-5]
    acc_dist_trending_up = df['acc_dist'].iloc[-1] > df['acc_dist'].iloc[-5]

    bullish_signal = price_trending_up and (rsi_trending_up or acc_dist_trending_up)
    return bullish_signal

def filter_altcoins():
    """Fetch market data and filter USDT altcoins suitable for trading."""
    tickers = fetch_with_retry(exchange.fetch_tickers)
    shortlisted = []

    for symbol, ticker in tqdm(tickers.items(), desc="Filtering USDT Altcoins"):
        if not symbol.endswith('/USDT'):
            continue
        
        volume = ticker.get('quoteVolume', 0)
        high, low = ticker.get('high', 0), ticker.get('low', 0)
        volatility = ((high - low) / low) * 100 if low > 0 else 0

        if volume > MIN_VOLUME and volatility > MIN_VOLATILITY:
            shortlisted.append(symbol)

    return shortlisted

def analyze_bollinger_squeeze():
    """Identify coins experiencing a Bollinger Squeeze and analyze breakout direction."""
    Initial_Bollinger_Squeeze_List_1D = []
    Bullish_Bollinger_Squeeze_List_1D = []

    shortlisted_coins = filter_altcoins()

    for coin in tqdm(shortlisted_coins, desc="Analyzing Bollinger Squeeze"):
        df = get_market_data(coin, timeframe=LONG_TICK)
        
        if detect_bollinger_squeeze(df):
            Initial_Bollinger_Squeeze_List_1D.append(coin)
            
            if determine_breakout_direction(df):
                Bullish_Bollinger_Squeeze_List_1D.append(coin)

    return Bullish_Bollinger_Squeeze_List_1D

def confirm_breakout_on_short_tick(bullish_list):
    """Analyze each coin in Bullish_Bollinger_Squeeze_List_1D on a short timeframe."""
    confirmed_trades = []

    for coin in tqdm(bullish_list, desc="Confirming breakout on short tick"):
        df = get_market_data(coin, timeframe=SHORT_TICK)
        
        if determine_breakout_direction(df):
            confirmed_trades.append(coin)

    return confirmed_trades

def generate_trade_details(coin):
    """Generate trade details and output format."""
    df = get_market_data(coin, timeframe=SHORT_TICK)
    latest_close = df['close'].iloc[-1]
    atr = df['high'].rolling(window=14).mean().iloc[-1] - df['low'].rolling(window=14).mean().iloc[-1]

    entry = latest_close
    stop_loss = latest_close - (1.5 * atr)
    target1 = latest_close + (1.5 * atr)
    target2 = latest_close + (2.5 * atr)
    target3 = latest_close + (4 * atr)
    final_target = latest_close + (6 * atr)

    trade_setup = f"""
    🔹 **Trade Setup for {coin}** 🔹
    
    📌 [Trade on KuCoin](https://www.kucoin.com/trade/{coin.replace('/', '-')})
    
    🔹 **Entry Price:** {entry:.4f}
    🔹 **Stop Loss:** {stop_loss:.4f} (🔻 {(entry - stop_loss) / entry * 100:.2f}%)
    
    🎯 **Targets:**
    - Target 1: {target1:.4f} (+{((target1 - entry) / entry) * 100:.2f}%)
    - Target 2: {target2:.4f} (+{((target2 - entry) / entry) * 100:.2f}%)
    - Target 3: {target3:.4f} (+{((target3 - entry) / entry) * 100:.2f}%)
    - Final Target: {final_target:.4f} (+{((final_target - entry) / entry) * 100:.2f}%)
    """
    
    return trade_setup

def execute_strategy():
    """Execute the entire trading strategy."""
    print("🔍 Scanning for Bollinger Squeeze setups on 1D timeframe...")
    bullish_squeeze_list = analyze_bollinger_squeeze()

    print("bullish_squeeze_list:")
    print(bullish_squeeze_list)
    
    print("✅ Confirming breakouts on 1H timeframe...")
    final_trade_list = confirm_breakout_on_short_tick(bullish_squeeze_list)

    for coin in final_trade_list:
        trade_details = generate_trade_details(coin)
        print(trade_details)






# Run the strategy
execute_strategy()
