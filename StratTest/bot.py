import logging
from datetime import datetime
from StratTest.engine import TradingStrategy
import pandas as pd
import ccxt
import config



class TradingBot():

    def __init__(self, strategy, indicator, sandbox=True, **params):

        ## Exchange connectivity
        self.exchange = ccxt.bitstamp(
            {
                'apiKey': config.BITSTAMP_API_KEY,
                'secret': config.BITSTAMP_API_SECRET
            }
        )
        self.exchange.set_sandbox_mode(sandbox)

        self.strategy = strategy
        self.indicator = indicator
        self.params = params
        self.in_position = False
        
        self.logger = logging.getLogger('Trading Bot')
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

        ## TODO check logic for positioning - before last period?
        ## TODO when crossing happens, in current bar you can be kicked out several times Wait for
        ## some form of confirmation?

        last_period = df.index[-1]
        before_last_period = df.index[-2]

        if df.loc[before_last_period][f'{self.strategy}_new_position']==1:

            if not self.in_position:
                ## check if already in position, avoid double orders on same bar refreshing with new signal every time
                ## order = exchange.create_market_buy_order('ETH/USD', 0.05)
                ## print(order)
                
                self.logger.info(f"New BUY order placed at {datetime.now().isoformat()}")
                print(f'{datetime.now().isoformat()} - placed a new buy order')
                self.in_position = True

            else:
                self.logger.info(f"No new orders, current position: {self.in_position}")


        elif df.loc[before_last_period][f'{self.strategy}_new_position']==-1:

            if self.in_position:

                # order = exchange.create_market_sell_order('ETH/USD', 0.05)
                # print(order)
                self.logger.info(f"New SELL order placed at {datetime.now().isoformat()}")
                print(f'{datetime.now().isoformat()} - placed a new sell order')
                self.in_position = False

            else:
                self.logger.info(f"No new orders, current position: {self.in_position}")
            

        else:
            self.logger.info(f"No new orders, current position: {self.in_position}")


    def run_bot(self, pair):

        try:

            bars = self.exchange.fetch_ohlcv(pair, timeframe='1m', limit=100) # most recent candle keeps evolving
            self.bars_df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            self.bars_df['timestamp'] = pd.to_datetime(self.bars_df['timestamp'], unit='ms')
            self.logger.info(f"Succesfully fetched bars at {datetime.now().isoformat()}")
            
            indicator_df = self._get_crossover()
            
            self._check_buy_sell_signals(indicator_df)
            self.logger.info('#####')
        
        except Exception as e:
            self.logger.critical(f"Bot malfunctioned at {datetime.now().isoformat()}", exc_info=True)
