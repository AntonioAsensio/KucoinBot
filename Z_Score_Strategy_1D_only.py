import ccxt
import pandas as pd
import numpy as np
import time
from tqdm import tqdm
import requests
import time
import datetime
import os

# User-configurable parameters
MIN_VOLUME = 100000  # Minimum 24h trading volume
MIN_VOLATILITY = 2.5  # Minimum volatility percentage

# Telegram bot configuration
TELEGRAM_BOT_TOKEN = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxx'
TELEGRAM_CHAT_ID = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxx'

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

# New function based on the Statistical Trend Analysis PineScript
def compute_zscore_strategy(df, length=40, source='close'):
    """
    Implementation of the Statistical Trend Analysis (Scatterplot) strategy
    Returns z_score and z_change values for trend analysis
    """
    # Select the source based on input
    if source == 'Returns':
        src = (df['close'] - df['open']) / df['close'] * 100
    elif source in df.columns:
        src = df[source]
    else:
        src = df['close']  # Default fallback
    
    # Calculate Z-score: (value - mean) / standard deviation
    mean = src.rolling(window=length).mean()
    stdev = src.rolling(window=length).std()
    z_score = (src - mean) / stdev
    
    # Limit Z-score to range [-4, 4] as in the original script
    z_score = z_score.clip(-4, 4)
    
    # Calculate Z-change over length/3 periods
    change_period = max(1, length // 3)
    z_change = z_score.diff(change_period)
    z_change = z_change.clip(-4, 4)
    
    return z_score, z_change

def apply_zscore_strategy(df, length=40, data_points=100):
    """
    Apply the Z-score statistical strategy based on quadrant analysis
    Returns a signal (1 for buy, -1 for sell, 0 for neutral)
    """
    # Compute Z-score and Z-change
    z_score, z_change = compute_zscore_strategy(df, length)
    
    # Get only the recent data based on data_points
    recent_z = z_score.iloc[-data_points:].tolist()
    recent_z_change = z_change.iloc[-data_points:].tolist()
    
    # Count points in each quadrant
    quad1 = 0  # Z > 0, Z-change > 0 (Strong Uptrend)
    quad2 = 0  # Z > 0, Z-change < 0 (Weakening Uptrend)
    quad3 = 0  # Z < 0, Z-change < 0 (Strong Downtrend)
    quad4 = 0  # Z < 0, Z-change > 0 (Recovering Downtrend)
    
    for i in range(min(len(recent_z), len(recent_z_change))):
        z = recent_z[i]
        z_ch = recent_z_change[i]
        
        if pd.notna(z) and pd.notna(z_ch):
            if z > 0 and z_ch > 0:
                quad1 += 1
            elif z > 0 and z_ch < 0:
                quad2 += 1
            elif z < 0 and z_ch < 0:
                quad3 += 1
            elif z < 0 and z_ch > 0:
                quad4 += 1
    
    # Determine current quadrant for the most recent data point
    current_z = z_score.iloc[-1]
    current_z_change = z_change.iloc[-1]
    
    current_quadrant = 0
    if pd.notna(current_z) and pd.notna(current_z_change):
        if current_z > 0 and current_z_change > 0:
            current_quadrant = 1
        elif current_z > 0 and current_z_change < 0:
            current_quadrant = 2
        elif current_z < 0 and current_z_change < 0:
            current_quadrant = 3
        elif current_z < 0 and current_z_change > 0:
            current_quadrant = 4
    
    # Count total valid points
    total_points = quad1 + quad2 + quad3 + quad4
    
    # Trading signals based on quadrant distribution and current position
    signal = 0
    
    # Buy signal: If we're in quadrant 4 (recovering) and it's dominant or 
    # in quadrant 1 (strong uptrend) and it's dominant
    if total_points > 0:
        if (current_quadrant == 4 and quad4 > 0.3 * total_points) or \
           (current_quadrant == 1 and quad1 > 0.3 * total_points):
            signal = 1
        
        # Sell signal: If we're in quadrant 2 (weakening) and it's dominant or
        # in quadrant 3 (strong downtrend) and it's dominant
        elif (current_quadrant == 2 and quad2 > 0.3 * total_points) or \
             (current_quadrant == 3 and quad3 > 0.3 * total_points):
            signal = -1
    
    # Add these values to the dataframe for reference
    df['z_score'] = z_score
    df['z_change'] = z_change
    df['zscore_signal'] = signal
    
    # Return the distribution for reporting
    quadrant_info = {
        'quad1': quad1,  # Strong uptrend
        'quad2': quad2,  # Weakening uptrend
        'quad3': quad3,  # Strong downtrend
        'quad4': quad4,  # Recovering downtrend
        'current_quadrant': current_quadrant,
        'signal': signal
    }
    
    return signal, quadrant_info

# Initialize CCXT KuCoin API client
exchange = ccxt.kucoin()

def fetch_with_retry(func, *args, max_retries=5, delay=exchange.rateLimit / 1000, **kwargs):
    """Fetch data with retries on rate limit errors and connection issues."""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except (ccxt.NetworkError, ccxt.ExchangeError, requests.exceptions.ConnectionError) as e:
            print(f"⚠️ API request failed ({type(e).__name__}). Attempt {attempt + 1}/{max_retries}. Retrying in {delay:.2f}s...")
            time.sleep(delay)
        except ccxt.RateLimitExceeded:
            print(f"⏳ Rate limit hit. Waiting {delay:.2f}s before retrying...")
            time.sleep(delay)
    
    print(f"❌ Max retries ({max_retries}) reached. API request failed.")
    return None  # Return None if all attempts fail



def get_market_data(symbol, timeframe, limit):
    """Fetch historical market data for a given symbol and timeframe."""
    candles = fetch_with_retry(exchange.fetch_ohlcv, symbol, timeframe, limit=limit)
    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df.astype(float)
    return df




def get_kucoin_liquidity(symbol, order_size=0.1, max_retries=5):
    """Fetch KuCoin order book data with retry logic for connection issues."""
    kucoin_symbol = symbol.replace("/", "-")
    base_url = "https://api.kucoin.com/api/v1/market/orderbook/level2_20"

    for attempt in range(max_retries):
        try:
            response = requests.get(base_url, params={"symbol": kucoin_symbol}, timeout=5)
            response.raise_for_status()  # Raises error if not 200 response
            json_response = response.json()

            if "data" not in json_response or not json_response["data"]:
                return {"liquidity_classification": "Unknown"}  # If "data" is missing or empty

            data = json_response["data"]
            bids = [[float(price), float(size)] for price, size in data.get("bids", [])]
            asks = [[float(price), float(size)] for price, size in data.get("asks", [])]

            if not bids or not asks:
                return {"liquidity_classification": "Unknown"}

            best_bid, best_bid_size = bids[0]
            best_ask, best_ask_size = asks[0]
            mid_price = (best_bid + best_ask) / 2
            spread = (best_ask - best_bid) / mid_price * 100  # Percentage spread

            depth_bids = sum(size for _, size in bids[:10])
            depth_asks = sum(size for _, size in asks[:10])

            def calculate_slippage(order_size, order_book, is_buy=True):
                remaining = order_size
                cost = 0.0
                for price, size in (order_book if is_buy else reversed(order_book)):
                    if remaining <= size:
                        cost += remaining * price
                        break
                    cost += size * price
                    remaining -= size
                return ((cost / order_size) - (best_ask if is_buy else best_bid)) / (best_ask if is_buy else best_bid) * 100

            buy_slippage = calculate_slippage(order_size, asks, is_buy=True)
            sell_slippage = calculate_slippage(order_size, bids, is_buy=False)

            def classify_liquidity(spread, depth, slippage):
                if spread < 0.05 and depth > 50 * order_size and slippage < 0.1:
                    return "High"
                elif 0.05 <= spread <= 0.2 and 10 * order_size <= depth <= 50 * order_size and 0.1 <= slippage <= 0.5:
                    return "Mid"
                else:
                    return "Low"

            return {
                "spread_percentage": spread,
                "market_depth_bid": depth_bids,
                "market_depth_ask": depth_asks,
                "buy_slippage_%": buy_slippage,
                "sell_slippage_%": sell_slippage,
                "liquidity_classification": classify_liquidity(spread, depth_bids, buy_slippage)
            }

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            print(f"⚠️ KuCoin API request failed (attempt {attempt + 1}/{max_retries}). Retrying in 3s...")
            time.sleep(3)  # Wait before retrying

    print(f"❌ KuCoin API request failed after {max_retries} attempts.")
    return {"liquidity_classification": "Unknown"}  # Return fallback value


def send_telegram_message(message):
    """Send a message to the configured Telegram chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"✅ Telegram message sent successfully.")
        else:
            print(f"❌ Telegram message failed: {response.json()}")
    except Exception as e:
        print(f"❌ Error sending Telegram message: {e}")

def define_trade_levels(df, symbol, strategy_name, volume, volatility, timeframe, quadrant_info=None):
    """Define trade levels, adjust price formatting, and save results to a dated CSV file."""
    latest_close = df['close'].iloc[-1]
    atr = compute_atr(df).iloc[-1]

    entry = latest_close
    stop_loss = latest_close - (1.5 * atr)
    target1 = latest_close + (1.5 * atr)
    target2 = latest_close + (2.5 * atr)
    final_target = latest_close + (4 * atr)

    t1_perc = ((target1 - entry) / entry) * 100
    t2_perc = ((target2 - entry) / entry) * 100
    final_perc = ((final_target - entry) / entry) * 100

    # Auto-detect decimal precision
    def auto_format(value):
        return f"{value:.10f}" if value < 0.0001 else f"{value:.4f}"

    liquidity_info = get_kucoin_liquidity(symbol, order_size=1)
    liquidity = liquidity_info.get("liquidity_classification", "Unknown")
    spread = liquidity_info.get("spread_percentage", "N/A")
    depth = liquidity_info.get("market_depth_bid", "N/A")

    # Generate timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_date = datetime.datetime.now().strftime("%Y-%m-%d")  # Format as YYYY-MM-DD

    # Create CSV filename with run date
    csv_file = f"trades_log_{run_date}.csv"

    # Convert symbol format to KuCoin-compatible (e.g., "BTC/USDT" → "BTC-USDT")
    kucoin_symbol = symbol.replace("/", "-")
    kucoin_trade_url = f"https://www.kucoin.com/trade/{kucoin_symbol}"

    # Create DataFrame for logging
    trade_data = pd.DataFrame([{
        "Timestamp": timestamp,
        "Symbol": symbol,
        "Timeframe": timeframe,  # NEW: Added timeframe
        "Strategy": strategy_name,
        "Volume": volume,
        "Volatility (%)": round(volatility, 2),
        "Liquidity": liquidity,
        "Spread (%)": spread,
        "Depth": depth,
        "Entry Price": auto_format(entry),
        "Stop Loss": auto_format(stop_loss),
        "Target 1": auto_format(target1),
        "Target 2": auto_format(target2),
        "Final Target": auto_format(final_target),
        "T1 Gain (%)": round(t1_perc, 2),
        "T2 Gain (%)": round(t2_perc, 2),
        "Final Gain (%)": round(final_perc, 2)
    }])

    # Save to CSV (Append Mode)
    try:
        trade_data.to_csv(csv_file, mode="a", index=False, header=not os.path.exists(csv_file))
        print(f"✅ Trade setup for {symbol} ({timeframe}) saved to {csv_file}")
    except Exception as e:
        print(f"❌ Error saving to CSV: {e}")

    # Format the trade message for Telegram with hyperlink and timeframe
    trade_setup = f"""
    📅 **Analysis Run Date: {run_date}**
    🔹 [**{symbol} ({timeframe})**]({kucoin_trade_url}) 🔹

    📈 **Strategy Triggered:** {strategy_name}
    📊 **24H Volume:** {volume:,.0f}
    🌊 **Volatility:** {volatility:.2f}%
    💧 **Liquidity:** {liquidity} (Spread: {spread}%, Depth: {depth})
    🕒 **Timeframe:** {timeframe}
    """

    if quadrant_info:
        trade_setup += f"""
    📊 **Z-Score Quadrant Analysis:**
    - Q1 (Strong Uptrend): {quadrant_info['quad1']} points
    - Q2 (Weakening Uptrend): {quadrant_info['quad2']} points
    - Q3 (Strong Downtrend): {quadrant_info['quad3']} points
    - Q4 (Recovering Downtrend): {quadrant_info['quad4']} points
    - Current Position: Quadrant {quadrant_info['current_quadrant']}
    """

    trade_setup += f"""
    🔹 **Entry Price:** {entry:.4f}
    🔹 **Stop Loss:** {stop_loss:.4f} (🔻 {(entry - stop_loss) / entry * 100:.2f}%)

    🎯 **Targets:**
    - Target 1: {target1:.4f} (+{t1_perc:.2f}%)
    - Target 2: {target2:.4f} (+{t2_perc:.2f}%)
    - Final Target: {final_target:.4f} (+{final_perc:.2f}%)
    """

    # Send trade setup to Telegram
    send_telegram_message(trade_setup)

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
        liquidity_info = get_kucoin_liquidity(coin, order_size=1)
        liquidity = liquidity_info.get("liquidity_classification", "Unknown")

        # Skip low-liquidity coins
        if liquidity == "Low":
            print(f"⚠️ Skipping {coin} due to low liquidity.")
            continue

        df_1D = get_market_data(coin, timeframe='1d', limit=100)
        volume, high, low = df_1D['volume'].sum(), df_1D['high'].max(), df_1D['low'].min()
        volatility = ((high - low) / low) * 100 if low > 0 else 0

        strategy_triggered = None
        quadrant_info = None

        # Apply the new Z-score strategy
        zscore_signal, quadrant_info = apply_zscore_strategy(df_1D, length=40, data_points=100)
        
        if zscore_signal == 1:
            strategy_triggered = "Z-Score Statistical Strategy"
        elif apply_momentum_strategy_1D(df_1D):
            strategy_triggered = "Momentum Strategy 1D"
        elif apply_trend_reversal_strategy(df_1D):
            strategy_triggered = "Trend Reversal Strategy"

        if strategy_triggered:
            df_4H = get_market_data(coin, timeframe='1h', limit=100)
            
            if strategy_triggered == "Z-Score Statistical Strategy":
                zscore_4h_signal, _ = apply_zscore_strategy(df_4H, length=20, data_points=50)
                confirmation = zscore_4h_signal == 1
            else:
                confirmation = apply_momentum_strategy_4H(df_4H) or apply_trend_reversal_strategy(df_4H)
                
            if confirmation:
                trade_setup = define_trade_levels(df_4H, coin, strategy_triggered, volume, volatility, quadrant_info)
                print(trade_setup)


def execute_zscore_strategy():
    """Run only the Z-Score Statistical Strategy for testing, excluding low-liquidity coins."""
    shortlisted_coins = filter_altcoins()

    for coin in tqdm(shortlisted_coins, desc="Processing Z-Score Strategy"):
        liquidity_info = get_kucoin_liquidity(coin, order_size=1)
        liquidity = liquidity_info.get("liquidity_classification", "Unknown")

        # Skip low-liquidity coins
        if liquidity == "Low":
            print(f"⚠️ Skipping {coin} due to low liquidity.")
            continue

        df_1D = get_market_data(coin, timeframe='1d', limit=100)
        volume, high, low = df_1D['volume'].sum(), df_1D['high'].max(), df_1D['low'].min()
        volatility = ((high - low) / low) * 100 if low > 0 else 0

        # Apply Z-score strategy
        zscore_signal, quadrant_info = apply_zscore_strategy(df_1D, length=40, data_points=100)
        
        if zscore_signal == 1:
            trade_setup = define_trade_levels(df_1D, coin, "Z-Score Statistical Strategy", volume, volatility,'1d', quadrant_info)
            print(trade_setup)



# Choose which strategy to execute
# execute_momentum_strategy()  # Run all strategies including Z-Score
execute_zscore_strategy()  # Run only Z-Score strategy for testing

input("\nPress Enter to exit...")