import logging
from datetime import datetime
from StratTest.engine import TradingStrategy
import pandas as pd
import ccxt
import config

## Exchange connectivity
exchange = ccxt.binance(
    {
        'apiKey': config.BINANCE_API_KEY,
        'secret': config.BINANCE_SECRET_KEY
    }
)

class TradingBot():

    def __init__(self, strategy, indicator, **params):

        self.strategy = strategy
        self.indicator = indicator
        self.params = params
        
        # logger_name = f'{self.strategy} - {self.indicator} logger - {datetime.now().isoformat()}'
        self.logger = logging.getLogger('Trading Bot')
        # self.bot_actions_handler = logging.FileHandler(f'{config.directory_path}/StratTest/Logging/{logger_name}.log')
        # self.bot_actions_handler.setLevel(logging.DEBUG)
        # self.logger.addHandler(self.bot_actions_handler)
        self.logger.info(f"Bot instanciated at {datetime.now().isoformat()}")


    def _get_crossover(self):

        trading_strategy = TradingStrategy(self.bars_df)
        trading_strategy.add_indicator(self.indicator, window=self.params['short_ema'])
        trading_strategy.add_indicator(self.indicator, window=self.params['long_ema'])

        trading_strategy.add_strategy(
            self.strategy,
            execution_type=None, 
            stop_loss=0,
            comms_bps=0,
            short_ema=f"ema_{self.params['short_ema']}", 
            long_ema=f"ema_{self.params['long_ema']}",
            print_trades=False
        )

        return self.bars_df


    def _check_buy_sell_signals(self, df):

        ## TODO check logic for positioning

        #print("checking for buy and sell signals")
        # print(df.tail(5))
        last_period = df.index[-1]
        before_last_period = df.index[-2]

        if df.loc[before_last_period][f'{self.strategy}_new_position']==1:
            print("changed to uptrend, buy")
            # order = exchange.create_market_buy_order('ETH/USD', 0.05)
            # print(order)
            self.logger.info(f"New BUY order placed at {datetime.now().isoformat()}")
            print('placed a new buy order')

        elif df.loc[before_last_period][f'{self.strategy}_new_position']==-1:
            print("changed to downtrend, sell")

            # order = exchange.create_market_sell_order('ETH/USD', 0.05)
            # print(order)
            self.logger.info(f"New SELL order placed at {datetime.now().isoformat()}")
            print("placed a new sell order")
            
        else:
            self.logger.info(f"No new orders")


    def run_bot(self, pair):

        try:
            #print(f"Fetching new bars for {datetime.now().isoformat()}")
            bars = exchange.fetch_ohlcv(pair, timeframe='1m', limit=100) # most recent candle keeps evolving
            self.bars_df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            self.bars_df['timestamp'] = pd.to_datetime(self.bars_df['timestamp'], unit='ms')
            self.logger.info(f"Succesfully fetched bars at {datetime.now().isoformat()}")
            
            indicator_df = self._get_crossover()
            
            self._check_buy_sell_signals(indicator_df)
            self.logger.info('#####')
        
        except Exception as e:
            self.logger.critical(f"Bot malfunctioned at {datetime.now().isoformat()}", exc_info=True)
