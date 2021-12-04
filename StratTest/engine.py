from ta.volatility import BollingerBands, AverageTrueRange
from ta.trend import EMAIndicator

import numpy as np
import pandas as pd

import plotly.graph_objects as go
from plotly.subplots import make_subplots


class TradingStrategy():

    def __init__(self, data, frequency, printout=False):
        self.df = data # dataframe with open, high, low, close, volume columns
        self.frequency = frequency
        self.printout = printout


    def resample_data(self):

        ''' Method to be called if the dataframe is at a lower granularity than desired dataset '''
        
        self.df = self.df.resample(self.frequency, label='right').agg( # closing time of candlestick
            {
            'Mid_Price': ['last', 'first', np.max, np.min], 
            # 'volume': np.sum
            }
        )

        self.df.columns = self.df.columns.get_level_values(1)

        self.df['close'] = self.df['last']
        self.df['open'] = self.df['first']
        self.df['high'] = self.df['amax']
        self.df['low'] = self.df['amin']
        # data_resampled['volume'] = data_resampled['sum']
        self.df.index.name = 'datetime'

        self.df = self.df[['open', 'high', 'low', 'close']]
        

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


        if self.printout: print(f'Adding {indicator} with: {params}')


    def _calculate_exec_prices(self, execution_type='current_bar_close', comms_bps=0):
        ''' exec_type can assume values of:
                - next_bar_open: assume entry and exit trades are executed at the next bar open px
                - current_bar_close: assume entry and exit trades are executed at the current bar close px
                - next_bar_worst: TODO, assume trade is executed at the worst px available next bar, high 
                    or low depending on the trade directions         
        '''

        # get positions in the dataframe where indicator generates signals
        open_trades_idx = np.where(self.df[f'{self.strategy}_new_position']==1)[0]
        closing_trades_idx = np.where(self.df[f'{self.strategy}_new_position']==-1)[0]
        between_open_close_idx = np.where(self.df[f'{self.strategy}_signal']!=0)
        # out_market_idx = np.where((self.df[f'{self.strategy}_signal']==0) 
        #     & (self.df[f'{self.strategy}_new_position']!=0))[0]
        print(open_trades_idx)
        print(closing_trades_idx)

        self.df['trade_grouper'] = np.nan
        self.df.loc[self.df.iloc[open_trades_idx].index, 'trade_grouper'] = self.df.iloc[open_trades_idx].index # add grouper at opening
        self.df.loc[self.df.iloc[closing_trades_idx].index, 'trade_grouper'] = self.df.iloc[open_trades_idx[:closing_trades_idx.shape[0]]].index # add grouper at closing
        self.df.loc[self.df.iloc[between_open_close_idx].index, 'trade_grouper'] = self.df.iloc[between_open_close_idx]['trade_grouper'].fillna(method='ffill') # add grouper between


        # TODO: these assume that order is not cancelled between order being triggered and executed
        if execution_type == 'next_bar_open':
            self.df['px_returns_calcs']  = np.where(
                self.df[f'{self.strategy}_new_position']!=0, self.df['open'].shift(-1), self.df['close'])
            self.df['execution_time'] = pd.to_datetime(np.where(self.df[f'{self.strategy}_new_position']!=0, self.df.index.shift(1, freq=self.frequency), pd.NaT))

        elif execution_type == 'current_bar_close':
            self.df['px_returns_calcs'] = self.df['close'].copy()
            self.df['execution_time'] = pd.to_datetime(np.where(self.df[f'{self.strategy}_new_position']!=0, self.df.index, pd.NaT))


        # apply any trading fee after stop loss calculation
        if self.comms_bps != 0:
            self._add_transaction_costs()


    def _get_strat_gross_returns(self):
        ''' 
        Get strategy gross log returns time series, inclusive of stop losses and execution assumptions (ie current or next close), 
        but without accounting for any trading costs
        '''

        # get gross log cumulative returns over time
        self.df['gross_log_returns'] = np.log(self.df['px_returns_calcs']) - np.log(self.df['px_returns_calcs'].shift(1))

        self.df[f'{self.strategy}_gross_log_returns'] = self.df['gross_log_returns'] * self.df[f'{self.strategy}_signal'] # accounts for long short

        self.df[f'{self.strategy}_gross_cum_log_returns'] = np.exp(self.df[f'{self.strategy}_gross_log_returns'].cumsum()) # cumulative gross performance when in


    def _calculate_strat_metrics(self):

        # get individual trades performances
        self.trades_df = self.df.groupby('trade_grouper').agg(
            entry_price=('execution_price', 'first'), 
            exit_price=('execution_price', 'last'), 
            trade_len=('trade_grouper', 'count'),
            direction=('EMACrossOverLO_new_position', 'first'),
            liquidated_at=('execution_time', 'last')
        )

        self.trades_df['trades_log_return'] = np.log(self.trades_df['exit_price']) - np.log(self.trades_df['entry_price'])
        self.trades_df['cum_trades_log_return'] = self.trades_df['trades_log_return'].cumsum()

        self.trades_df['trades_pctg_return'] = np.exp(self.trades_df['trades_log_return']) - 1
        self.trades_df['cum_trades_pctg_return'] = np.exp(self.trades_df['cum_trades_log_return']) - 1

        self.cum_return = f"{self.trades_df['cum_trades_pctg_return'][-1]:.2%}"


    def _add_stop_losses(self, stop_loss):

        # scenario where no stop loss is present, invested position is the same as the signal output
        # keep this column for sanity check later
        # self.df['_new_position'] = self.df[f'{self.strategy}_new_position'].copy()
        # self.df['_trades'] = self.df[f'{self.strategy}_trades'].copy()
        # self.df['_signal'] = self.df[f'{self.strategy}_signal'].copy()


        # col to keep track of stop loss trigger
        self.df['sl_trigger'] = np.nan
        self.df['sl_hit'] = 0
        self.df['sl_trade'] = np.nan

        # all_trades_list = []
        for name, sub_df in self.df.groupby(by='trade_grouper'):

            entry_price = self.df[self.df.index==name]['px_returns_calcs'].values[0]
            direction = self.df[self.df.index==name][f'{self.strategy}_new_position'].values[0]

            # check for stop losses before any backtesting
            if direction > 0:

                sl_price = entry_price * (1 - stop_loss)
                sub_df['sl_trigger'] = sl_price
                self.df.loc[sub_df.index, 'sl_trigger'] = sl_price

                if (sub_df['sl_trigger'] < sub_df['low']).sum() == sub_df.shape[0]:
                    if self.print_trades: print(f'Long ({direction}) position held until signal reversed')
                    
                else:
                    sl_trigger_time = sub_df[~(sub_df['sl_trigger'] < sub_df['low'])].index[0] # when stop loss was triggered
                    sl_affected_range = sub_df[sub_df.index>=sl_trigger_time].index # all the datapoints subsequently affected by stop loss

                    #self.df.loc[sl_trigger_time, f'{self.strategy}_new_position'] = 0 # create exit point when sl is hit
                    #self.df.loc[sl_trigger_time, f'{self.strategy}_trades'] = "hold" # create exit point when sl is hit
                    self.df.loc[sl_trigger_time, 'sl_hit'] = -1 # flag stop loss being hit
                    self.df.loc[sl_trigger_time, 'sl_trade'] = "stop_sell" # sl trade type
                    self.df.loc[sl_affected_range, f'{self.strategy}_signal'] = 0 # turn signal to 0 - out of market
                    
                    if self.print_trades: print(f'Stop loss triggered - closing long ({direction}) position')

            elif direction < 0:

                sl_price = entry_price * (1 + stop_loss)
                sub_df['sl_trigger'] =  sl_price
                self.df.loc[sub_df.index, 'sl_trigger'] = sl_price

                if (sub_df['sl_trigger'] > sub_df['high']).sum() == sub_df.shape[0]:
                    if self.print_trades: print(f'Short ({direction}) position held until signal reversed')

                else:
                    sl_trigger_time = sub_df[~(sub_df['sl_trigger'] > sub_df['high'])].index[0] # when stop loss was triggered
                    sl_affected_range = sub_df[sub_df.index>=sl_trigger_time].index  # all the datapoints subsequently affected by stop loss

                    #self.df.loc[sl_trigger_time, f'{self.strategy}_new_position'] = 0 # create exit point when sl is hit
                    #self.df.loc[sl_trigger_time, f'{self.strategy}_trades'] = "hold" # create exit point when sl is hit
                    self.df.loc[sl_trigger_time, 'sl_hit'] = +1 # flag stop loss being hit
                    self.df.loc[sl_trigger_time, 'sl_trade'] = "stop_buy" # sl trade type
                    self.df.loc[sl_affected_range, f'{self.strategy}_signal'] = 0 # turn signal to 0 - out of market
                    
                    if self.print_trades: print(f'Stop loss triggered - closing short ({direction}) position')

        # recalculate performance with stop losses
        self._calculate_exec_prices(self.execution_type)


    def _add_transaction_costs(self):
        '''
        comms_bps: float, execution cost in basis points
        '''
        self.comms_pcgt = self.comms_bps/10000

        if self.stop_loss>0: 
            self.df['number_transaction'] = self.df[f'{self.strategy}_new_position'].abs() + self.df['sl_hit'].abs()
        else:
            self.df['number_transaction'] = self.df[f'{self.strategy}_new_position'].abs()
            
        # self.df['total_comms_%'] = self.comms_pcgt * self.df['number_transaction']

        # recalculate prices where a new position occurs. Increase price when buying and decrease when selling (+)
        self.df['execution_price'] = np.where(
            self.df[f'{self.strategy}_new_position']!=0, 
            self.df['px_returns_calcs'] * (1 + (self.comms_pcgt * self.df[f'{self.strategy}_new_position'])),
            np.nan
        )


    def add_strategy(self, strategy, stop_loss=0, comms_bps=0, execution_type='next_bar_open', print_trades=False, **indicators):

        self.strategy = strategy
        self.execution_type = execution_type ### self.execution_type
        self.stop_loss = stop_loss
        self.comms_bps = comms_bps
        self.print_trades = print_trades
        # transform basis points commission in percentage
        

        if self.strategy == 'EMACrossOverLS':

            self.short_ema = f"ema_{indicators['short_ema']}"
            self.long_ema = f"ema_{indicators['long_ema']}"

            self.add_indicator('EMAIndicator', window=indicators['short_ema'])
            self.add_indicator('EMAIndicator', window=indicators['long_ema'])

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

            self.short_ema = f"ema_{indicators['short_ema']}"
            self.long_ema = f"ema_{indicators['long_ema']}"

            self.add_indicator('EMAIndicator', window=indicators['short_ema'])
            self.add_indicator('EMAIndicator', window=indicators['long_ema'])

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


        # calculate strategy performance ## TODO check if this is needed
        self._calculate_exec_prices(execution_type=self.execution_type)

        # # add stop loss
        # if stop_loss>0: self._add_stop_losses(self.stop_loss)

        # # add transaction costs
        # if comms_bps!=0: 
        #     self._add_transaction_costs(self.comms_bps)

        self._get_strat_gross_returns() # get strategy returns time series
        self._calculate_strat_metrics() # calculate strategy perfomance looking at individual trades


    def trading_chart(self, plot_strategy=False, **indicators):

        indicator_names = indicators.values()
        plot_indic_color = ['#CCFFFF', '#FFCCFF']

        fig = make_subplots(
            rows=3, 
            cols=1,
            shared_xaxes=True,
            row_heights=[0.2, 0.6, 0.2],
            vertical_spacing=0.02,
            specs=[
                [{"secondary_y": True}],
                [{"secondary_y": False}],
                [{"secondary_y": False}],
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
            row=2, 
            col=1
        )
        # candlestick xaxes
        fig.update_xaxes(rangeslider_visible=False,    row=2,
            col=1)


        # add indicators to candlestick chart
        if len(indicator_names) > 0:
            for indic, color in zip (indicator_names, plot_indic_color):
                fig.add_scatter(
                    x=self.df.index, 
                    y=self.df[indic], 
                    name=indic, 
                    marker=dict(color=color),
                    row=2, 
                    col=1
                )

        if plot_strategy:
            # add buy trades marks
            fig.add_scatter(
                x=self.df.index, 
                y=self.df['close']+100, 
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
                row=2, 
                col=1
            )

            # add sell trades marks
            fig.add_scatter(
                x=self.df.index, 
                y=self.df['close']-100, 
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
                    row=2, 
                    col=1
            )

            # add stop loss
            if self.stop_loss >0:
                fig.add_scatter(
                    x=self.df.index, 
                    y=self.df['close']+500, 
                    showlegend=False, 
                    mode='markers',
                    marker=dict(
                        size=12,
                        # I want the color to be red if trade is a sell
                        color=(
                            (self.df['sl_hit'] == 1)).astype('int'),
                        colorscale=[[0, 'rgba(255, 0, 0, 0)'], [1, '#B7FFA1']],
                        symbol=105   
                        ),
                        row=2, 
                        col=1
                )

                fig.add_scatter(
                    x=self.df.index, 
                    y=self.df['close']-500, 
                    showlegend=False, 
                    mode='markers',
                    marker=dict(
                        size=12,
                        # I want the color to be red if trade is a sell
                        color=(
                            (self.df['sl_hit'] == -1)).astype('int'),
                        colorscale=[[0, 'rgba(255, 0, 0, 0)'], [1, '#FF7F7F']],
                        symbol=106   
                        ),
                        row=2, 
                        col=1
                )



            # add strategy returns
            fig.add_scatter(
                x=self.df.index,
                y=self.df[f'{self.strategy}_gross_cum_log_returns'],
                name='gross_performance',
                row=3,
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
                row=1,
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
                row=1,
                col=1,
                secondary_y=True
            )


        # general layout
        fig.update_layout(
            width=1200,
            height=700,
            title=f'<b>{self.strategy} Strategy</b>',
            title_x=.5,
            yaxis_title='USDT/BTC',
            template="plotly_dark",
            # plot_bgcolor='rgb(10,10,10)'
        )

        return fig


    def strategy_metrics(self):
        pass
