import dash
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import data_preprocessing as dp
from datetime import date, datetime, timedelta
import plotly.graph_objs as go
from dash import Input, Output, dcc, html

currencies = ['USDT_BTC', 'BTC_AAVE']
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

app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

def dynamic_strategy_controls(strategy):
    if strategy == 'EMACrossOverLS' or strategy == 'EMACrossOverLO':
        return [
            dbc.Row(
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
            ),

            dbc.Row(
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
            ),
        ]

    elif strategy == 'BollingerBandsLO':
        return [
            dbc.Row(
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
            ),

            dbc.Row(
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
                                {"label": col, "value": col} for col in currencies
                            ],
                            value="USDT_BTC",
                        ),
                    ],
                    width=6
                ),

                dbc.Col(
                    [
                        dbc.Label("Frequency"),
                        dcc.Dropdown(
                            id="data-frequency-variable",
                            options=[
                                {"label": col, "value": col} for col in frequencies
                            ],
                            value="30min",
                        ),
                    ],
                    width=6
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
            [
                dbc.Label("Strategy"),
                dcc.Dropdown(
                    id="strategy-input",
                    options=[
                        {"label": col, "value": col} for col in strategies.keys()
                    ],
                    value="BollingerBandsLO",
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
                dcc.Store(id="chart-data-session", storage_type="session"),
                dbc.Col(controls, md=2),
                dbc.Col(dcc.Graph(id="strategy-graph"), md=10),
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
    return max_date, initial_viz_month, start_date, end_date


# handle display of strategy parameters
@app.callback(
    Output("strategy-parameter-elements", "children"),
    Input("strategy-input", "value")
)
def display_strategy_parameters(strategy):
    elements = [dbc.Label("Strategy parameters")] + dynamic_strategy_controls(strategy)
    return elements


@app.callback(
    Output("chart-data-session", "children"),
    Input("currency-variable", "value"),
    Input("data-frequency-variable", "value"),
    Input("strategy-param-1", "value"),
)
def cache_dataset(pair, start_date, end_date):
    # fill this out with the logic to cache data when the inputs are changed
    # no need to redownload the data simply when strategy parameters change
    # decide what to do when only frequency changes
    pass


@app.callback(
    Output("strategy-graph", "figure"),
    Input("data-frequency-variable", "value"),
    Input("chart-date-picker-range", "start_date"),
    Input("chart-date-picker-range", "end_date"),
)
def make_graph(frequency, param1, param2):
    pass



if __name__ == "__main__":
    app.run_server(debug=True, port=8888)