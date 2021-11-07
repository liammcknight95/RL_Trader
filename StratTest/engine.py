from ta.volatility import BollingerBands, AverageTrueRange
from ta.trend import EMAIndicator

import numpy as np
import pandas as pd

import plotly.graph_objects as go
from plotly.subplots import make_subplots


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



    def _calculate_performance(self, exec_type='next_bar_open'):
        ''' exec_type can assume values of:
                - next_bar_open: assume entry and exit trades are executed at the next bar open px
                - current_bar_close: assume entry and exit trades are executed at the current bar close px
                - next_bar_worst: TODO, assume trade is executed at the worst px available next bar, high 
                    or low depending on the trade directions         
        '''
        if exec_type == 'next_bar_open':
            self.df['potential_entry_price'] = self.df['open'].shift(-1) # assume entry trade is executed at the next bar open
            self.df['potential_closing_price'] = self.df['open'].shift(-1) # assume closing is executed at the next bar open


        elif exec_type == 'current_bar_close':
            self.df['px_returns_calcs'] = self.df['close'].copy()
            self.df['returns'] = np.log(self.df['close']) - np.log(self.df['close'].shift(1))

        self.df[f'{self.strategy}_returns'] = self.df['returns'] * self.df[f'{self.strategy}_signal']

        self.df[f'{self.strategy}_cum_performance'] = np.exp(self.df[f'{self.strategy}_returns'].cumsum())
        # self.df[f'{self.strategy}_cash'] = self.df[f'{self.strategy}_cum_performance'] * initial_cash

        # np.exp(self.df['returns'].cumsum()).plot(figsize=(8,4), legend=True) # reverse log returns to prices
        # self.df[f'{self.strategy}_cum_performance'].plot(legend=True)


    def _add_stop_losses():
        pass


    def add_strategy(self, strategy, **indicators):

        self.strategy = strategy

        if self.strategy == 'EMACrossOver':

            self.short_ema = indicators['short_ema']
            self.long_ema = indicators['long_ema']

            ## Generate Signals
            # signal: tiemseries of +1 when long, -1 when short, 0 when neutral
            self.df[f'{self.strategy}_signal'] = np.where(
                self.df[self.short_ema] > self.df[indicators['long_ema']], 1, 
                np.where(self.df[self.short_ema] < self.df[indicators['long_ema']], -1, 0))

            # trades: flag when a new trade is generated - descriptive
            self.df[f'{self.strategy}_trades'] = np.where(
                self.df[f'{self.strategy}_signal'].diff() > 0, 'buy', 
                np.where(self.df[f'{self.strategy}_signal'].diff() < 0, 'sell', 'hold'))

            # trades: flag when a new trade is generated - numeric
            self.df[f'{self.strategy}_new_position'] = np.where(
                self.df[f'{self.strategy}_signal'].diff() > 0, +1, 
                np.where(self.df[f'{self.strategy}_signal'].diff() < 0, -1, 0))

        # calculate strategy performance
        self._calculate_performance(exec_type='current_bar_close')

        # add stop loss

    
    def trading_chart(self, plot_strategy=False, **indicators):

        indicator_names = indicators.values()
        plot_indic_color = ['#CCFFFF', '#FFCCFF']

        fig = make_subplots(
            rows=2, 
            cols=1,
            shared_xaxes=True,
            row_heights=[0.2, 0.8],
            vertical_spacing=0.02
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

            # add strategy returns
            fig.add_scatter(
                x=self.df.index,
                y=self.df[f'{self.strategy}_cum_performance'],
                name='cum_performance',
                row=1,
                col=1
            )

        # general layout
        fig.update_layout(
            width=1200,
            height=500,
            title=f'<b>{self.strategy} Strategy</b>',
            title_x=.5,
            yaxis_title='USDT/BTC',
            template="plotly_dark",
            # plot_bgcolor='rgb(10,10,10)'
        )

        return fig