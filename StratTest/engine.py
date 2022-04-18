from datetime import datetime
from ta.volatility import BollingerBands, AverageTrueRange
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator

import numpy as np
import pandas as pd

import plotly.graph_objects as go
from plotly.subplots import make_subplots


class TradingStrategy():

    def __init__(self, data, frequency, mode='testing' , printout=False):
        assert isinstance(data.index, pd.DatetimeIndex), 'DataFrame passed does not have a datetime index'
        # if data.index.freq == frequency: self.df = data # dataframe with open, high, low, close, volume columns
        if mode=='testing': self.resample_data(data, frequency)
        elif mode=='live': self.df = data
        self.frequency = frequency
        self.printout = printout
        self.strategy = ''


    def resample_data(self, data, frequency):

        ''' Method to be called if the dataframe is at a lower granularity than desired dataset '''
        
        # resample data to wanted frequency
        print(f'Resampling data from {data.index.freq} to {frequency}')
        self.df = data.groupby(pd.Grouper(level=data.index.name, freq=frequency)).agg(
            close=('Mid_Price', 'last'),
            open=('Mid_Price', 'first'),
            high=('Mid_Price', max),
            low=('Mid_Price', min),
            Bid_Size_30bps=('Bid_Size_30bps', np.mean),
            Ask_Size_30bps=('Ask_Size_30bps', np.mean),
            ## comment out until trades restored
            # amount_buy=('amount_buy', np.sum),
            # amount_sell=('amount_sell', np.sum),
            # wav_price_buy=('wav_price_buy', np.mean),
            # wav_price_sell=('wav_price_sell', np.mean),
            # unique_orders_buy=('unique_orders_buy', np.sum),
            # unique_orders_sell=('unique_orders_sell', np.sum)
            # 'Mid_Price': ['last', 'first', np.max, np.min], 
            # 'volume': np.sum
            
        ).copy()

        self.df['amount_buy'] = 0
        self.df['amount_sell'] = 0
        self.df['volume'] = self.df['amount_buy'] + self.df['amount_sell']
        self.df.index.name = 'datetime'

    def add_indicator(self, indicator, **params):

        if indicator == 'BollingerBands':

            bb_indicator = BollingerBands(self.df['close'], window=params['window'], window_dev=params['window_dev'])

            # bands created adding and subtracting std from moving average
            self.df[f'bollinger_hband_{params["window"]}'] = bb_indicator.bollinger_hband()
            self.df[f'bollinger_lband_{params["window"]}'] = bb_indicator.bollinger_lband()
            self.df[f'bollinger_mavg_{params["window"]}'] = bb_indicator.bollinger_mavg()


        elif indicator == 'AverageTrueRange':

            atr_indicator = AverageTrueRange(self.df['high'], self.df['low'], self.df['close'])
            
            self.df['atr'] = atr_indicator.average_true_range()


        elif indicator == 'EMAIndicator':

            ema_indicator = EMAIndicator(self.df['close'], window=params['window'])

            self.df[f'ema_{params["window"]}'] = ema_indicator.ema_indicator()

        
        elif indicator == 'RSI':

            rsi_indicator = RSIIndicator(self.df['close'], window=params['window'])

            self.df[f'rsi_{params["window"]}'] = rsi_indicator.rsi()



        if self.printout: print(f'Adding {indicator} with: {params}')


    def _calculate_trade_groupers(self):
        ''' function that create a trade grouper column using a timestamp, to identify each
        new individual trade '''

    # get positions in the dataframe where indicator generates signals
        open_trades_idx = np.where(self.df[f'{self.strategy}_new_position']==1)[0]
        closing_trades_idx = np.where(self.df[f'{self.strategy}_new_position']==-1)[0]
        between_open_close_idx = np.where(self.df[f'{self.strategy}_signal']!=0)
        # out_market_idx = np.where((self.df[f'{self.strategy}_signal']==0) 
        #     & (self.df[f'{self.strategy}_new_position']!=0))[0]
        # print(open_trades_idx.shape)
        # print(closing_trades_idx.shape)

        self.df['trade_grouper'] = np.nan
        self.df.loc[self.df.iloc[open_trades_idx].index, 'trade_grouper'] = self.df.iloc[open_trades_idx].index # add grouper at opening
        self.df.loc[self.df.iloc[closing_trades_idx].index, 'trade_grouper'] = self.df.iloc[open_trades_idx[:closing_trades_idx.shape[0]]].index # add grouper at closing
        self.df.loc[self.df.iloc[between_open_close_idx].index, 'trade_grouper'] = self.df.iloc[between_open_close_idx]['trade_grouper'].fillna(method='ffill') # add grouper between


    def _calculate_exec_prices(self, execution_type):
        ''' exec_type can assume values of:
                - next_bar_open: assume entry and exit trades are executed at the next bar open px
                - current_bar_close: assume entry and exit trades are executed at the current bar close px
                - next_bar_worst: TODO, assume trade is executed at the worst px available next bar, high 
                    or low depending on the trade directions         
        '''

        # TODO: these assume that order is not cancelled between order being triggered and executed
        if execution_type == 'next_bar_open':
            self.df['px_returns_calcs']  = np.where(
                self.df[f'{self.strategy}_new_position']!=0, self.df['open'].shift(-1), self.df['close'])
            self.df['execution_time'] = pd.to_datetime(np.where(self.df[f'{self.strategy}_new_position']!=0, self.df.index.shift(1, freq=self.frequency), pd.NaT))

        elif execution_type == 'current_bar_close':
            self.df['px_returns_calcs'] = self.df['close'].copy()
            self.df['execution_time'] = pd.to_datetime(np.where(self.df[f'{self.strategy}_new_position']!=0, self.df.index, pd.NaT))

        elif execution_type == 'cheat_previous_close':
            self.df['px_returns_calcs'] = np.where(
                self.df[f'{self.strategy}_new_position']==1, self.df['close'], 
                np.where( 
                    self.df[f'{self.strategy}_new_position']==-1, self.df['close'].shift(1), self.df['close']
                )
            )
            self.df['execution_time'] = pd.to_datetime(np.where(self.df[f'{self.strategy}_new_position']!=0, self.df.index.shift(-1), pd.NaT))

        # apply any trading fee after stop loss calculation
        self._add_transaction_costs()


    def _add_transaction_costs(self):
        '''
        comms_bps: float, execution cost in basis points
        create column populated with execution prices based on transaction costs
        used later to create trades dataframe
        '''
        self.comms_pcgt = self.comms_bps/10000
        # print(self.comms_bps, self.comms_pcgt)

        # if self.stop_loss>0: 
        #     self.df['number_transaction'] = self.df[f'{self.strategy}_new_position'].abs() + self.df['sl_hit'].abs()
        # else:
        #     self.df['number_transaction'] = self.df[f'{self.strategy}_new_position'].abs()
            
        # self.df['total_comms_%'] = self.comms_pcgt * self.df['number_transaction']

        # recalculate prices where a new position occurs. Increase price when buying and decrease when selling (+)
        self.df['execution_price'] = np.where(
            self.df[f'{self.strategy}_new_position']!=0, 
            self.df['px_returns_calcs'] * (1 + (self.comms_pcgt * self.df[f'{self.strategy}_new_position'])),
            np.nan
        )


    def _get_strat_gross_returns(self):
        ''' 
        Get strategy gross log returns time series, inclusive of stop losses and execution assumptions (ie current or next close), 
        but without accounting for any trading costs
        '''

        # get gross log cumulative returns over time
        self.df['gross_log_returns'] = (np.log(self.df['px_returns_calcs']) - np.log(self.df['px_returns_calcs'].shift(1))).shift(-1)

        self.df[f'{self.strategy}_gross_log_returns'] = self.df['gross_log_returns'] * self.df[f'{self.strategy}_signal'] # accounts for long short

        self.df[f'{self.strategy}_gross_cum_pctg_returns'] = np.exp(self.df[f'{self.strategy}_gross_log_returns'].cumsum()) -1  # cumulative gross performance when in


    def _calculate_strat_metrics(self):
        '''
        Create trades dataframe and calculate strategy metrics
        Calculated using execution_price, which is the the price net of transaction cost
        '''

        # get individual trades performances
        self.trades_df = self.df.groupby('trade_grouper').agg(
            entry_price=('execution_price', 'first'), 
            exit_price=('execution_price', 'last'), 
            trade_len=('trade_grouper', 'count'),
            direction=(f'{self.strategy}_new_position', 'first'),
            liquidated_at=('execution_time', 'last'),
            sl_hit=('sl_hit', 'sum')
        )

        self.trades_df['trades_log_return'] = np.log(self.trades_df['exit_price']) - np.log(self.trades_df['entry_price'])
        self.trades_df['cum_trades_log_return'] = self.trades_df['trades_log_return'].cumsum()

        self.trades_df['trades_pctg_return'] = np.exp(self.trades_df['trades_log_return']) - 1
        self.trades_df['cum_trades_pctg_return'] = np.exp(self.trades_df['cum_trades_log_return']) - 1

        # net return
        try:
            self.stats_cum_return = f"{self.trades_df['cum_trades_pctg_return'][-1]:.2%}"
        except:
            self.stats_cum_return = f"{np.nan}"

        # number of trades
        self.stats_number_trades = self.trades_df.shape[0]

        # net return per trade
        self.stats_avg_return = self.trades_df['trades_pctg_return'].mean()

        # best win
        self.stats_best_trade = self.trades_df['trades_pctg_return'].max()

        # worst loss
        self.stats_worst_trade = self.trades_df['trades_pctg_return'].min()


    def _add_stop_loss(self):
        # works well for long only
        self.df['temp_trade_grouper_filled_nans'] = self.df['trade_grouper'].fillna(datetime(2030,1,1))
        self.df['sl_price'] = self.df.groupby('temp_trade_grouper_filled_nans')['high'].transform(pd.Series.cummax)  * (1-(self.stop_loss_bps/10000)) * self.df[f'{self.strategy}_signal']
        
        self.df['sl_hit'] = (self.df['low'] < self.df['sl_price']) * (self.df['close'] < self.df['open']) * self.df[f'{self.strategy}_signal']

        for name, sub_df in self.df.groupby(by='trade_grouper'):

            # entry_price = self.df[self.df.index==name]['px_returns_calcs'].values[0]
            direction = self.df[self.df.index==name][f'{self.strategy}_new_position'].values[0]

            # check for stop losses before any backtesting
            if direction > 0: # if long
                
                def handle_stop_loss_recursively(sub_df):
                    # print('here')
                    if sub_df['sl_hit'].sum()==0:
                        # if stop loss not hit do nothing
                        return 'finished'
                    else:
                        sl_trigger_time = sub_df[sub_df['sl_hit'] > 0].index[0] # when stop loss was triggered
                        sl_affected_range = sub_df[sub_df.index>=sl_trigger_time].index # all the datapoints subsequently affected by stop loss

                        # self.df.loc[sl_trigger_time, 'sl_hit'] = -1 # flag stop loss being hit
                        self.df.loc[sl_trigger_time, f'{self.strategy}_trades'] = "stop_sell" # sl trade type
                        self.df.loc[sl_trigger_time, f'{self.strategy}_new_position'] = -1
                        self.df.loc[sl_affected_range, f'{self.strategy}_signal'] = 0 # turn signal to 0 - out of market
                        self.df.loc[sl_affected_range[-1], f'{self.strategy}_new_position'] = 0 # set original closing position to 0
                        self.df.loc[sl_affected_range[1:], 'trade_grouper'] = np.nan # set trade grouper to nan, with the exception of the actual trigger timestamp

                        # check if it trades should be resumed, conditions: 
                        previous_high_px = sub_df[sub_df.index<=sl_trigger_time]['high'].max()
                        # series with all the occurrences where a trade could be reactivated
                        trade_reactivate_series = sub_df[(sub_df.index>sl_trigger_time)&(sub_df['close']>previous_high_px)]

                        if trade_reactivate_series.shape[0]>0: # restore sub df signals and add a new buy..
                            sub_df_resume_trade = sub_df[sub_df.index>=trade_reactivate_series.index[0]].copy()

                            print('reactiating trades', sub_df_resume_trade.index[0])
                            new_start_trade = sub_df_resume_trade.index[0]
                            new_trade_range = sub_df_resume_trade[sub_df_resume_trade.index>=new_start_trade].index

                            self.df.loc[new_start_trade, f'{self.strategy}_trades'] = "buy"
                            self.df.loc[new_start_trade, f'{self.strategy}_new_position'] = 1
                            self.df.loc[new_trade_range, f'{self.strategy}_signal'] = 1
                            self.df.loc[new_trade_range[-1], f'{self.strategy}_new_position'] = -1 # set original closing position to -1 - # check maybe wait for next bar
                            self.df.loc[new_trade_range, 'trade_grouper'] = new_start_trade # create new trade grouper
                            
                            if sub_df_resume_trade['sl_hit'].sum()==0: # if trade can resume and no further sl is hit carry it till the end of this sub df..
                                print('no more sl')
                                return 'finished'

                            else: # ..handle this as a new trade with stop loss - recursion
                                print('one more recursion')
                                return handle_stop_loss_recursively(sub_df_resume_trade)
                
                handle_stop_loss_recursively(sub_df)
        self.df.loc[self.df[f'{self.strategy}_new_position']==0, 'sl_hit'] = 0 # reset where trades where not reactivated - never hit stops


    def add_strategy(self, strategy, stop_loss_bps=0, comms_bps=0, execution_type='next_bar_open', print_trades=False, indicators_params={}):

        self.strategy = strategy
        self.execution_type = execution_type ### self.execution_type
        self.stop_loss_bps = stop_loss_bps
        self.comms_bps = comms_bps
        self.print_trades = print_trades
        # transform basis points commission in percentage
        # print(indicators_dict)
        # indicators = indicators_dict['indicators_dict']
        # print(indicators)

        if self.strategy == 'EMACrossOverLS':

            self.short_ema = f"ema_{indicators_params['short_ema']}"
            self.long_ema = f"ema_{indicators_params['long_ema']}"

            self.add_indicator('EMAIndicator', window=indicators_params['short_ema'])
            self.add_indicator('EMAIndicator', window=indicators_params['long_ema'])

            ## Generate Signals
            # signal: tiemseries of +1 when long, -1 when short, 0 when neutral
            self.df[f'{self.strategy}_signal'] = np.where(
                self.df[self.short_ema] > self.df[self.long_ema ], 1, 
                np.where(self.df[self.short_ema] < self.df[self.long_ema ], -1, 0))

            # trades: flag when a new trade is generated - descriptive
            self.df[f'{self.strategy}_trades'] = np.where(
                self.df[f'{self.strategy}_signal'].diff() > 0, 'buy', 
                np.where(self.df[f'{self.strategy}_signal'].diff() < 0, 'sell', 'hold'))

            # trades: flag when a new trade is generated - numeric
            self.df[f'{self.strategy}_new_position'] = np.where(
                self.df[f'{self.strategy}_signal'].diff() > 0, +1, 
                np.where(self.df[f'{self.strategy}_signal'].diff() < 0, -1, 0))


        elif self.strategy == 'EMACrossOverLO':

            # indicator column names
            self.short_ema = f"ema_{indicators_params['short_ema']}"
            self.long_ema = f"ema_{indicators_params['long_ema']}"
            self.indicator_names = [self.short_ema, self.long_ema]

            # add indicators
            self.add_indicator('EMAIndicator', window=indicators_params['short_ema'])
            self.add_indicator('EMAIndicator', window=indicators_params['long_ema'])

            ## Generate Signals
            # signal: tiemseries of +1 when long, -1 when short, 0 when neutral
            self.df[f'{self.strategy}_signal'] = np.where(
                self.df[self.short_ema] > self.df[self.long_ema], 1, 0)

            # trades: flag when a new trade is generated - descriptive
            self.df[f'{self.strategy}_trades'] = np.where(
                self.df[f'{self.strategy}_signal'].diff() > 0, 'buy', 
                np.where(self.df[f'{self.strategy}_signal'].diff() < 0, 'sell', 'hold'))

            # trades: flag when a new trade is generated - numeric
            self.df[f'{self.strategy}_new_position'] = np.where(
                self.df[f'{self.strategy}_signal'].diff() > 0, +1, 
                np.where(self.df[f'{self.strategy}_signal'].diff() < 0, -1, 0))


        elif self.strategy == 'BollingerBandsLO':

            # indicator column names
            self.hband = f"bollinger_hband_{indicators_params['window']}"
            self.lband = f"bollinger_lband_{indicators_params['window']}"
            self.mavg = f"bollinger_mavg_{indicators_params['window']}"
            self.indicator_names = [self.hband, self.lband, self.mavg]

            # add indicators
            self.add_indicator('BollingerBands', window=indicators_params['window'], window_dev=indicators_params['window_dev'])

            ## Generate Signals
            self.df[f'{self.strategy}_signal'] = np.where(self.df['close'] > self.df[self.hband], 1,
                np.where(self.df['close'] < self.df[self.mavg], 0, np.nan))

            self.df[f'{self.strategy}_signal'] = self.df[f'{self.strategy}_signal'].fillna(method='ffill').fillna(0) # fillna 0 handles initial NAs

            # trades: flag when a new trade is generated - descriptive
            self.df[f'{self.strategy}_trades'] = np.where(
                self.df[f'{self.strategy}_signal'].diff() > 0, 'buy', 
                np.where(self.df[f'{self.strategy}_signal'].diff() < 0, 'sell', 'hold'))

            # trades: flag when a new trade is generated - numeric
            self.df[f'{self.strategy}_new_position'] = np.where(
                self.df[f'{self.strategy}_signal'].diff() > 0, +1, 
                np.where(self.df[f'{self.strategy}_signal'].diff() < 0, -1, 0))
                
        elif self.strategy == 'MultiIndic':
            self.rsi = f"rsi_{indicators_params['window']}"
            self.indicator_names = [self.rsi]

            # add indicators
            self.add_indicator('RSI', window=indicators_params['window'])

            ## Generate Signals
            self.df[f'{self.strategy}_signal'] = np.where(self.df[self.rsi] < 70, 1, 0)


            # trades: flag when a new trade is generated - descriptive
            self.df[f'{self.strategy}_trades'] = np.where(
                self.df[f'{self.strategy}_signal'].diff() > 0, 'buy', 
                np.where(self.df[f'{self.strategy}_signal'].diff() < 0, 'sell', 'hold'))       

    
            # trades: flag when a new trade is generated - numeric
            self.df[f'{self.strategy}_new_position'] = np.where(
                self.df[f'{self.strategy}_signal'].diff() > 0, +1, 
                np.where(self.df[f'{self.strategy}_signal'].diff() < 0, -1, 0))  

        elif self.strategy == 'Buy&Hold':
            self.indicator_names = []
            ## Generate Signals
            self.df[f'{self.strategy}_signal'] = 1 # always long
            # self.df.loc[0, f'{self.strategy}_signal'] = 1 # just buys signal at the beginning

            # trades: flag when a new trade is generated - descriptive
            self.df[f'{self.strategy}_trades'] = 'hold'
            self.df.loc[self.df.index[0], f'{self.strategy}_trades'] = 'buy' # only 1 buy trade at the beginning
            self.df.loc[self.df.index[-1], f'{self.strategy}_trades'] = 'sell'

            # trades: flag when a new trade is generated - numeric
            self.df[f'{self.strategy}_new_position'] = 0
            self.df.loc[self.df.index[0], f'{self.strategy}_new_position'] = 1 # only 1 buy trade at the beginning
            self.df.loc[self.df.index[-1], f'{self.strategy}_new_position'] = -1
        # get groupers
        self._calculate_trade_groupers()

        # add stop loss
        if self.stop_loss_bps>0: self._add_stop_loss()
        else: self.df['sl_hit'] = np.nan

        # calculate strategy performance ## TODO check if this is needed
        self._calculate_exec_prices(execution_type=self.execution_type)

        self._get_strat_gross_returns() # get strategy returns time series
        self._calculate_strat_metrics() # calculate strategy perfomance looking at individual trades
        # print(self.df)

    def trading_chart(self, plot_strategy=False, plot_volatility=False):#, indicators_params={}):

        indicator_names = self.indicator_names
        # print(indicator_names, self.df.columns)
        plot_indic_color = ['#CCFFFF', '#FFCCFF', '#536868']

        fig = make_subplots(
            rows=4, 
            cols=1,
            shared_xaxes=True,
            row_heights=[0.5, 0.2, 0.15, 0.15],
            vertical_spacing=0.02,
            specs=[
                [{"secondary_y": True}],
                [{"secondary_y": False}],
                [{"secondary_y": True}],
                [{"secondary_y": False}]
            ]
        )

        fig.add_trace(
            go.Candlestick(
                x=self.df.index,
                open=self.df['open'],
                high=self.df['high'],
                low=self.df['low'],
                close=self.df['close'],
                name='px',
                increasing_line_color= 'green', 
                decreasing_line_color= 'red'
            ),
            row=1, 
            col=1
        )
        # candlestick xaxes
        fig.update_xaxes(
            rangeslider_visible=False,    
            row=1,
            col=1
        )


        # add indicators to candlestick chart
        if len(indicator_names) > 0:
            for indic, color in zip (indicator_names, plot_indic_color):
                # print(indic)
                # indicators requiring sec axis
                if 'rsi' in indic: sec_y=True
                else: sec_y=False

                fig.add_scatter(
                    x=self.df.index, 
                    y=self.df[indic], 
                    name=indic, 
                    marker=dict(color=color),
                    row=1, 
                    col=1,
                    secondary_y=sec_y
                )

        # if plot_volatility:
        #     fig.add_scatter(
        #             x=self.df.index, 
        #             y=self.df['bar_volatility'], 
        #             name=indic, 
        #             marker=dict(color='#6339D9'),
        #             row=2, 
        #             col=1,
        #             secondary_y=True
        #     )

        # add volumes
        # fig.add_scatter(
        #     # x=self.df.index, 
        #     # y=self.df['volume'], 
        #     # name='volume', 
        #     # marker=dict(color=color),
        #     row=2, 
        #     col=1,
        #     # secondary_y=sec_y
        # )

        # fig.add_bar(
        #     x=self.df.index, 
        #     y=self.df['amount_sell'], 
        #     name='amount_sell', 
        #     marker=dict(color='Crimson'),
        #     row=2, 
        #     col=1,
        # )        
        # fig.add_bar(
        #     x=self.df.index, 
        #     y=self.df['amount_buy'], 
        #     name='amount_buy', 

        #     marker=dict(color='LightSkyBlue'),
        #     row=2, 
        #     col=1,
        # )


        if plot_strategy:
            # add buy trades marks
            fig.add_scatter(
                x=self.df.index, 
                y=self.df['close'],#+100, 
                showlegend=False,
                mode='markers',
                marker=dict(
                    size=12,
                    # I want the color to be green if trade is a buy
                    color=(
                        (self.df[f'{self.strategy}_trades'] == 'buy')).astype('int'),
                    colorscale=[[0, 'rgba(255, 0, 0, 0)'], [1, '#B7FFA1']],
                    symbol=5
                ),
                row=1, 
                col=1
            )

            # add sell trades marks
            fig.add_scatter(
                x=self.df.index, 
                y=self.df['close'],#-100, 
                showlegend=False, 
                mode='markers',
                marker=dict(
                    size=12,
                    # I want the color to be red if trade is a sell
                    color=(
                        (self.df[f'{self.strategy}_trades'] == 'sell')).astype('int'),
                    colorscale=[[0, 'rgba(255, 0, 0, 0)'], [1, '#FF7F7F']],
                    symbol=6   
                    ),
                    row=1, 
                    col=1
            )

            # add stop loss
            if self.stop_loss_bps >0:

                fig.add_scatter(
                    x=self.df.index, 
                    y=self.df['close'],#-500, 
                    showlegend=False, 
                    mode='markers',
                    marker=dict(
                        size=12,
                        # I want the color to be red if trade is a sell
                        color=(
                            (self.df['sl_hit'] == 1)).astype('int'),
                        colorscale=[[0, 'rgba(255, 0, 0, 0)'], [1, '#FF7F7F']],
                        symbol=106   
                        ),
                        row=1, 
                        col=1
                )



            # add strategy returns
            fig.add_scatter(
                x=self.df.index,
                y=self.df[f'{self.strategy}_gross_cum_pctg_returns'],
                name='gross_performance',
                row=4,
                col=1
            )

            
            fig.add_scatter(
                x=self.trades_df['liquidated_at'],
                y=self.trades_df['cum_trades_pctg_return'],
                name='net_performance',
                row=4,
                col=1
            )


            # add trades perfomance
            fig.add_scatter(
                x=self.trades_df.index,#['liquidated_at'],
                y=self.trades_df['trades_pctg_return'],
                name='trades_performance',
                mode='markers',
                marker=dict(
                    size=10,
                    color='#4fc3f7 ',
                    # # I want the color to be red if trade is a sell
                    # color=(
                    #     (self.trades_df['direction'] == 1)).astype('int'),
                    # colorscale=[[0, '#FF7F7F'], [1, 'green']],
                    symbol=0  
                    ),
                row=3,
                col=1,
                secondary_y=False
            )

            # add strategy position
            fig.add_scatter(
                x=self.df.index,
                y=self.df[f'{self.strategy}_signal'],
                opacity=0.4,
                name='position',
                mode='lines',
                marker=dict(color=('#ffeded')),
                row=3,
                col=1,
                secondary_y=True
            )



        # update subplots layouts
        fig.update_layout(
            barmode="relative",
            yaxis1=dict(title="Price chart"),
            yaxis2=dict(title=""),
            yaxis3=dict(title="Volume"),
            yaxis4=dict(title="Trade Net Ret"), 
            yaxis5=dict(title="Position"), 
            yaxis6=dict(title="Return"),
        )

        # general layout
        fig.update_layout(
            # width=1200,
            # height=700,
            title=f'<b>{self.strategy} Strategy</b>',
            title_x=.5,
            # yaxis_title='USDT/BTC',
            template="plotly_dark",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(gridcolor='#444'),
            yaxis=dict(gridcolor='#444')
        )



        return fig


    def strategy_metrics(self):
        pass
