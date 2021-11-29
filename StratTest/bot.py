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
        self.sl_price = 0
        self.verify_execution = False
        
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


    def get_ob_and_sizing(self, pair, owned_ccy_size):
        self.order_book = self.exchange.fetchOrderBook(pair)

        self.ob_datetime = self.order_book['datetime']

        self.top_ask_px = self.order_book['asks'][0][0]
        self.top_ask_quantity = self.order_book['asks'][0][1]

        self.top_bid_px = self.order_book['bids'][0][0]
        self.top_bid_quantity = self.order_book['bids'][0][1]

        self.top_mid_px = (self.top_ask_px + self.top_bid_px) / 2
        self.top_ob_spread = (self.top_ask_px - self.top_bid_px) / self.top_mid_px # TODO check for spread when placing order

        # current_mid_price : 1 BTC = my_size : x BTC
        self.trade_size = owned_ccy_size/self.top_mid_px



    def check_open_orders(self, pair):
        ''' Only one open order per pair.  Orders are listed chronologically (ie oldest order with index 0)'''

        self.open_orders = self.exchange.fetchOpenOrders(pair)

        # check if current selected pair has more than one active order
        self.pair_open_orders = [order for order in self.open_orders if order['symbol']==pair]

        assert len(self.pair_open_orders) <= 1, f''' Too many orders ({len(self.pair_open_orders)}) on {pair} - logic did not work correctly. Check open orders immediately. exchange.fetchOpenOrders(symbol) '''


    def order_executed_check(self, pair, id):
        ''' Check if a certain order 'id' has been executed '''

        if self.verify_execution:
            self.executed_orders = self.exchange.fetchMyTrades(pair)
            return len([order['id'] for order in self.executed_orders if order['id']==id]) == 1

            ## TODO check if any buy, sell or stop loss has been executed


    ## TODO ORDER MANAGEMENT METHOD:
    ## check against open orders, live orders and past trade. Essential: order ID, side, amount (filled) and state of the order

    def _check_buy_sell_signals(self, df, pair, owned_ccy_size, sl_pctg, sl_type):

        ## TODO check logic for positioning - before last period?
        ## TODO when crossing happens, in current bar you can be kicked out several times Wait for
        ## some form of confirmation?

        last_period = df.index[-1]
        before_last_period = df.index[-2]

        self.previous_price = self.current_price
        self.current_price = df.loc[before_last_period]['close']


        if not self.in_position:
            # if not in position, check the signal

            if df.loc[before_last_period][f'{self.strategy}_new_position']==1:

                # get order book and sizing
                self.get_ob_and_sizing(pair, owned_ccy_size)


                self.order_price = self.top_ask_px * 1.001
                ## check if already in position, avoid double orders on same bar refreshing with new signal every time
                # place limit buy order 10bps above current ask price - provide some buffer for signal confirmation
                self.buy_order = self.exchange.createLimitOrder(
                    pair,
                    side='buy',
                    amount=self.trade_size, 
                    price=self.order_price 
                )
                
                # set initial stop loss
                self.sl_price = self.buy_order['price'] * (1 - sl_pctg)

                self.logger.info(f"New BUY ORDER PLACED at {datetime.now().isoformat()}: {self.buy_order}. Order book: ask: {self.top_ask_px} - bid: {self.top_bid_px}. Stop loss level: {self.sl_price}")
                print(f'{datetime.now().isoformat()} - placed a new buy order: {self.buy_order}. Stop loss {self.sl_price}')
                self.in_position = True

            else:
                self.logger.info(f"No new orders, current position: {self.in_position}")

        
        elif self.in_position:

            if self.order_executed_check(pair, self.buy_order['id']):
                # 

                # if in position and order has been executed monitor price level and adjust stop loss level accordingly
                # if one of the 2 conditions is hit, close the position with a market order

                if sl_type == 'trailing' and self.current_price > self.previous_price and self.current_price > self.order_price and self.in_position:
                    # with trailing stop loss, if live order, update stop loss price if trade currently in profit
                    self.sl_price = self.buy_order['price'] * (1 - sl_pctg)
                    self.logger.info(f"Stop loss price updated at {datetime.now().isoformat()} to: {self.sl_price}")


                
                if df.loc[before_last_period][f'{self.strategy}_new_position']==-1 or self.current_price < self.sl_price:
                    # when signal reverses, close the position with sell market order

                    # retrieve a fresh order book
                    self.get_ob_and_sizing(pair, owned_ccy_size)

                    self.sell_order = self.exchange.createOrder(
                        pair, 
                        'market', 
                        'sell', 
                        self.buy_order['amount']
                    )

                    self.logger.info(f"SELL ORDER PLACED at {datetime.now().isoformat()}: id: {self.sell_order['id']}. Order book: ask: {self.top_ask_px} - bid: {self.top_bid_px}. Stop loss level: {self.sl_price}")
                    
                    print(f"{datetime.now().isoformat()} - placed a new sell order id: {self.sell_order['id']}.")

                    self.in_position = False
                    self.buy_order = {}
                    self.sl_price = 0

                else:
                    self.logger.info(f"Order still open, keep cruising")
            

            else:
                # if order has not been executed yet, check if keeping it open or cancelling it

                if df.loc[before_last_period][f'{self.strategy}_new_position']>-1 and self.current_price < self.sl_price:
                    self.logger.info(f"Order {self.buy_order['id']}: PLACED BUT NOT yet executed at {self.buy_order['price']}. Trying to execute it")
                
                else:
                    self.cancel_order(self.buy_order['id'])
                    self.logger.info(f"CANCELLING order {self.buy_order['id']}: at price {self.buy_order['price']} due to adverse price movements")
                    
                    self.in_position = False
                    self.buy_order = {}
                    self.sl_price = 0




    def run_bot(self, pair, size, sl_pctg, sl_type='static'):
        '''
        Method that runs the trading bot - to be wrapped inside a scheduler
            pair: str - trading currency pair
            size: float - amount to be traded on a single order
            sl_pctg: float - stop loss as a percentage of order price
            sl_type: str - type of stop loss, static or trailing
        '''

        try:

            bars = self.exchange.fetch_ohlcv(pair, timeframe='1m', limit=100) # most recent candle keeps evolving
            self.bars_df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            self.bars_df['timestamp'] = pd.to_datetime(self.bars_df['timestamp'], unit='ms')
            self.logger.info(f"Succesfully fetched bars at {datetime.now().isoformat()}")
            
            indicator_df = self._get_crossover()
            
            self._check_buy_sell_signals(indicator_df, pair, size, sl_pctg, sl_type)
            self.logger.info('#####')
        
        except Exception as e:
            self.logger.critical(f"Bot malfunctioned at {datetime.now().isoformat()}", exc_info=True)
