import ccxt
import pandas as pd
import numpy as np
import time
from tqdm import tqdm

# User-configurable parameters
MIN_VOLUME = 100000  # Minimum 24h trading volume
MIN_VOLATILITY = 2.5  # Minimum volatility percentage

def compute_rsi(series, period=14):
    """Compute Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_macd(series, short_period=12, long_period=26, signal_period=9):
    """Compute MACD and Signal Line."""
    short_ema = series.ewm(span=short_period, adjust=False).mean()
    long_ema = series.ewm(span=long_period, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=signal_period, adjust=False).mean()
    return macd, signal

def compute_atr(df, period=14):
    """Compute Average True Range (ATR)."""
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def compute_supertrend(df, period=10, multiplier=3):
    """Compute Supertrend Indicator."""
    atr = compute_atr(df, period)
    hl2 = (df['high'] + df['low']) / 2
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    supertrend = pd.Series(index=df.index, dtype='float64')
    direction = 1
    for i in range(1, len(df)):
        if df['close'].iloc[i] > upper_band.iloc[i - 1]:
            direction = 1
        elif df['close'].iloc[i] < lower_band.iloc[i - 1]:
            direction = -1
        supertrend.iloc[i] = upper_band.iloc[i] if direction == 1 else lower_band.iloc[i]
    return supertrend

def bollinger_bands(series, period=20, std_dev=2):
    """Compute Bollinger Bands."""
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper_band = sma + (std_dev * std)
    lower_band = sma - (std_dev * std)
    return upper_band, lower_band

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


def get_market_data(symbol, timeframe, limit):
    """Fetch historical market data for a given symbol and timeframe."""
    candles = fetch_with_retry(exchange.fetch_ohlcv, symbol, timeframe, limit=limit)
    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df.astype(float)
    return df

def define_trade_levels(df, symbol, strategy_name, volume, volatility):
    """Define entry, stop loss, and target levels using ATR and Fibonacci extensions."""
    latest_close = df['close'].iloc[-1]
    atr = compute_atr(df).iloc[-1]
    
    entry = latest_close
    stop_loss = latest_close - (1.5 * atr)
    target1 = latest_close + (1.5 * atr)
    target2 = latest_close + (2.5 * atr)
    final_target = latest_close + (4 * atr)

    # Calculate % increase for each target
    t1_perc = ((target1 - entry) / entry) * 100
    t2_perc = ((target2 - entry) / entry) * 100
    final_perc = ((final_target - entry) / entry) * 100

    # Formatted output
    trade_setup = f"""
    🔹 **Trade Setup for {symbol}** 🔹
    
    📈 **Strategy Triggered:** {strategy_name}
    📊 **24H Volume:** {volume:,.0f}
    🌊 **Volatility:** {volatility:.2f}%

    🔹 **Entry Price:** {entry:.4f}
    🔹 **Stop Loss:** {stop_loss:.4f} (🔻 {(entry - stop_loss) / entry * 100:.2f}%)
    
    🎯 **Targets:**
    - Target 1: {target1:.4f} (+{t1_perc:.2f}%)
    - Target 2: {target2:.4f} (+{t2_perc:.2f}%)
    - Final Target: {final_target:.4f} (+{final_perc:.2f}%)
    """

    return trade_setup


def filter_altcoins(min_volume=MIN_VOLUME, min_volatility=MIN_VOLATILITY):
    """Fetch market data and filter USDT altcoins suitable for momentum trading."""
    tickers = fetch_with_retry(exchange.fetch_tickers)
    shortlisted = []
    
    for symbol, ticker in tqdm(tickers.items(), desc="Filtering USDT Altcoins"):
        if not symbol.endswith('/USDT'):  # Filter for USDT pairs only
            continue

        volume = ticker.get('quoteVolume')
        high, low = ticker.get('high'), ticker.get('low')

        # Ensure high and low values are not None and avoid division by zero
        if high is None or low is None or low == 0:
            print(f"Skipping {symbol} due to missing or invalid high/low values.")
            continue

        volatility = ((high - low) / low) * 100
        if volume and volume > min_volume and volatility > min_volatility:
            shortlisted.append(symbol)
    
    return shortlisted



def apply_momentum_strategy_1D(df):
    df['rsi'] = compute_rsi(df['close'])
    df['macd'], df['macd_signal'] = compute_macd(df['close'])
    df['atr'] = compute_atr(df)
    df['supertrend'] = compute_supertrend(df)
    return (df['rsi'].iloc[-1] > 55) & (df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]) & (df['close'].iloc[-1] > df['supertrend'].iloc[-1])

def apply_momentum_strategy_4H(df):
    df['rsi'] = compute_rsi(df['close'])
    df['macd'], df['macd_signal'] = compute_macd(df['close'])
    df['supertrend'] = compute_supertrend(df)
    return (df['rsi'].iloc[-1] > 55) & (df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]) & (df['close'].iloc[-1] > df['supertrend'].iloc[-1])

def apply_trend_reversal_strategy(df):
    """Check for trend reversal conditions using TradingView-style indicators."""
    
    # Compute indicators
    df['rsi'] = compute_rsi(df['close'])
    df['macd'], df['macd_signal'] = compute_macd(df['close'])
    df['supertrend'] = compute_supertrend(df)
    df['stoch_rsi'] = compute_rsi(df['rsi'], period=14)  # RSI of RSI (Stochastic RSI)
    
    # Ensure enough data points
    if len(df) < 5:
        return False  

    # RSI Divergence (Price making lower low, RSI making higher low)
    rsi_divergence = (df['close'].iloc[-1] < df['close'].iloc[-3]) and (df['rsi'].iloc[-1] > df['rsi'].iloc[-3])

    # MACD Bullish Crossover
    macd_crossover = df['macd'].iloc[-1] > df['macd_signal'].iloc[-1] and df['macd'].iloc[-2] < df['macd_signal'].iloc[-2]

    # Supertrend Flip (Price moves above Supertrend)
    supertrend_flip = df['close'].iloc[-1] > df['supertrend'].iloc[-1] and df['close'].iloc[-2] < df['supertrend'].iloc[-2]

    # Bollinger Band Squeeze Breakout
    df['bb_upper'], df['bb_lower'] = bollinger_bands(df['close'])  # Compute Bollinger Bands
    bb_squeeze = (df['close'].iloc[-1] > df['bb_upper'].iloc[-2])  # Breakout above upper band

    # Stochastic RSI Bullish Cross (Oversold area)
    stoch_rsi_crossover = df['stoch_rsi'].iloc[-1] > 20 and df['stoch_rsi'].iloc[-2] < 20

    # **Final Trend Reversal Confirmation**
    return (rsi_divergence and macd_crossover and supertrend_flip) or bb_squeeze or stoch_rsi_crossover



def execute_momentum_strategy():
    shortlisted_coins = filter_altcoins()
    
    for coin in tqdm(shortlisted_coins, desc="Processing Coins"):
        # print(f"🔍 Checking {coin} on 1D timeframe...")

        df_1D = get_market_data(coin, timeframe='1d', limit=100)
        volume, high, low = df_1D['volume'].sum(), df_1D['high'].max(), df_1D['low'].min()
        volatility = ((high - low) / low) * 100 if low > 0 else 0

        strategy_triggered = None

        if apply_momentum_strategy_1D(df_1D):
            strategy_triggered = "Momentum Strategy 1D"
        elif apply_trend_reversal_strategy(df_1D):
            strategy_triggered = "Trend Reversal Strategy"

        if strategy_triggered:
            # print(f"✅ {coin} passed {strategy_triggered}. Checking 4H timeframe...")
            
            df_4H = get_market_data(coin, timeframe='1h', limit=100)
            
            if apply_momentum_strategy_4H(df_4H) or apply_trend_reversal_strategy(df_4H):
                # 🔹 **FIXED: Passed `coin` as argument!**
                trade_setup = define_trade_levels(df_4H, coin, strategy_triggered, volume, volatility)
                print(trade_setup)
        #     else:
        #         print(f"❌ {coin} did not pass 4H strategy.")
        # else:
        #     print(f"❌ {coin} did not pass 1D strategy.")




execute_momentum_strategy()
input("\nPress Enter to exit...")