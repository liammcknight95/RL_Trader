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


    def _calculate_performance(self, execution_type):
        ''' exec_type can assume values of:
                - next_bar_open: assume entry and exit trades are executed at the next bar open px
                - current_bar_close: assume entry and exit trades are executed at the current bar close px
                - next_bar_worst: TODO, assume trade is executed at the worst px available next bar, high 
                    or low depending on the trade directions         
        '''

        # get positions in the dataframe where indicator generates signals
        open_trades_idx = np.where(self.df[f'{self.strategy}_new_position']!=0)[0]
        # -2 because of shape is n rows and df is 0 indexed and because we do + 1 later - avoid out of bound error
        closing_trades_idx = np.append(open_trades_idx, self.df.shape[0]-2)[1:] 

        self.df['trade_grouper'] = np.nan
        self.df.loc[self.df.iloc[open_trades_idx].index, 'trade_grouper'] = self.df.iloc[open_trades_idx].index
        self.df['trade_grouper'] = self.df['trade_grouper'].fillna(method='ffill')


        if execution_type is None:
            # skip recalculation pf px_returns_calcs
            pass
        
        else:
            if execution_type == 'next_bar_open':
                self.df['px_returns_calcs']  = np.where(
                    self.df['EMACrossOver_new_position']!=0, self.df['open'].shift(-1), self.df['close'])

                self.df['returns'] = np.log(self.df['px_returns_calcs']) - np.log(self.df['px_returns_calcs'].shift(1))

            elif execution_type == 'current_bar_close':
                self.df['px_returns_calcs'] = self.df['close'].copy()

                self.df['returns'] = np.log(self.df['px_returns_calcs']) - np.log(self.df['px_returns_calcs'].shift(1))



            self.df[f'{self.strategy}_returns'] = self.df['returns'] * self.df[f'{self.strategy}_signal']

            self.df[f'{self.strategy}_trade_performance'] = self.df.groupby('trade_grouper')[['EMACrossOver_returns']].transform(np.sum)

            self.df[f'{self.strategy}_cum_performance'] = np.exp(self.df[f'{self.strategy}_returns'].cumsum())
            # self.df[f'{self.strategy}_cash'] = self.df[f'{self.strategy}_cum_performance'] * initial_cash

            # np.exp(self.df['returns'].cumsum()).plot(figsize=(8,4), legend=True) # reverse log returns to prices
            # self.df[f'{self.strategy}_cum_performance'].plot(legend=True)


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
        self._calculate_performance(self.execution_type)


    def _add_transaction_costs(self, comms_bps):
        '''
        commission: float, execution cost in basis points
        '''

        self.df['number_transaction'] = self.df[f'{self.strategy}_new_position'].abs() + self.df['sl_hit'].abs()
        self.df['total_comms'] = self.comms_pcgt * self.df['number_transaction']

        # add column to preserve original returns for checks
        self.df['returns_before_tr'] = self.df['returns'].copy()

        self.df['returns'] = self.df['returns'] - self.df['total_comms']

        # recalculate performance with stop losses
        self._calculate_performance(None)


    def add_strategy(self, strategy, stop_loss=0, comms_bps=0, execution_type='next_bar_open', print_trades=False, **indicators):

        self.strategy = strategy
        self.execution_type = execution_type ### self.execution_type
        self.stop_loss = stop_loss
        self.comms_bps = comms_bps
        self.print_trades = print_trades
        # transform basis points commission in percentage
        self.comms_pcgt = comms_bps/10000

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

        # calculate strategy performance ## TODO check if this is needed
        self._calculate_performance(execution_type=self.execution_type)

        # add stop loss
        if stop_loss>0: self._add_stop_losses(self.stop_loss)

        # add transaction costs
        if comms_bps!=0: 
            self._add_transaction_costs(self.comms_bps)


    def trading_chart(self, plot_strategy=False, **indicators):

        indicator_names = indicators.values()
        plot_indic_color = ['#CCFFFF', '#FFCCFF']

        fig = make_subplots(
            rows=3, 
            cols=1,
            shared_xaxes=True,
            row_heights=[0.2, 0.6, 0.2],
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
                y=self.df[f'{self.strategy}_cum_performance'],
                name='cum_performance',
                row=3,
                col=1
            )

            # add trades perfomance
            fig.add_scatter(
                x=self.df.index,
                y=self.df[f'{self.strategy}_trade_performance'],
                name='trades_performance',
                mode='markers',
                marker=dict(
                    size=10,
                    # I want the color to be red if trade is a sell
                    color=(
                        (self.df['number_transaction'] > 0)).astype('int'),
                    colorscale=[[0, 'rgba(255, 0, 0, 0)'], [1, '#1184e8']],
                    symbol=0   
                    ),
                row=1,
                col=1
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



## trading bot
def tr(data):
    data['previous_close'] = data['close'].shift(1)
    data['high-low'] = abs(data['high'] - data['low'])
    data['high-pc'] = abs(data['high'] - data['previous_close'])
    data['low-pc'] = abs(data['low'] - data['previous_close'])

    tr = data[['high-low', 'high-pc', 'low-pc']].max(axis=1)

    return tr

def atr(data, period):
    data['tr'] = tr(data)
    atr = data['tr'].rolling(period).mean()

    return atr

def supertrend(df, period=7, atr_multiplier=3):
    hl2 = (df['high'] + df['low']) / 2
    df['atr'] = atr(df, period)
    df['upperband'] = hl2 + (atr_multiplier * df['atr'])
    df['lowerband'] = hl2 - (atr_multiplier * df['atr'])
    df['in_uptrend'] = True

    for current in range(1, len(df.index)):
        previous = current - 1

        if df['close'][current] > df['upperband'][previous]:
            df['in_uptrend'][current] = True
        elif df['close'][current] < df['lowerband'][previous]:
            df['in_uptrend'][current] = False
        else:
            df['in_uptrend'][current] = df['in_uptrend'][previous]

            if df['in_uptrend'][current] and df['lowerband'][current] < df['lowerband'][previous]:
                df['lowerband'][current] = df['lowerband'][previous]

            if not df['in_uptrend'][current] and df['upperband'][current] > df['upperband'][previous]:
                df['upperband'][current] = df['upperband'][previous]
        
    return df


in_position = False

def check_buy_sell_signals(df):
    global in_position

    print("checking for buy and sell signals")
    print(df.tail(5))
    last_row_index = len(df.index) - 1
    previous_row_index = last_row_index - 1

    if not df['in_uptrend'][previous_row_index] and df['in_uptrend'][last_row_index]:
        print("changed to uptrend, buy")
        if not in_position:
            order = exchange.create_market_buy_order('ETH/USD', 0.05)
            print(order)
            in_position = True
        else:
            print("already in position, nothing to do")
    
    if df['in_uptrend'][previous_row_index] and not df['in_uptrend'][last_row_index]:
        if in_position:
            print("changed to downtrend, sell")
            order = exchange.create_market_sell_order('ETH/USD', 0.05)
            print(order)
            in_position = False
        else:
            print("You aren't in position, nothing to sell")

def run_bot():
    print(f"Fetching new bars for {datetime.now().isoformat()}")
    bars = exchange.fetch_ohlcv('ETH/USDT', timeframe='1m', limit=100)
    df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    supertrend_data = supertrend(df)
    
    check_buy_sell_signals(supertrend_data)