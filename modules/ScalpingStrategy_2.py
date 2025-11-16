import pandas as pd
import numpy as np
import ta  # Technical Analysis library


class ScalpingStrategy:
    def __init__(self,):
       
        
        # Strategy Parameters
        self.EMA_period = 30
        self.ATR_Period = 14
        self.ATR_Multi = 1
        self.Baseline_Multi = 0.2
        self.BB_PERIODS = 10
        self.DEVIATIONS = 1
        self.MACD_FAST_LENGTH = 12
        self.MACD_SLOW_LENGTH = 26
        self.MACD_SIGNAL_LENGTH = 9
        self.ZERO_LINE = 0
        self.STOPLOSS_PERCENTAGE = 0.02
        self.VOLUME_MA_LENGTH = 9

    def calculate_indicators(self, df):
        """
        Calculate all required indicators for the strategy.
        """
        if df.empty or not {'close', 'high', 'low', 'volume'}.issubset(df.columns):
            raise ValueError("DataFrame must contain 'close', 'high', 'low', and 'volume' columns.")
        
        # 1. VOLUME INDICATOR
        df['VOLUME_MA'] = df['volume'].rolling(window=self.VOLUME_MA_LENGTH).mean()
        
        # 2. SSL Hybrid Indicator
        df['EMA_Close'] = ta.trend.ema_indicator(df['close'], window=self.EMA_period)
        df['Kelt_MA'] = ta.trend.ema_indicator(df['close'], window=self.ATR_Period)
        df['Range'] = df['high'] - df['low']
        df['Range_MA'] = df['Range'].rolling(window=self.EMA_period).mean()
        df['upperk'] = df['Kelt_MA'] + (df['Range_MA'] * self.Baseline_Multi)
        df['lowerk'] = df['Kelt_MA'] - (df['Range_MA'] * self.Baseline_Multi)
        
        def calculate_ssl(row):
            if row['close'] > row['upperk']:
                return 1  # Green
            if row['close'] < row['lowerk']:
                return -1  # Red
            return 0  # Grey
        
        df['SSL'] = df.apply(calculate_ssl, axis=1)
        
        # 3. MACD BB Indicator
        # df['MACD'] = ta.trend.macd(df['close'], window_slow=self.MACD_SLOW_LENGTH, window_fast=self.MACD_FAST_LENGTH)
        # df['MACD_signal'] = ta.trend.macd_signal(df['close'], window_slow=self.MACD_SLOW_LENGTH, window_fast=self.MACD_FAST_LENGTH, window_sign=self.MACD_SIGNAL_LENGTH)
        # df['MACD_hist'] = df['MACD'] - df['MACD_signal']
        
        # df['MACD_Std'] = df['MACD'].rolling(window=self.BB_PERIODS).std()
        # df['MACD_MA'] = df['MACD'].rolling(window=self.DEVIATIONS).mean()
        # df['MACD_Upper'] = df['MACD_MA'] + (df['MACD_Std'] * self.DEVIATIONS)
        # df['MACD_Lower'] = df['MACD_MA'] - (df['MACD_Std'] * self.DEVIATIONS)

        df['MACD'] = df['close'].ewm(span=self.MACD_FAST_LENGTH).mean() - df['close'].ewm(span=self.MACD_SLOW_LENGTH).mean()
        df['MACD_SIGNAL'] = df['MACD'].ewm(span=self.MACD_SIGNAL_LENGTH).mean()
        df['MACD_HIST'] = df['MACD'] - df['MACD_SIGNAL']
        df['Std'] = df['MACD'].rolling(window=self.BB_PERIODS).std()
        df['MACD_Upper'] = df['MACD'].rolling(window=self.BB_PERIODS).mean() + (df['Std'] * self.DEVIATIONS)
        df['MACD_Lower'] = df['MACD'].rolling(window=self.BB_PERIODS).mean() - (df['Std'] * self.DEVIATIONS)
        
        df['MC'] = np.where(df['MACD'] >= df['MACD_Upper'], 1, 0)  # lime (1) if MACD > Upper Band
        
        return df
    
    def evaluate_conditions(self, df):
        """
        Evaluate Buy, Sell, or Hold conditions.
        """
        last_row = df.iloc[-1]
        # last_3_ssl = df['SSL'].iloc[-3:].tolist()
        last_3_ssl = df['SSL'].iloc[-(3+1):-1].tolist()
        
        # BUY CONDITIONS
        buy_condition_1 = any(x == 0 for x in last_3_ssl) and last_row['SSL'] != 0
        buy_condition_2 = last_row['SSL'] == 1
        buy_condition_3 = last_row['VOLUME_MA'] < last_row['volume']
        buy_condition_4 = last_row['MC'] == 1
        buy_condition_5 = last_row['MACD'] > self.ZERO_LINE

        # DEBUG
        if buy_condition_1:
            print("buy_condition_1 is OK")
        else:
            print("buy_condition_1 is BAD")

        if buy_condition_2:
            print("buy_condition_2 is OK")
        else:
            print("buy_condition_2 is BAD")

        if buy_condition_3:
            print("buy_condition_3 is OK")
        else:
            print("buy_condition_3 is BAD")
            
        if buy_condition_4:
            print("buy_condition_4 is OK")
        else:
            print("buy_condition_4 is BAD")

        if buy_condition_5:
            print("buy_condition_5 is OK")
        else:
            print("buy_condition_5 is BAD")
        
        print("--------------------------------------------")
        # END DEBUG
        
        if all([buy_condition_1, buy_condition_2, buy_condition_3, buy_condition_4, buy_condition_5]):
            return 'buy'
        
        # SELL CONDITIONS
        sell_condition_1 = any(x == 0 for x in last_3_ssl) and last_row['SSL'] != 0
        sell_condition_2 = last_row['SSL'] == -1
        sell_condition_3 = last_row['VOLUME_MA'] < last_row['volume']
        sell_condition_4 = last_row['MC'] == 0
        sell_condition_5 = last_row['MACD'] < self.ZERO_LINE

        #DEBUG
        if sell_condition_1:
            print("sell_condition_1 is OK")
        else:
            print("sell_condition_1 is BAD")

        if sell_condition_2:
            print("sell_condition_2 is OK")
        else:
            print("sell_condition_2 is BAD")

        if sell_condition_3:
            print("sell_condition_3 is OK")
        else:
            print("sell_condition_3 is BAD")
            
        if sell_condition_4:
            print("sell_condition_4 is OK")
        else:
            print("sell_condition_4 is BAD")

        if sell_condition_5:
            print("sell_condition_5 is OK")
        else:
            print("sell_condition_5 is BAD")
        # END DEBUG
        
        if all([sell_condition_1, sell_condition_2, sell_condition_3, sell_condition_4, sell_condition_5]):
            return 'sell'
        
        return 'hold'
    
    def run(self, df):
        """
        Run the strategy on a given DataFrame.
        """
        if df.empty:
            print("No data provided.")
            return "hold"
        
        df = self.calculate_indicators(df)
        action = self.evaluate_conditions(df)
         # DEBUGGING
        last_row = df.iloc[-1]
        # last_3_ssl = df['SSL'].iloc[-3:].tolist()
        last_3_ssl = df['SSL'].iloc[-(3+1):-1].tolist()
        

        print("=========================================================================")

  
        # print(f"last_3_ssl = {last_3_ssl}")
        # print(f"last_row['SSL'] = {last_row['SSL']}")

        # if (last_row['volume'] < last_row['VOLUME_MA']):
        #     print("VOL MA below VOL: GOOD")
        # else:
        #     print("VOL MA above VOL: BAD")
        # print(f"last_row['MC']  = {last_row['MC'] }")
        # print(f"last_row['MACD']  = {last_row['MACD'] }")
        # print("=========================================================================")
        print(f"Action: {action.upper()}")
        # print("=========================================================================")

        return action
