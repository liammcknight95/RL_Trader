import plotly_express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def live_bot_strategy(data_bars, data_orders=None, params=[], theme='dark'):

    fig = make_subplots(
        rows=2, 
        cols=1,
        shared_xaxes=True,
        row_heights=[0.8, 0.2],
        vertical_spacing=0.02,
        specs=[
            [{"secondary_y": True}],
            [{"secondary_y": True}]
        ]
    )

    fig.add_trace(
        go.Candlestick(
            x=data_bars['bar_time'],
            open=data_bars['bar_open'],
            high=data_bars['bar_high'],
            low=data_bars['bar_low'],
            close=data_bars['bar_close'],
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

    plot_param_color = ['#CCFFFF', '#FFCCFF', '#536868']
    for param, param_color in zip(params, plot_param_color):
        # need to pass the actual indicators here
        fig.add_scatter(
            x=data_bars['bar_time'], 
            y=data_bars[param], 
            name=param, 
            marker=dict(color=param_color),
            row=1, 
            col=1,
            secondary_y=False
        )


    # add signal
    fig.add_scatter(
        x=data_bars['bar_time'], 
        y=data_bars['bar_strategy_signal'], 
        name='signal', 
        # marker=dict(color=color),
        row=2, 
        col=1,
        secondary_y=False
    )
    
    # add buys and sell
    if data_orders[data_orders['order_direction']=='buy'].shape[0] > 0:
        # add buy trades marks
        fig.add_scatter(
            x=data_orders['order_timestamp_placed'], 
            y=data_orders['order_price_filled'], 
            showlegend=False,
            mode='markers',
            marker=dict(
                size=12,
                # I want the color to be green if trade is a buy
                color=(
                    (data_orders['order_direction'] == 'buy')).astype('int'),
                colorscale=[[0, 'rgba(255, 0, 0, 0)'], [1, '#B7FFA1']],
                symbol=5
            ),
            row=1, 
            col=1
        )

    if data_orders[data_orders['order_direction']=='sell'].shape[0] > 0:

        # add sell trades marks
        fig.add_scatter(
            x=data_orders['order_timestamp_placed'], 
            y=data_orders['order_price_filled'], 
            showlegend=False, 
            mode='markers',
            marker=dict(
                size=12,
                # I want the color to be red if trade is a sell
                color=(
                    (data_orders['order_direction'] == 'sell')).astype('int'),
                colorscale=[[0, 'rgba(255, 0, 0, 0)'], [1, '#FF7F7F']],
                symbol=6   
                ),
                row=1, 
                col=1
        )


    if theme=='dark':
        # general layout
        fig.update_layout(
            # width=1200,
            # height=700,
            title=f'<b>Strategy</b>',
            title_x=.5,
            # yaxis_title='USDT/BTC',
            template="plotly_dark",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(zerolinecolor='#444', gridcolor='#444'),
            yaxis=dict(zerolinecolor='#444', gridcolor='#444')
        )
    elif theme=='light':
        #
        fig.update_layout(
            title=f'<b>Strategy</b>',
            title_x=.5,
            # xaxis=dict(zerolinecolor='#444', gridcolor='#444'),
            # yaxis=dict(zerolinecolor='#444', gridcolor='#444')
        )

    return fig
