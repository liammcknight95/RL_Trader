import logging
from datetime import datetime
from StratTest.engine import TradingStrategy
from StratTest import db_update_tables as db_update
import pandas as pd
import ccxt
import config
import uuid
import json


# TODO check if data from api need to be assigned a time frequency - to align with resample data in 
# engine and make sure there's no gaps
# TODO using order ID now, check if I can make use of transaction id

class TradingBot():

    def __init__(self, pair, strategy, frequency, sl_type, sl_pctg, owned_ccy_size, sandbox=True, **params):
        ''' 
            pair: str - currency pair the bot is trading
            strategy: str - 
            frequency: str - ie '30m'
            sl_type: str - type of stop loss, static or trailing
            sl_pctg: float - stop loss as a percentage of order price
            owned_ccy_size: float - amount of owned currency to be traded on a single order
        '''
        ## Exchange connectivity
        self.exchange = ccxt.bitstamp(
            {
                'apiKey': config.BITSTAMP_API_KEY,
                'secret': config.BITSTAMP_API_SECRET
            }
        )
        self.exchange.set_sandbox_mode(sandbox)

        ## Database connectivity
        self.db_config_parameters = config.pg_db_configuration(location='local')

        self.pair = pair
        self.strategy = strategy
        # self.indicator = indicator
        self.frequency = frequency
        self.sl_type = sl_type
        self.sl_pctg = sl_pctg
        self.params = params
        self.in_position = False
        self.signal_time = pd.Timestamp(datetime.now()) # initiate signal time, updated throughout bot lif
        self.owned_ccy_size = owned_ccy_size
        
        self.logger = logging.getLogger('Trading Bot')
        self.logger.info(f"Bot instanciated at {datetime.now().isoformat()}")
        self._db_new_bot() # add new bot to database


    def _db_new_bot(self):
        ''' Method that gathers all the information needed to create a new bot in the database '''

        self.bot_id = 'bot-' + str(uuid.uuid4())
        bot_owned_ccy_end_position = None
        bot_start_date = self.signal_time
        bot_end_date = None
        bot_exchange = 'Bitstamp' # static for now
        json_parameters = json.dumps(self.params)
        
        fields = [
            self.bot_id,
            self.pair,
            self.owned_ccy_size,
            bot_owned_ccy_end_position,
            bot_start_date,
            bot_end_date,
            self.strategy,
            json_parameters,
            self.sl_pctg,
            self.sl_type,
            self.frequency,
            bot_exchange
        ]
        # create new database record
        db_update.insert_bots_table(fields, self.db_config_parameters)


    def _db_update_bot(self):
        
        fields = [
            self.bot_id,
            self.end_of_bot_time,
            # a position
            # TODO take time and final position when process is terminated
        ]
        db_update.insert_bots_table(fields, self.db_config_parameters)

    def _db_new_order(self, order):
        order_id = 'order-' + str(uuid.uuid4())
        order_timestamp_placed = order['datetime']
        order_price_placed = order['price']
        order_quantity_placed = order['amount']
        order_direction = order['side']
        order_exchange_type = order['type']
        if order['filled'] == 0:
            order_status = 'dormant'
        elif order['filled'] < order['amount']:
            order_status = 'partialled'
        else:
            order_status = 'filled'
        order_ob_bid_price = self.top_bid_px
        order_ob_ask_price = self.top_ask_px
        order_ob_bid_size = self.top_bid_quantity
        order_ob_ask_size = self.top_ask_quantity
        order_exchange_trade_id = order['id']
        order_trades = order['trades']
        order_quantity_filled = order['amount'] - order['remaining']
        order_price_filled = None
        order_fee = None

        fields = [
            order_id,
            self.bot_id,
            order_timestamp_placed,
            order_price_placed,
            order_quantity_placed,
            order_direction,
            order_exchange_type,
            order_status,
            order_ob_bid_price,
            order_ob_ask_price,
            order_ob_bid_size,
            order_ob_ask_size,
            order_exchange_trade_id,
            order_trades,
            order_quantity_filled,
            order_price_filled,
            order_fee
        ]
        print(fields)
        # create new order database record
        db_update.insert_orders_table(fields, self.db_config_parameters)


    def _db_update_order(self, order_id, order_checked):
        order_status = ...
        order_trades = order_checked
        order_quantity_filled = order_checked['amount']
        order_price_filled = order_checked['price']

        fields = [
            order_status,
            order_trades,
            order_quantity_filled,
            order_price_filled,
            self.bot_id,
            order_id
        ]

        db_update.update_single_order_table(fields, self.config_parameters)


    def _db_new_order_book(self, bar):
        ''' bar: pd.Series containing strategy latest pulled data and indicator '''

        ob_record_timestamp = datetime.now().isoformat()
        ob_bar_time = bar['timestamp'] # TODO check if this is correct, time need not to be index
        ob_open = bar['open']
        ob_high = bar['high']
        ob_low = bar['low']
        ob_close = bar['close']
        ob_action = bar[f'{self.strategy}_trades']
        ob_in_position = self.in_position
        ob_stop_loss_price = self.sl_price
        ob_strategy_signal = bar[f'{self.strategy}_signal']  

        fields = [
            self.bot_id,
            ob_record_timestamp,
            ob_bar_time, 
            ob_open,
            ob_high,
            ob_low,
            ob_close,
            ob_action,
            ob_in_position,
            ob_stop_loss_price,
            ob_strategy_signal
        ]

        # create new orderbook record
        db_update.insert_order_book_bars_table(fields, self.db_config_parameters)


    def _db_new_health_status(self, health_status, err):

        health_status_timestamp = datetime.now().isoformat()

        fields = [
            self.bot_id,
            health_status_timestamp,
            health_status,
            err
        ]

        # create new api health status database record
        db_update.insert_health_status_table(fields, self.db_config_parameters)


    def _get_crossover(self, plot=False):

        trading_strategy = TradingStrategy(self.bars_df, self.frequency, mode='live')
        print(self.params)
        trading_strategy.add_strategy(
            self.strategy,
            execution_type='next_bar_open',#None, 
            stop_loss_bps=0,
            comms_bps=0,
            print_trades=False,
            indicators_params=self.params

        )

        if plot:
            fig = trading_strategy.trading_chart(
               plot_strategy=True, 
               plot_volatility=False
            )
            fig.show()

        return self.bars_df


    def get_ob_and_sizing(self):
        self.order_book = self.exchange.fetchOrderBook(self.pair)

        self.ob_datetime = self.order_book['datetime']

        self.top_ask_px = self.order_book['asks'][0][0]
        self.top_ask_quantity = self.order_book['asks'][0][1]

        self.top_bid_px = self.order_book['bids'][0][0]
        self.top_bid_quantity = self.order_book['bids'][0][1]

        self.top_mid_px = (self.top_ask_px + self.top_bid_px) / 2
        self.top_ob_spread = (self.top_ask_px - self.top_bid_px) / self.top_mid_px # TODO check for spread when placing order

        # current_mid_price : 1 BTC = my_size : x BTC
        self.trade_size = self.owned_ccy_size/self.top_mid_px


    def check_open_orders(self):
        ''' Only one open order per pair.  Orders are listed chronologically (ie oldest order with index 0)'''

        self.open_orders = self.exchange.fetchOpenOrders(self.pair)

        # check if current selected pair has more than one active order
        self.pair_open_orders = [order for order in self.open_orders if order['symbol']==self.pair]

        assert len(self.pair_open_orders) <= 1, f''' Too many orders ({len(self.pair_open_orders)}) on {self.pair} - logic did not work correctly. Check open orders immediately. exchange.fetchOpenOrders(symbol) '''


    def order_executed_check(self, order_id):
        ''' Check if a certain order 'id' has been executed '''
        # TODO check if this order check is robust of if order executed in multiple tranches might return multiple entries for that certain order id
        self.executed_orders = self.exchange.fetchMyTrades(self.pair)
        current_order_records = [order['order'] for order in self.executed_orders if order['order']==order_id]
        order_checked = len(current_order_records) == 1
        
        if order_checked:
            self._db_update_order(order_id, current_order_records[0]) # only value with records in the database
            self.logger.info(f"-- Order status updated at {datetime.now().isoformat()}")
        else:
            self.logger.warning(f"-- Order not updated, order_checked not 1 {current_order_records} - at {datetime.now().isoformat()}")

        return order_checked

    ## TODO ORDER MANAGEMENT METHOD:
    ## check against open orders, live orders and past trade. Essential: order ID, side, amount (filled) and state of the order

    def _check_buy_sell_signals(self, df):

        current_period = df.index[-1] # current bar - used for stop losses and reversals
        previous_period = df.index[-2] # previous bar - used to check signals

        self.current_price = df.loc[current_period]['close']
        self.previous_price = df.loc[previous_period]['close']

        if not self.in_position:
            # if not in position, check the signal

            if df.loc[previous_period][f'{self.strategy}_new_position']==1 and df.loc[previous_period]['timestamp']>self.signal_time:
                # if signal is 1 and has been generated on a new bar - new timestamp

                # get order book and sizing
                self.get_ob_and_sizing(self.owned_ccy_size)

                self.order_price = self.top_ask_px * 1.001
                ## check if already in position, avoid double orders on same bar refreshing with new signal every time
                # place limit buy order 10bps above current ask price - provide some buffer for signal confirmation
                self.buy_order = self.exchange.createLimitOrder(
                    self.pair,
                    side='buy',
                    amount=self.trade_size, 
                    price=self.order_price 
                )
                
                # set initial stop loss
                self.sl_price = self.buy_order['price'] * (1 - self.sl_pctg)

                self.logger.info(f"----- New BUY ORDER PLACED at {datetime.now().isoformat()}: {self.buy_order}. Order book: ask: {self.top_ask_px} - bid: {self.top_bid_px}. Stop loss level: {self.sl_price} -----")
                print(f'{datetime.now().isoformat()} - placed a new buy order: {self.buy_order}. Stop loss {self.sl_price}')
                self.in_position = True
                self.signal_time = df.loc[previous_period]['timestamp']

                self._db_new_order(self.buy_order) # adding new order to database
            else:
                self.logger.info(f"No new orders. Current position: {self.in_position}")

        
        elif self.in_position:

            if self.order_executed_check(self.buy_order['id']):
                # 

                # if in position and order has been executed monitor price level and adjust stop loss level accordingly
                # if one of the 2 conditions is hit, close the position with a market order

                if self.sl_type == 'trailing' and self.current_price > self.previous_price and self.current_price > self.order_price:
                    # with trailing stop loss, if live order, update stop loss price if trade currently in profit
                    # since stop loss might update at different snaps of current bar, we need additional condition
                    # to make that stop loss price never "worsens" TODO: check if this extra condition can be added in the first if block
                    potential_new_sl_price = self.current_price * (1 - self.sl_pctg)
                    if potential_new_sl_price > self.sl_price:
                        self.sl_price = potential_new_sl_price
                        self.logger.info(f"----- Stop loss price updated at {datetime.now().isoformat()} to: {self.sl_price} -----")


                
                if df.loc[previous_period][f'{self.strategy}_new_position']==-1 or self.current_price <= self.sl_price:
                    # when signal reverses, close the position with sell market order

                    # retrieve a fresh order book
                    self.get_ob_and_sizing(self.owned_ccy_size)

                    self.sell_order = self.exchange.createOrder(
                        self.pair, 
                        'market', 
                        'sell', 
                        self.buy_order['amount']
                    )

                    self.logger.info(f"----- SELL ORDER PLACED at {datetime.now().isoformat()}: id: {self.sell_order['id']}. Order book: ask: {self.top_ask_px} - bid: {self.top_bid_px}. Stop loss level: {self.sl_price} -----")
                    
                    print(f"{datetime.now().isoformat()} - placed a new sell order id: {self.sell_order['id']}.")

                    self._db_new_order(self.sell_order) # adding new order to database

                    # reset positioning
                    self.in_position = False
                    self.buy_order = {}
                    self.sl_price = 0

                else:
                    self.logger.info(f"Order still open, keep cruising. Current position: {self.in_position}. Stop loss level: {self.sl_price}")
            

            else:
                # if order has not been executed yet, check if keeping it open or cancelling it

                if df.loc[previous_period][f'{self.strategy}_new_position']>-1 and self.current_price > self.sl_price:
                    self.logger.info(f"Order {self.buy_order['id']}: PLACED BUT NOT yet executed at {self.buy_order['price']}. Trying to execute it. Current position: {self.in_position}")
                
                else:
                    self.exchange.cancel_order(self.buy_order['id'])
                    self.logger.info(f"----- CANCELLING order {self.buy_order['id']}: at price {self.buy_order['price']} due to adverse price movements -----")
                    
                    # reset positioning
                    self.in_position = False
                    self.buy_order = {}
                    self.sl_price = 0




    def run_bot(self):
        ''' Method that runs the trading bot - to be wrapped inside a scheduler '''

        try:

            bars = self.exchange.fetch_ohlcv(self.pair, timeframe=self.frequency, limit=50) # most recent candle keeps evolving
            self.bars_df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            self.bars_df['timestamp'] = pd.to_datetime(self.bars_df['timestamp'], unit='ms')
            self.bars_df = self.bars_df.set_index('timestamp')
            self.logger.info(f"Succesfully fetched bars at {datetime.now().isoformat()}. Last bar: {self.bars_df.iloc[-1].to_dict()}")

            indicator_df = self._get_crossover()
            
            # self._check_buy_sell_signals(indicator_df, self.pair, self.owned_ccy_size, self.sl_pctg)
            self.logger.info('#####')

            # self._db_new_health_status('UP', '') # adding new bot status
        
        except Exception as err:
            self.end_of_bot_time = datetime.now().isoformat()
            self.logger.critical(f"Bot malfunctioned at {self.end_of_bot_time}", exc_info=True)
            self.logger.info('#####')

            # TODO check if this block is always executed when shutting the script

            # get all open orders for this bot and cancel
            pending_orders_df = db_update.select_all_bot_orders(self.bot_id, self.db_config_parameters)
            pending_orders_id = pending_orders_df['order_id'].tolist()
            for order_id in pending_orders_id:
                self.exchange.cancel_order(order_id)

            # check current position, close netting to 0
            net_exposure = db_update.select_bot_current_exposure(self.bot_id, self.db_config_parameters)
            # if positive exposure, sell it
            if net_exposure > 0:
                self.closing_order = self.exchange.createOrder(
                    self.pair, 
                    'market', 
                    'sell', 
                    net_exposure
                )
                self.get_ob_and_sizing(self) # check order book as a reference
                self._db_new_order(self.closing_order)

            # if negative exposure, close it
            elif net_exposure < 0:
                self.closing_order = self.exchange.createOrder(
                    self.pair, 
                    'market', 
                    'buy', 
                    net_exposure
                )
                self.get_ob_and_sizing(self) # check order book as a reference
                self._db_new_order(self.closing_order)

            # self._db_new_health_status('DOWN', err) # adding new bot status
