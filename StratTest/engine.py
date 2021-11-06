from ta.volatility import BollingerBands, AverageTrueRange
from ta.trend import EMAIndicator

class TradingStrategy():

    def __init__(self, data):
        self.df = data # dataframe with open, high, low, close, volume columns


    def add_indicator(self, indicator, **params):

        if indicator == 'BollingerBands':

            bb_indicator = BollingerBands(self.df['close'], window=params['window'])

            self.df[f'bollinger_hband_{params["window"]}'] = bb_indicator.bollinger_hband()
            self.df[f'bollinger_lband_{params["window"]}'] = bb_indicator.bollinger_lband()
            self.df[f'bollinger_mavg_{params["window"]}'] = bb_indicator.bollinger_mavg()


        elif indicator == 'AverageTrueRange':

            atr_indicator = AverageTrueRange(self.df['high'], self.df['low'], self.df['close'])
            
            self.df['atr'] = atr_indicator.average_true_range()


        elif indicator == 'EMAIndicator':

            ema_indicator = EMAIndicator(self.df['close'], window=params['window'])

            self.df[f'ema_{params["window"]}'] = ema_indicator.ema_indicator()


        print(f'Adding {indicator} with: {params}')



    def add_strategy(self):
        pass