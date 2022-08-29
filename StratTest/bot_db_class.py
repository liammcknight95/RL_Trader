import logging
from datetime import datetime
from StratTest.engine import TradingStrategy
from StratTest.bot_config import tick_size_decimals
from StratTest import db_update_tables as db_update
import numpy as np
import pandas as pd
import ccxt
import config
import uuid
import json
import signal, sys, os
import pytz
from chart_viz_config import app_timezone
from bot_balances import get_bot_performance_df


class BotDB():

    def get_db_config(self, database_setup):
        ## Database connectivity - handle local/local-docker duality
        if database_setup == 'local': database_setup = 'local_docker'
        self.db_config_parameters = config.pg_db_configuration(location=database_setup)

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
