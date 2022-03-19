from tracemalloc import start
import dash
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import data_preprocessing as dp
from datetime import date, datetime, timedelta
import plotly.graph_objs as go
from dash import Input, Output, dcc, html
from StratTest.engine import TradingStrategy

currencies = ['USDT_BTC', 'BTC_AAVE']
# frequencies = [timedelta(minutes=1), timedelta(minutes=15), 
#     timedelta(minutes=30), timedelta(minutes=60), timedelta(minutes=120), 
#     timedelta(minutes=240), timedelta(days=1)]
frequencies = ['1min', '15min', '30min', '60min', '120min', '240min', '1day']
strategies = {
    'EMACrossOverLS':{
        'ids':['short-ema-count', 'long-ema-count'],
        'short_ema':np.arange(1,101),
        'long_ema':np.arange(1,201)
    }, 
    'EMACrossOverLO':{
        'ids':['short-ema-count', 'long-ema-count'],
        'short_ema':np.arange(1,101),
        'long_ema':np.arange(1,201)
    },
    'BollingerBandsLO':{
        'ids':['boll-window-count', 'boll-window-dev-count'],
        'window':np.arange(1,101),
        'window_dev':np.arange(1,6)
    }, 
    'MultiIndic':{
        '':''
    }
}

app = dash.Dash(external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True)

def dynamic_strategy_controls(strategy):
    if strategy == 'EMACrossOverLS' or strategy == 'EMACrossOverLO':
        return [
            dbc.Row(
                [
                    dbc.Col(
                        [
                        dbc.Label("Short EMA"),
                        dbc.Input(
                            id="strategy-param-1", 
                            type="number", 
                            min=strategies[strategy]['short_ema'].min(), 
                            max=strategies[strategy]['short_ema'].max(), 
                            value=15
                        ),
                        ]
                    )
                ]
            ),

            dbc.Row(
                [
                    dbc.Col(
                        [
                        dbc.Label("Short EMA"),
                        dbc.Input(
                            id="strategy-param-2", 
                            type="number", 
                            min=strategies[strategy]['long_ema'].min(), 
                            max=strategies[strategy]['long_ema'].max(), 
                            value=30
                        ),
                        ]
                    )
                ]
            ),
        ]

    elif strategy == 'BollingerBandsLO':
        return [
            dbc.Row(
                [
                    dbc.Col(
                        [
                        dbc.Label("MA window"),
                        dbc.Input(
                            id="strategy-param-1", 
                            type="number", 
                            min=strategies[strategy]['window'].min(), 
                            max=strategies[strategy]['window'].max(), 
                            value=15
                        ),
                        ]
                    )
                ]
            ),

            dbc.Row(
                [
                    dbc.Col(
                        [
                        dbc.Label("Standard deviation factor"),
                        dbc.Input(
                            id="strategy-param-2", 
                            type="number", 
                            min=strategies[strategy]['window_dev'].min(), 
                            max=strategies[strategy]['window_dev'].max(), 
                            value=1
                        ),
                        ]
                    )
                ]
            ),
        ]


    elif strategy == 'MultiIndic':
        return []


controls = dbc.Card(
    [

        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Pair"),
                        dcc.Dropdown(
                            id="currency-variable",
                            options=[
                                {"label": cur, "value": cur} for cur in currencies
                            ],
                            value="USDT_BTC",
                        ),
                    ],
                ),
            ]
        ),

        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Frequency"),
                        dcc.Dropdown(
                            id="data-frequency-variable",
                            options=[
                                {"label": freq, "value": freq} for freq in frequencies
                            ],
                            value="30min",
                        ),
                    ],
                ),  
            ]
        ),

        html.Br(),

        dbc.Row(
            [
                dbc.Label("Select date range"),
                dcc.DatePickerRange(
                    id="chart-date-picker-range",
                    display_format='MMM Do, YY',
                    min_date_allowed=date(2021, 1, 1),
                ),
            ]
        ),

        html.Br(),

        dbc.Row(
            dbc.Col(
                [
                    dbc.Label("Strategy"),
                    dcc.Dropdown(
                        id="strategy-input",
                        options=[
                            {"label": col, "value": col} for col in strategies.keys()
                        ],
                        value="BollingerBandsLO",
                    ),
                ],
            )
            ),

        html.Br(),

        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Transaction Cost"),
                        dbc.Input(
                            id="strategy-transaction-cost", 
                            type="number", 
                            min=0, 
                            max=100, 
                            value=25
                    ),
                    ],
                ),
            ]
        ),

        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Stop Loss"),
                        dbc.Input(
                            id="strategy-stop-loss", 
                            type="number", 
                            min=0, 
                            max=10000, 
                            value=0
                    ),
                    ],
                ),  
            ]
        ),

        html.Br(),

        dbc.Row(
            id="strategy-parameter-elements"
        ),
    ],
    body=True,
)


app.layout = dbc.Container(
    [
        html.H1("RL Trader Charting Tool"),
        html.Hr(),
        dbc.Row(
            [
                dcc.Store(id="chart-data-session", storage_type="memory"),
                dbc.Col(controls, width=2, style={'height':'80vh'}),
                dbc.Col(
                    dbc.Card(
                        dcc.Graph(
                            id="strategy-graph",
                            figure={
                                'layout': go.Layout(
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                height=800
                                )
                            }
                        ),
                        body=True,
                        
                    ),
                    md=10,
                ),
            ],
            align="center",
            style={'height':'80vh'}
        ),
    ],
    fluid=True,
    id="outer-app-container"
)

# handle dynamic start and end date
@app.callback(
    Output("chart-date-picker-range", "max_date_allowed"),
    Output("chart-date-picker-range", "initial_visible_month"),
    Output("chart-date-picker-range", "start_date"),
    Output("chart-date-picker-range", "end_date"),
    Input("outer-app-container", "children")
)
def dynamic_start_end_dates(container_refresh):
    max_date = datetime.today().date()
    initial_viz_month = datetime.today() - timedelta(90)
    start_date = datetime.today().date()- timedelta(90)
    end_date = datetime.today().date() - timedelta(1)
    end_date = pd.to_datetime('2022-01-12').date()
    return max_date, initial_viz_month, start_date, end_date


# handle display of strategy parameters
@app.callback(
    Output("strategy-parameter-elements", "children"),
    Input("strategy-input", "value")
)
def display_strategy_parameters(strategy):
    elements = dbc.Col([dbc.Label("Strategy parameters")]+ dynamic_strategy_controls(strategy))
    return elements


@app.callback(
    Output("chart-data-session", "data"),
    Input("currency-variable", "value"),
    Input("chart-date-picker-range", "start_date"),
    Input("chart-date-picker-range", "end_date"),
)
def cache_dataset(pair, start_date, end_date):
    # fill this out with the logic to cache data when the inputs are changed
    # no need to redownload the data simply when strategy parameters change
    # decide what to do when only frequency changes
    print(start_date, end_date, pair)
    df_data = dp.import_data(
        pair, 
        start_date, 
        end_date, 
        include_trades=False, 
        frequency=timedelta(seconds=60), 
        depth=100
    )

    print(df_data.head())
    return df_data.reset_index().to_dict('records')
    # return dash.no_update

@app.callback(
    Output("strategy-graph", "figure"),
    Input("chart-data-session", "data"),
    Input("strategy-input", "value"),
    Input("data-frequency-variable", "value"),
    Input("strategy-transaction-cost", "value"),
    Input("strategy-stop-loss", "value"),
    Input("strategy-param-1", "value"),
    Input("strategy-param-2", "value"),
    # Input("data-frequency-variable", "value"),
    # Input("chart-date-picker-range", "start_date"),
    # Input("chart-date-picker-range", "end_date"),
    prevent_initial_call=True
)
def make_graph(cached_data, strategy, frequency, transaction_cost, stop_loss, param1, param2):
    
    # load cached data
    data = pd.DataFrame(cached_data)
    data['Datetime'] = pd.to_datetime(data['Datetime'])
    data = data.set_index('Datetime')
    print(data.iloc[1])
    # convert frequency from timedelta to seconds
    resample_freq = pd.to_timedelta(frequency)

    trading_strategy = TradingStrategy(data, frequency=resample_freq)
    trading_strategy.add_strategy(
        strategy, 
        execution_type='current_bar_close',#'next_bar_open', 'current_bar_close, 'cheat_previous_close
        stop_loss_bps=stop_loss,
        comms_bps=transaction_cost,
        indicators_params=dict(    
            # short_ema=short_ema,
            # long_ema=long_ema
            window=param1, 
            window_dev=param2
    ),
    print_trades=False
)
    fig = trading_strategy.trading_chart(plot_strategy=True)
    return fig



if __name__ == "__main__":
    app.run_server(debug=True, port=8888)