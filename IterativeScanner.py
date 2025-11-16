import ccxt
import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from ta.trend import SMAIndicator, MACD, EMAIndicator
from datetime import datetime
from tqdm import tqdm
import time
import random
from modules.SSL_HYBRID import SSLHybrid

np.set_printoptions(suppress=True)  # Avoid scientific notation in numbers

# Initialize the CCXT KuCoin exchange
exchange = ccxt.kucoin({
    'rateLimit': True,
    'enableRateLimit': True
})


# --- TXT to HTML Conversion ---
def txt_to_html_with_gradient(input_file: str, output_html: str, gradient_column: str, support_multiplier: float, resistance_multiplier: float):
    """
    Reads a txt file with comma-separated headers and values, creates a pandas DataFrame,
    applies gradient coloring to a specified column, and exports it to an HTML file.
    """
    df = pd.read_csv(input_file)
    df['EntryPoint'] = df['support'] * support_multiplier
    df['ExitPoint'] = df['resistance'] * resistance_multiplier
    
    if gradient_column not in df.columns:
        raise ValueError(f"Column '{gradient_column}' not found in the DataFrame.")
    
    styled_df = df.style.background_gradient(
        subset=[gradient_column], cmap='coolwarm', vmin=0, vmax=40
    )
    
    styled_df.to_html(output_html)
    print(f"DataFrame exported to {output_html} with gradient coloring on '{gradient_column}'.")


# --- Fetch Top N Coins by Volume ---
def fetch_top_N_coins_by_volume(top_N_coins):
    """
    Fetch the top N coins by 24-hour trading volume from KuCoin.
    """
    tickers = exchange.fetch_tickers()
    volume_data = []
    
    for symbol, data in tickers.items():
        if symbol.endswith('/USDT'):
            volume_data.append({'symbol': symbol, 'volume': data['quoteVolume']})
    
    sorted_coins = sorted(volume_data, key=lambda x: x['volume'], reverse=True)[:top_N_coins]
    return [coin['symbol'] for coin in sorted_coins]


# --- Fetch Hourly Data ---
def fetch_hourly_data(symbol, time_frame, limit=96):
    """Fetch hourly candles for a given symbol."""
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=time_frame, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df


# --- Support and Resistance ---
def calculate_support_resistance(order_book):
    bids = np.array(order_book['bids'])
    asks = np.array(order_book['asks'])
    cumulative_bids = np.cumsum(bids[:, 1])
    cumulative_asks = np.cumsum(asks[:, 1])
    support_price = bids[np.argmax(cumulative_bids), 0]
    resistance_price = asks[np.argmax(cumulative_asks), 0]
    return support_price, resistance_price


def analyze_coin(coin):
    """
    Analyze a coin for support, resistance, and price increase potential.
    """
    try:
        order_book = exchange.fetch_order_book(coin)
        current_price = exchange.fetch_ticker(coin)['last']
        support, resistance = calculate_support_resistance(order_book)
        potential_increase = ((resistance - support) / support) * 100

        return {
            'coin': coin,
            'current_price': current_price,
            'support': support,
            'resistance': resistance,
            'potential_increase_%': potential_increase
        }
    except Exception as e:
        return {'coin': coin, 'error': str(e)}

    # 'timeframes': {
    #             '1m': '1min',
    #             '3m': '3min',
    #             '5m': '5min',
    #             '15m': '15min',
    #             '30m': '30min', 
    #             '1h': '1hour',
    #             '2h': '2hour',
    #             '4h': '4hour',
    #             '6h': '6hour',
    #             '8h': '8hour',
    #             '12h': '12hour',
    #             '1d': '1day',
    #             '1w': '1week',
    #             '1M': '1month',
    #         },

# --- Main Function ---
          
            
def main():
    
    _4h_list = []
    _1h_list = []
    _15m_list = []

    predictions_file = open(r"D:\_KRYPTO_\KUCOIN_BOT\DailyScan.txt","a")
    predictions_output_table = r"D:\_KRYPTO_\KUCOIN_BOT\DailyScan.html"
    predictions_file_path = r"D:\_KRYPTO_\KUCOIN_BOT\DailyScan.txt"

    time_frame_4h = '4h'
    time_frame_1h = '1h'
    time_frame_15m = '15m'

    time_frame_list = [time_frame_4h, time_frame_1h, time_frame_15m]

    top_N_symbols = 200
    support_multiplier = 1.06
    resistance_multiplier = 0.96

    top_N_coins = fetch_top_N_coins_by_volume(top_N_symbols)

    strategy = SSLHybrid(atr_period=14, atr_multiplier=1, baseline_length=60)
    strategy = SSLHybrid(
        atr_period=14,
        atr_multiplier=1,
        baseline_length=60,
        ssl2_length=5,
        exit_length=15
        )
                    
    
    buy_signals_list = []

    for time_frame in  tqdm(time_frame_list):
        for symbol in tqdm(top_N_coins):
            try:   
                df = fetch_hourly_data(symbol, time_frame)
                action = strategy.process_signals(df)
                print(symbol)
                print(action)
                if action == 'buy':
                    if time_frame == '4h':
                        _4h_list.append(symbol)
                    if time_frame == '1h':
                        _1h_list.append(symbol)
                    if time_frame == '15m':
                        _15m_list.append(symbol)
                    print("Action is BUY")
                    buy_signals_list.append(symbol)
                    symbol_short = symbol.split('/')[0]
                    print(symbol)
                    r = analyze_coin(symbol)
                    url =f"https://www.tradingview.com/chart/fFzNcKEZ/?symbol=KUCOIN%3A{symbol_short}USDT"
                    prediction = f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{r['coin']},{time_frame},{r['current_price']},{r['support']},{r['resistance']},{r['potential_increase_%']:.2f},{url}"
                    with open(predictions_file_path, "a") as predictions_file:
                        predictions_file.write(prediction)
                        predictions_file.close()
 
            except Exception as e:
                print(f"Error processing {symbol}: {e}")


    
    common_symbols_4h_1h= [item for item in _4h_list if item in _1h_list]
    if len(common_symbols_4h_1h) > 0:
        print("-----------------------------------------------------------------------------------------------")
        print(f"coins with buy trigger at both 4h and 1h time frames: {common_symbols_4h_1h}")
        print("-----------------------------------------------------------------------------------------------")

        common_symbols_4h_1h_15m =[item for item in common_symbols_4h_1h if item in _15m_list]
        if len(common_symbols_4h_1h_15m) >0:
            print(f"!!!!!!!!!!!!!!!!coins with buy trigger at all, 4h, 1h, 15m time frames: {common_symbols_4h_1h_15m}")
        else:
            print("NO coins with simultaneous buy trigger at 4h & 1h & 15m")
    else:
        print("NO coins with simultaneous buy trigger at 4h & 1h")

    common_symbols_4h_15m =[item for item in _4h_list if item in _15m_list]
    if len(common_symbols_4h_15m) > 0:
        print(f"common_symbols_4h_15m: {common_symbols_4h_15m}")


    txt_to_html_with_gradient(predictions_file_path, predictions_output_table, "potential_increase_%", support_multiplier, resistance_multiplier)

if __name__ == "__main__":
    main()

