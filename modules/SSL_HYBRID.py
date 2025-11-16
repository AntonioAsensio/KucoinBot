import numpy as np
import pandas as pd

class SSLHybrid:
    def __init__(self, atr_period=14, atr_multiplier=1, baseline_length=60, ssl2_length=5, exit_length=15):
        """
        Initialize the SSLHybrid class with user-defined parameters.

        :param atr_period: Period for ATR calculation.
        :param atr_multiplier: Multiplier for ATR bands.
        :param baseline_length: Length for baseline calculation.
        :param ssl2_length: Length for SSL2 continuation trades.
        :param exit_length: Length for exit trades.
        """
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.baseline_length = baseline_length
        self.ssl2_length = ssl2_length
        self.exit_length = exit_length

    @staticmethod
    def calculate_atr(data, length):
        """
        Calculate the Average True Range (ATR).

        :param data: Pandas DataFrame with 'high', 'low', and 'close' columns.
        :param length: ATR period.
        :return: ATR values as a Pandas Series.
        """
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift(1))
        low_close = np.abs(data['low'] - data['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(window=length).mean()

    @staticmethod
    def calculate_hma(data, length):
        """
        Calculate the Hull Moving Average (HMA).

        :param data: Pandas Series.
        :param length: Length for HMA calculation.
        :return: HMA values as a Pandas Series.
        """
        half_length = length // 2
        sqrt_length = int(np.sqrt(length))
        wma_half = data.rolling(window=half_length).mean()
        wma_full = data.rolling(window=length).mean()
        hull = 2 * wma_half - wma_full
        return hull.rolling(window=sqrt_length).mean()

    def process_signals(self, data):
        """
        Process buy, sell, and hold signals based on the strategy.

        :param data: Pandas DataFrame with 'high', 'low', 'close', and 'open' columns.
        :return: The signal ('buy', 'sell', 'hold') for the last closed candle.
        """
        # Validate data length
        min_length = max(self.atr_period, self.baseline_length, self.ssl2_length, self.exit_length)
        if len(data) < min_length:
            raise ValueError("Not enough data to calculate signals.")

        # Calculate ATR and ATR bands
        atr = self.calculate_atr(data, self.atr_period)
        upper_band = data['close'] + self.atr_multiplier * atr
        lower_band = data['close'] - self.atr_multiplier * atr

        # Calculate SSL1 (Baseline)
        baseline_high = self.calculate_hma(data['high'], self.baseline_length)
        baseline_low = self.calculate_hma(data['low'], self.baseline_length)
        ssl1_signal = np.where(data['close'] > baseline_high, 1,
                               np.where(data['close'] < baseline_low, -1, 0))

        # Calculate SSL2 (Continuation Trades)
        ssl2_high = self.calculate_hma(data['high'], self.ssl2_length)
        ssl2_low = self.calculate_hma(data['low'], self.ssl2_length)
        ssl2_signal = np.where(data['close'] > ssl2_high, 1,
                               np.where(data['close'] < ssl2_low, -1, 0))

        # Calculate Exit signals
        exit_high = self.calculate_hma(data['high'], self.exit_length)
        exit_low = self.calculate_hma(data['low'], self.exit_length)
        exit_signal = np.where(data['close'] > exit_high, 1,
                               np.where(data['close'] < exit_low, -1, 0))

        # Generate final signals based on strategy arrows
        buy_signal = (data['close'] > baseline_high) & (ssl2_signal == 1)
        sell_signal = (data['close'] < baseline_low) & (ssl2_signal == -1)

        # Create a signal series
        signals = pd.Series("hold", index=data.index)
        signals[buy_signal] = "buy"
        signals[sell_signal] = "sell"

        
        # for buy in buy_signal:
        #     if buy == True:
        #         print("buy_signal found")

        # for sell in buy_signal:
        #     if sell == True:
        #         print("sell_signal found")

        # print(f"buy_signal = {buy_signal}")
        # print(f"sell_signal = {sell_signal}")

        # Return the signal for the last closed candle
        return signals.iloc[-1]  # Second-to-last row corresponds to the last closed candle
