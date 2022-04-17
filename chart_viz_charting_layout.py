import dash_bootstrap_components as dbc
from dash import dcc, html
from chart_viz_config import strategies, currencies, frequencies
from datetime import date
import plotly.graph_objects as go

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
                            value=15,
                            persistence=True
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
                            value=30,
                            persistence=True
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
                            value=15,
                            persistence=True
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
                            value=1,
                            persistence=True
                        ),
                        ]
                    )
                ]
            ),
        ]


    elif strategy == 'MultiIndic':
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
                            value=15,
                            persistence=True
                        ),
                        ]
                    )
                ],
                style={'display': 'none'}
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
                            value=30,
                            persistence=True
                        ),
                        ]
                    )
                ],
                style={'display': 'none'}
            ),
        ]

    elif strategy == 'Buy&Hold':
        return [
            dbc.Row(
                [
                    dbc.Col(
                        [
                        dbc.Input(
                            id="strategy-param-1",
                            persistence=True
                        ),
                        ]
                    )
                ],
                style={'display': 'none'}
            ),

            dbc.Row(
                [
                    dbc.Col(
                        [
                        dbc.Input(
                            id="strategy-param-2",
                            persistence=True
                        ),
                        ]
                    )
                ],
                style={'display': 'none'}
            ),
        ]

controls = dbc.Card(
    [

        dbc.Row(
            html.P('Controls', style={'fontSize':'22px', 'fontWeight':'bold'})
        ),

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
                            persistence=True
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
                            persistence=True
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
                    persistence=True
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
                        persistence=True
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
                            value=25,
                            persistence=True
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
                            value=0,
                            persistence=True
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
    style={'minHeight':'800px', 'height':'100%'},
    body=True,
)

charting_page_layout = dbc.Container(
    [
        html.Br(),
        dbc.Row(
            [
                html.Div(id="chart-data-store-ref", style={'display': 'none'}),
                dbc.Col(controls, width=2),
                dbc.Col(
                    dbc.Card(
                        dcc.Graph(
                            id="strategy-graph",
                            figure={
                                'layout': go.Layout(
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                height=770
                                )
                            }
                        ),
                        style={'minHeight':'800px', 'height':'100%'},
                        body=True,
                        
                    ),
                    md=10,
                ),
            ],
        ),
    ],
    fluid=True,
    id="outer-app-container"
)