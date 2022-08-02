import logging
from datetime import datetime
from StratTest.engine import TradingStrategy
from StratTest import db_update_tables as db_update
import numpy as np
import pandas as pd
import ccxt
import config
import uuid
import json
import signal, sys, os
import pytz
import math
from chart_viz_config import app_timezone
from bot_balances import get_bot_performance_df

# TODO check if data from api need to be assigned a time frequency - to align with resample data in 
# engine and make sure there's no gaps
# TODO using order ID now, check if I can make use of transaction id
# TODO should number of fetched bars be an input to be optimized based on the strategy look back period
# NOTE 1 minute bar problematic, does not return minute before last
# note exchange bars seem to be a bit slow to refresh. a new 5 min bar would start with close px of 2 bars above
# this is happening cause, similarly to 1 minute, it does not return the penultimate bar immediately
## TODO check why new trade not generate immediately at the start of the trading bot - engine ###
print('##### bot.py', os.getpid())

class TradingBot():

    def __init__(self, exchange_subaccount, pair, strategy, frequency, sl_type, sl_pctg, owned_ccy_size, opening_position, container_id, container_name, database_setup, sandbox=True, **params):
        ''' 
            exchange_subaccount: str - name of exchange subaccount used for the strategy
            pair: str - currency pair the bot is trading
            strategy: str - trading strategy used by the engine to genrate signal
            frequency: str - ie '30m'
            sl_type: str - type of stop loss, static or trailing
            sl_pctg: float - stop loss as a percentage of order price
            owned_ccy_size: float - amount of owned currency to be traded on a single order
        '''

        self.logger = logging.getLogger('Trading Bot')

        try:
            self.script_pid = os.getpid()# script program di
            print('##### inside class bot.py', os.getpid())

            ## Exchange connectivity
            self.exchange_subaccount = exchange_subaccount
            self.exchange = ccxt.bitstamp(
                {
                    'apiKey': config.exchange_keys[self.exchange_subaccount]['KEY'],
                    'secret': config.exchange_keys[self.exchange_subaccount]['SECRET']
                }
            )
            self.exchange.set_sandbox_mode(sandbox)

            ## Database connectivity - handle local/local-docker duality
            if database_setup == 'local': database_setup = 'local_docker'
            self.db_config_parameters = config.pg_db_configuration(location=database_setup)

            self.pair = pair
            self.initial_bar_fetch_size = 300
            self.strategy = strategy
            # self.indicator = indicator
            self.frequency = frequency
            self.sl_type = sl_type
            self.sl_pctg = sl_pctg
            self.params = params
            self.in_position = False
            self.signal_time = pd.Timestamp(datetime.now(pytz.utc)).tz_convert(app_timezone) # initiate signal time, updated throughout bot life
            self.owned_ccy_size = owned_ccy_size
            self.opening_position = opening_position
            self.sl_price = None
            self.container_id = container_id
            self.container_name = container_name
            self.bars_df = pd.DataFrame()
            self._db_new_bot() # add new bot to database and define self.bot_id     
            

            # extract parameters generic names for bars table
            if self.strategy == 'EMACrossOverLO':

                self.strat_param_1 = f"ema_{self.params['short_ema']}"
                self.strat_param_2 = f"ema_{self.params['long_ema']}"
                self.strat_param_3 = None
                self.strat_param_4 = None

            elif self.strategy == 'BollingerBandsLO':

                self.strat_param_1 = f"bollinger_hband_{params['window']}"
                self.strat_param_2 = f"bollinger_lband_{params['window']}"
                self.strat_param_3 = f"bollinger_mavg_{params['window']}"
                self.strat_param_4 = None

            # opening position on instanciation
            if self.opening_position == 'Current':
                ''' If Current is selected, try to place an order when bot is instanciated. Only condition to be checked
                    is that the strategy last bar has a valid signal (ie not waiting for next bar confirmation)'''
                
                self.fetch_bars() # get bars
                initial_bars_df = self._get_crossover().reset_index() # generate signal - updates self.bars_df
                    
                current_period = initial_bars_df.index[-1]
                if initial_bars_df.loc[current_period][f'{self.strategy}_signal']==1:

                    self.create_new_order()

                    self.in_position = True
                    self.signal_time = initial_bars_df.loc[current_period]['timestamp']

                    # append bar with a "buy" trade signal
                    self.bars_df.iloc[-1, self.bars_df.columns.get_loc(f'{self.strategy}_trades')] = 'buy' # hardcoded buy, temp replace value to append first bar
                    self._db_new_bar(self.bars_df.reset_index().iloc[-1])
                    
                    self._db_new_order(self.buy_order) # adding new order to database
                    self.logger.info(f"----- Opening BUY ORDER PLACED at {datetime.now().isoformat()}: {self.buy_order}. Order book: ask: {self.top_ask_px} - bid: {self.top_bid_px}. Stop loss level: {self.sl_price} -----")

                else: self.logger.info(f"No Opening order placed, resuming normal bot activity")

            self.sell_order = None # placeholder for an initial empty sell order

            # append initial fetch to db - important on "current opening" bots to see what has happened prior to inception
            for index, row in self.bars_df.reset_index().iterrows():
                self._db_new_bar(row)
            self.logger.info(f"Appended {self.bars_df.shape[0]} new bars")

            self.logger.info(f"Bot instanciated at {datetime.now().isoformat()}")

        except Exception as e:
            self.logger.error(f"Bot instanciation failed due to: {e}", exc_info=True)


    def _db_new_bot(self):
        ''' Method that gathers all the information needed to create a new bot in the database '''

        self.bot_id = 'bot-' + str(uuid.uuid4())
        bot_owned_ccy_end_position = None
        bot_start_date = self.signal_time
        bot_end_date = None
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
            self.exchange_subaccount,
            self.script_pid,
            self.container_id,
            self.container_name
        ]
        # create new database record
        db_update.insert_bots_table(fields, self.db_config_parameters)


    def _db_update_bot(self):
        # TODO calculate bot_owned_ccy_end_position dynamically
        bot_owned_ccy_end_position = 0.
        fields = [
            bot_owned_ccy_end_position,
            self.end_of_bot_time,
            self.bot_id
        ]
        db_update.update_bots_table(fields, self.db_config_parameters)


    def _db_new_order(self, order):
        order_id = 'order-' + str(uuid.uuid4())
        order_timestamp_placed = pd.to_datetime(order['datetime']).tz_convert(app_timezone) # TODO have timezone in configuration
        order_price_placed = order['price']
        order_quantity_placed = order['amount']
        order_direction = order['side']
        order_exchange_type = order['type']
        if order['filled'] == 0:
            order_status = 'dormant'
        elif np.isclose(order['filled'], order['amount']): # isclose for float comparison
            order_status = 'filled'
        else:
            order_status = 'partialled'
        order_ob_bid_price = self.top_bid_px
        order_ob_ask_price = self.top_ask_px
        order_ob_bid_size = self.top_bid_quantity
        order_ob_ask_size = self.top_ask_quantity
        order_exchange_trade_id = order['id']
        order_trades = order['trades']
        order_quantity_filled = order['amount'] - order['remaining'] # or simply the filled part
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


    def _db_update_order(self, order_exchange_trade_id, order_chunks):
        ''' updated orders in the database based on bot id and exchange trade id (fetchMyTrades) - 
            to allow for orders not immediately filled.
            bot id not necessary here, but helps to showcase that everything is handled on a bot by bot basis.
            order_exchange_trade_id: string, exchange unique oder identiefier
            order_chunks: list containing all the clips belonging to the id described above
        '''

        # ie: all trades associated with the order and sum amount traded across those
        order_trades = json.dumps(order_chunks)

        order_quantity_filled = 0
        order_weighted_prices = 0 # components for weighted average price
        order_fee = 0

        for order_chunk in order_chunks:
            # for each chunk of the order, calculate the stats
            order_quantity_filled += order_chunk['amount']
            order_weighted_prices += order_chunk['price'] * order_chunk['amount']
            order_fee += order_chunk['fee']['cost']

        order_price_filled = order_weighted_prices / order_quantity_filled # weighted average price

        # order initial amount placed compared to order_quantity_filled to determine status
        total_amount_placed = db_update.order_placed_amount(order_exchange_trade_id, self.db_config_parameters)
        
        if order_quantity_filled == 0:
            order_status = 'dormant'
        elif np.isclose(order_quantity_filled, total_amount_placed): # isclose for floating comparison
            order_status = 'filled'
        else:
            order_status = 'partialled'

        fields = [
            order_status,
            order_trades,
            order_quantity_filled,
            order_price_filled,
            order_fee,
            self.bot_id,
            order_exchange_trade_id,
            
        ]

        db_update.update_single_order_table(fields, self.db_config_parameters)


    def _db_new_bar(self, bar):
        ''' bar: pd.Series containing strategy latest pulled data and indicator '''

        bar_record_timestamp = self.bars_fetched_at_timestamp.isoformat()
        bar_bar_time = bar['timestamp']
        bar_open = bar['open']
        bar_high = bar['high']
        bar_low = bar['low']
        bar_close = bar['close']
        bar_volume = bar['volume']
        bar_action = bar[f'{self.strategy}_trades']
        bar_in_position = self.in_position
        bar_stop_loss_price = self.sl_price
        bar_strategy_signal = int(bar[f'{self.strategy}_signal'])

        if self.strat_param_1: bar_param_1 = bar[self.strat_param_1]
        else: bar_param_1 =  None

        if self.strat_param_2: bar_param_2 = bar[self.strat_param_2]
        else: bar_param_2 =  None

        if self.strat_param_3: bar_param_3 = bar[self.strat_param_3]
        else: bar_param_3 =  None

        if self.strat_param_4: bar_param_4 = bar[self.strat_param_4]
        else: bar_param_4 =  None

        fields = [
            self.bot_id,
            bar_record_timestamp,
            bar_bar_time, 
            bar_open,
            bar_high,
            bar_low,
            bar_close,
            bar_volume,
            bar_action,
            bar_in_position,
            bar_stop_loss_price,
            bar_strategy_signal,
            bar_param_1,
            bar_param_2,
            bar_param_3,
            bar_param_4
        ]

        # create new orderbook record
        db_update.insert_order_book_bars_table(fields, self.db_config_parameters)


    def _db_new_health_status(self, health_status, err):

        health_status_timestamp = pd.Timestamp(datetime.now(pytz.utc)).tz_convert(app_timezone)

        fields = [
            self.bot_id,
            health_status_timestamp,
            health_status,
            err
        ]

        # create new api health status database record
        db_update.insert_health_status_table(fields, self.db_config_parameters)


    @staticmethod
    def _clean_bars_response(bars):
        ''' Convert bars api response into a dataframe, sort it and handle timestamp conversion '''

        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']).sort_values(by='timestamp')
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['timestamp'] = df['timestamp'].dt.tz_localize('utc').dt.tz_convert(app_timezone) # localize to utc and then convert to London tz
        df = df.set_index('timestamp') # useful to have timestamp index for the engine
        return df


    def fetch_bars(self):
        ''' Check existing bars dataframe against latest pulled data and update only the essential part of it '''

        if self.bars_df.shape[0] == 0: # initial fetch

            bars = self.exchange.fetch_ohlcv(self.pair, timeframe=self.frequency, limit=self.initial_bar_fetch_size) # most recent candle keeps evolving
            self.bars_df = self._clean_bars_response(bars)
            self.bars_fetched_at_timestamp = pd.Timestamp(datetime.now(pytz.utc)).tz_convert(app_timezone) # used for database, logging and df delta checks
            self.logger.info(f"Succesfully fetched initial {self.initial_bar_fetch_size} bars at {self.bars_fetched_at_timestamp.isoformat()}. Last bar: {self.bars_df.iloc[-1].to_dict()}")

        else: # fetch deltas to minimize data called via api

            # set index if timestamp is not set as index
            if 'timestamp' in self.bars_df.columns:
                self.bars_df = self.bars_df.set_index('timestamp')

            # working out how many bars to fetch
            bar_fetching_time = pd.Timestamp(datetime.now(pytz.utc)).tz_convert(app_timezone)
            last_existing_bar_time = self.bars_df.index.max()
            minutes_since_last_bar = (bar_fetching_time - last_existing_bar_time).seconds / 60 # elapsed time since last fetched bar
            
            freq_in_minutes = int(self.frequency .replace('m', '')) # translate minute frequency into integer numbeer of minutes

            # number of new bars to fetch: if 1 is current bar refreshed, if 2 means that new bar has started
            limit_bars_fetch = math.ceil(minutes_since_last_bar / freq_in_minutes) + 5 # ceil rounds up the number of bars to fetch - +5 to make extra sure no bars are lost
            delta_bars = self.exchange.fetch_ohlcv(self.pair, timeframe=self.frequency, limit=limit_bars_fetch) #
            self.bars_fetched_at_timestamp = pd.Timestamp(datetime.now(pytz.utc)).tz_convert(app_timezone)
            self.logger.info(f"Succesfully fetched {limit_bars_fetch} delta bars")
            
            print(f"delta updated, fetched {limit_bars_fetch} bars")
            delta_bars_df = self._clean_bars_response(delta_bars)

            # replace dataframe part re-fetched
            self.bars_df = self.bars_df.loc[~(self.bars_df.index.isin(delta_bars_df.index))] # drop old rows
            self.bars_df = pd.concat([self.bars_df, delta_bars_df], axis=0) # append new ones
            self.bars_df.sort_index(inplace=True) # after stacking the 2 df, sort index timestamp

            if self.bars_df.shape[0] > self.initial_bar_fetch_size: 
                print('in limit_bars_fetch > 1')
                bars_to_drop = self.bars_df.shape[0] - self.initial_bar_fetch_size
                # if shape of dataframe exceeds the initial fetch size, drop elements at the top
                self.bars_df = self.bars_df.iloc[bars_to_drop: , :] # drop top dataframe rows 1 in excess of limit_bars_fetch
                self.logger.info(f"Dropped {bars_to_drop} rows")

        # self.logger.info(f"Current bars df shape: {self.bars_df.shape}. Tail:\n {self.bars_df.tail(15).to_string()}")
        # self.logger.info(self.bars_df.tail(15).to_string())


    def _get_crossover(self, plot=False):

        trading_strategy = TradingStrategy(self.bars_df, self.frequency, mode='live')
        print(self.params)
        trading_strategy.add_strategy(
            self.strategy,
            execution_type='next_bar_open',#None, 
            stop_loss_bps=self.sl_pctg*10000,
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

        # pull orders history
        df_orders = db_update.select_all_bot_orders(
            self.bot_id, 
            ('filled', '', ), 
            self.db_config_parameters
        )
        if df_orders.shape[0] > 0:
            performance_df = get_bot_performance_df(df_orders)
            # update owned ccy size
            self.owned_ccy_size = self.owned_ccy_size + performance_df['base_ccy_cum_net'].iloc[-1]

        # current_mid_price : 1 BTC = my_size : x BTC
        self.trade_size = self.owned_ccy_size/self.top_mid_px



    def check_open_orders(self):
        ''' Only one open order per pair.  Orders are listed chronologically (ie oldest order with index 0)'''

        self.open_orders = self.exchange.fetchOpenOrders(self.pair)

        # check if current selected pair has more than one active order
        self.pair_open_orders = [order for order in self.open_orders if order['symbol']==self.pair]

        assert len(self.pair_open_orders) <= 1, f''' Too many orders ({len(self.pair_open_orders)}) on {self.pair} - logic did not work correctly. Check open orders immediately. exchange.fetchOpenOrders(symbol) '''


    def order_executed_check(self, order_exchange_trade_id):
        ''' Check if a certain order 'id' has been executed '''
        # check if order has been already fully filled, if so move on
        if db_update.order_filled_checked(order_exchange_trade_id, self.db_config_parameters):
            return True
        
        self.executed_orders = self.exchange.fetchMyTrades(self.pair)
        current_order_records = [order for order in self.executed_orders if order['order']==order_exchange_trade_id]
        order_checked = len(current_order_records) >= 1 # at least one order chunk
        
        if order_checked:
            self._db_update_order(order_exchange_trade_id, current_order_records) # only value with records in the database
            self.logger.info(f"-- Order status updated at {datetime.now().isoformat()}")
        else:
            self.logger.warning(f"-- Order not executed, order_checked less than 1 {current_order_records} - at {datetime.now().isoformat()}")

        return order_checked


    def create_new_order(self):
        # get order book and sizing
        self.get_ob_and_sizing()

        self.order_price = self.top_ask_px * 1.001
        ## check if already in position, avoid double orders on same bar refreshing with new signal every time
        # place limit buy order 10bps above current ask price - provide some buffer for signal confirmation
        try:
            self.buy_order = self.exchange.createLimitOrder(
                self.pair,
                side='buy',
                amount=self.trade_size, 
                price=self.order_price 
            )

        except Exception as e:
            self.orders_error_handling(e)
            self.logger.error(f'### Order NOT place correctly due to the following exception: {type(e).__name__} - {e}')
        
        # set initial stop loss NOTE might need to be adjusted with trailing/dynamic logic
        # self.sl_price = self.buy_order['price'] * (1 - self.sl_pctg)
        self.sl_price = self.bars_df.iloc[-1]['sl_price'] # already calculated from engine


    def orders_error_handling(self, e):
        ''' Handle orders related exception.
            if exception is raised, it's then captured y the run_bot exception block
            if the exception is not a known one, activate the termination protocle and leave the bot
        '''
        if type(e).__name__ == 'BadSymbol':
            self.logger.error(f'handling bad simble excp, {e}, {type(e).__name__}', exc_info=True)
            raise

        elif type(e).__name__ == 'InsufficientFunds':
            # insufficient funds
            self.logger.error(f'insufficient funds error: {e}', exc_info=True)
            raise

        elif type(e).__name__ == 'InvalidOrder':
            # invalid order, ie Minimum order size is 10.0 GBP
            self.logger.error(f'InvalidOrder error: {e}', exc_info=True)
            raise

        elif type(e).__name__ == 'ExchangeError':
            # errors such as price more than 20% above mkt price
            self.logger.error(f'exchange error: {e}', exc_info=True)
            raise

        elif type(e).__name__ == 'ExchangeNotAvailable':
            # errors such as price more than 20% above mkt price
            self.logger.error(f'Network error, exchange not available: {e}', exc_info=True)
            raise

        else:
            # in case of unaught exception, just log the error and carry on - for now
            self.logger.error(f'other uncaught: , {e}, {type(e).__name__}', exc_info=True)
            raise
            # self._bot_termination_protocol(e)
            

    ## TODO ORDER MANAGEMENT METHOD:
    ## check against open orders, live orders and past trade. Essential: order ID, side, amount (filled) and state of the order

    def _check_buy_sell_signals(self):

        current_period = self.bars_df.index[-1] # current bar - used for stop losses and reversals
        previous_period = self.bars_df.index[-2] # previous bar - used to check signals

        self.current_price = self.bars_df.loc[current_period]['close']
        self.previous_price = self.bars_df.loc[previous_period]['close']

        # if not in position, check the signal..
        if not self.in_position:

            # .. but first check that any previous sell order has been executed
            if self.sell_order:
                if self.order_executed_check(self.sell_order['id']):
                    self.sell_order = None
                    # TODO a check could be added that the order has been fully executed, fetching from db?
                    self.logger.info(f"SELL ORDER has been executed, setting self.sell_order = None")

            else:
                # business as usual
                if self.bars_df.loc[previous_period][f'{self.strategy}_new_position']==1 and self.bars_df.loc[previous_period]['timestamp']>self.signal_time:
                    # if signal is 1 and has been generated on a new bar - new timestamp, allows for signal confirmation

                    self.create_new_order() # initial stop loss set in here                  
                    self.in_position = True
                    self.signal_time = self.bars_df.loc[previous_period]['timestamp']
                    self._db_new_order(self.buy_order) # adding new order to database
                    self.logger.info(f"----- New BUY ORDER PLACED at {datetime.now().isoformat()}: {self.buy_order}. Order book: ask: {self.top_ask_px} - bid: {self.top_bid_px}. Stop loss level: {self.sl_price}. Notional Equivalent {self.owned_ccy_size} -----")
                else:
                    self.logger.info(f"No new orders. Current position: {self.in_position}")
                    self.logger.info(f"Current period: {current_period}, Previous period: {previous_period}, Current period ts: {self.bars_df.loc[current_period]['timestamp']}, Previous period ts: {self.bars_df.loc[previous_period]['timestamp']}, self.signal_time: {self.signal_time}")
        
        elif self.in_position:

            if self.order_executed_check(self.buy_order['id']):

                # if in position and order has been executed monitor price level and adjust stop loss level accordingly
                # if one of the 2 conditions is hit, close the position with a market order

                if self.current_price > self.previous_price and self.current_price > self.order_price:

                    potential_new_sl_price = self.bars_df.iloc[-1]['sl_price']
                    # update sl price if potential_new_sl_price constitutes an improvement
                    if potential_new_sl_price > self.sl_price:
                        self.sl_price = potential_new_sl_price
                        self.logger.info(f"----- {self.sl_type} stop loss price updated to: {self.sl_price} -----")


                if self.bars_df.loc[previous_period][f'{self.strategy}_new_position']==-1 or self.current_price <= self.sl_price:
                    # when signal reverses, close the position with sell market order

                    # retrieve a fresh order book
                    self.get_ob_and_sizing()

                    self.sell_order = self.exchange.createOrder(
                        self.pair, 
                        'market', 
                        'sell', 
                        self.buy_order['amount']
                    )

                    self.logger.info(f"----- SELL ORDER PLACED at {datetime.now().isoformat()}: id: {self.sell_order['id']}. Order book: ask: {self.top_ask_px} - bid: {self.top_bid_px}. Stop loss level: {self.sl_price} -----")

                    self._db_new_order(self.sell_order) # adding new order to database

                    # reset positioning
                    self.in_position = False
                    self.buy_order = {}
                    self.sl_price = 0

                else:
                    self.logger.info(f"Order still open, keep cruising. Current position: {self.in_position}. Stop loss level: {self.sl_price}")
                    self.logger.info(f"Current period: {current_period}, Previous period: {previous_period}, Current period ts: {self.bars_df.loc[current_period]['timestamp']}, Previous period ts: {self.bars_df.loc[previous_period]['timestamp']}, self.signal_time: {self.signal_time}")
            

            else:
                # if order has not been executed yet, check if keeping it open or cancelling it

                if self.bars_df.loc[previous_period][f'{self.strategy}_new_position']>-1 and self.current_price > self.sl_price:
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
            # fetching initial bars or just the delta/missing ones
            self.fetch_bars()

            # generate signal - updates self.bars_df
            self._get_crossover()
            
            # generate orders based on signal - reset index, need timestamp column in _check_buy_sell_signals and _db_new_bar
            self.bars_df.reset_index(inplace=True)
            self._check_buy_sell_signals()
            
            # update bars record on database
            self._db_new_bar(self.bars_df.iloc[-1]) # here in order to also add info about the indicator and stop losses

            self.logger.info(f"Current bars df shape: {self.bars_df.shape}. Tail:\n {self.bars_df.tail(10).to_string()}")
            self.logger.info('#####')

            self._db_new_health_status('UP', '') # adding new bot status
        
        except Exception as err:
            print('Bot malfunctioned')
            self._db_new_health_status('MALF', str(err)) # [:100]
            self.end_of_bot_time = pd.Timestamp(datetime.now(pytz.utc)).tz_convert(app_timezone)
            self.logger.critical(f"Bot malfunctioned at {self.end_of_bot_time}", exc_info=True)
            self.logger.info('#####')


    ### Bot termination protocol steps ###
    def _cancel_bot_pending_orders(self):
        ''' When trading bot fails or is terminated, cancel all pending orders '''
        try:
            # get all open orders for this bot and cancel
            pending_orders_df = db_update.select_all_bot_orders(self.bot_id, order_statuses=('dormant', 'partialled'), config_parameters=self.db_config_parameters)
            pending_orders_id = pending_orders_df['order_id'].tolist()
            for order_id in pending_orders_id:
                self.exchange.cancel_order(order_id)
            self.logger.info(f"Cancelled {len(pending_orders_id)} pending orders")
        except Exception as e:
            self.logger.error("Error in cancelling pending orders", exc_info=True)


    def _close_open_positions(self):
        ''' When trading bot fails or is terminated, liquidate all positions as market orders '''
        try:
            # check current position, close netting to 0
            net_exposure = db_update.select_bot_current_exposure(self.bot_id, self.db_config_parameters)
            if net_exposure:
                # if positive exposure, sell it
                if net_exposure > 0:
                    self.closing_order = self.exchange.createOrder(
                        self.pair, 
                        'market', 
                        'sell', 
                        net_exposure
                    )
                    self._db_new_order(self.closing_order)

                # if negative exposure, close it
                elif net_exposure < 0:
                    self.closing_order = self.exchange.createOrder(
                        self.pair, 
                        'market', 
                        'buy', 
                        net_exposure
                    )
                    self._db_new_order(self.closing_order)
            else:
                print(f'Net exposure is {net_exposure}')

            self.logger.info(f"Closed open position of {net_exposure}")

        except Exception as e:
            self.logger.error("Failed closing open positions", exc_info=True)

    def _bot_termination_protocol(self, err):
        self.end_of_bot_time = pd.Timestamp(datetime.now(pytz.utc)).tz_convert(app_timezone) # used to update database and in logger
        self.logger.critical(f"Activated bot termination protocol at {self.end_of_bot_time}", exc_info=True)
        self._cancel_bot_pending_orders()
        self._close_open_positions()
        self._db_update_bot() # update bots table
        self._db_new_health_status('DOWN', err) # adding new bot status
        self.logger.info('## End of termination protocol ##')
        ## TODO add a little while loop to make sure closing orders have been executed, not just placed