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



    def check_existing_orders(self, pair):
        ''' Only one open order per pair.  Orders are listed chronologically (ie oldest order with index 0)'''

        self.open_orders = self.exchange.fetchOpenOrders(pair)

        # check if current selected pair has more than one active order
        self.pair_open_orders = [order for order in self.open_orders if order['symbol']==pair]

        assert len(self.pair_open_orders) <= 1, f''' Too many orders ({len(self.pair_open_orders)}) on {pair} - logic did not work correctly. Check open orders immediately. exchange.fetchOpenOrders(symbol) '''


    ## TODO ORDER MANAGEMENT METHOD:
    ## if signal and no order in place, place one
    ## if signal, but order already in place for that signalled direction, ignore (maybe based on next bar opening and/or some stop losses)
    ## if signal, but order in place for opposition direction, cancel order and create new order on opposite direction
    ## if no signal, ignore
    ## check against open orders, live orders and past trade. Essential: order ID, side, amount (filled) and state of the order

    def _check_buy_sell_signals(self, df, pair, owned_ccy_size):

        ## TODO check logic for positioning - before last period?
        ## TODO when crossing happens, in current bar you can be kicked out several times Wait for
        ## some form of confirmation?

        last_period = df.index[-1]
        before_last_period = df.index[-2]

        if df.loc[before_last_period][f'{self.strategy}_new_position']==1:

            if not self.in_position:
                # get order book and sizing
                self.get_ob_and_sizing(pair, owned_ccy_size)



                ## check if already in position, avoid double orders on same bar refreshing with new signal every time
                # place limit buy order 10bps above current ask price - provide some buffer for signal confirmation
                self.live_order = self.exchange.createLimitOrder(
                    pair,
                    side='buy',
                    amount=self.trade_size, 
                    price=self.top_ask_px * 1.001
                )
                
                self.logger.info(f"New BUY order placed at {datetime.now().isoformat()}: {self.live_order}. Order book: ask: {self.top_ask_px} - bid: {self.top_bid_px}")
                print(f'{datetime.now().isoformat()} - placed a new buy order: {self.live_order}')
                self.in_position = True

            else:
                self.logger.info(f"No new orders, current position: {self.in_position}")


        elif df.loc[before_last_period][f'{self.strategy}_new_position']==-1:

            if self.in_position:
                # get order book and sizing
                order_closing_size = self.live_order['amount']

                # place limit buy order 10bps below current bid price - provide some buffer for end of signal confirmation
                order = self.exchange.createLimitOrder(
                    pair,
                    side='sell',
                    amount=order_closing_size, 
                    price=self.top_bid_px * 0.999
                )

                self.logger.info(f"New SELL order placed at {datetime.now().isoformat()}")
                print(f'{datetime.now().isoformat()} - placed a new sell order')
                self.in_position = False

            else:
                self.logger.info(f"No new orders, current position: {self.in_position}")
            

        else:
            self.logger.info(f"No new orders, current position: {self.in_position}")


    def run_bot(self, pair, size):

        try:

            bars = self.exchange.fetch_ohlcv(pair, timeframe='1m', limit=100) # most recent candle keeps evolving
            self.bars_df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            self.bars_df['timestamp'] = pd.to_datetime(self.bars_df['timestamp'], unit='ms')
            self.logger.info(f"Succesfully fetched bars at {datetime.now().isoformat()}")
            
            indicator_df = self._get_crossover()
            
            self._check_buy_sell_signals(indicator_df, pair, size)
            self.logger.info('#####')
        
        except Exception as e:
            self.logger.critical(f"Bot malfunctioned at {datetime.now().isoformat()}", exc_info=True)
