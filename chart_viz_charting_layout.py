from pydoc import classname
import dash_bootstrap_components as dbc
from dash import dcc, html
from chart_viz_config import strategies, currencies, frequencies
from datetime import date
import plotly.graph_objects as go

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
                        id="strategy-backtest-strategy",
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
    body=True,
    # style={'overflowY':'scroll'},
    # style={'minHeight':'92vh', 'maxHeight':'92vh'},
    className='h-100'
)


strategy_stats = dbc.Row(
    [
        dbc.Col(
            dbc.Card(
                [
                    dbc.Label("Gross Return"),
                    html.P(
                        id='strategy-gross-return-stat', 
                    )
                ],
                className='h-100 text-center stats-styling',
                body=True
            ),
            width=2
        ),
        dbc.Col(
            dbc.Card(
                [
                    dbc.Label("Net Return"),
                    html.P(id='strategy-net-return-stat')
                ],
                className='h-100 text-center stats-styling',
                body=True
            ),
            width=2
        ),
        dbc.Col(
            dbc.Card(
                [
                    dbc.Label("Trades Number"),
                    html.P(id='strategy-trades-number-stat')
                ],
                className='h-100 text-center stats-styling',
                body=True
            ),
            width=2
        ),
        dbc.Col(
            dbc.Card(
                [
                    dbc.Label("Max Drawdown"),
                    html.P(id='strategy-sharpe-ratio-stat')
                ],
                className='h-100 text-center stats-styling',
                body=True
            ),
            width=2
        ),
        dbc.Col(
            dbc.Card(
                [
                    dbc.Label("Net Returns by Trade Lenght"),
                    dcc.Graph(
                        id="strategy-single-trades",
                        figure={
                            'layout': go.Layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            xaxis=dict(gridcolor='#444'),
                            yaxis=dict(gridcolor='#444'),
                            height=80
                            )
                        },
                        config={
                            'displayModeBar': False
                        }
                    ),
                ],
                className='h-100 text-center stats-styling',
                body=True
            ),
            width=4
        ),
    ],
    # style={'minHeight':'5vh', 'maxHeight':'10vh'}
)

charting_page_layout = dbc.Container(
    [
        html.Br(),
        dbc.Row(
            [
                html.Div(id="chart-data-store-ref", style={'display': 'none'}),
                dbc.Col(controls, width=2),
                dbc.Col(
                    [
                        # dbc.Card(
                        #     [
                                strategy_stats,
                                html.Br(),
                                dbc.Card(
                                    dcc.Graph(
                                        id="strategy-graph",
                                        figure={
                                            'layout': go.Layout(
                                            paper_bgcolor='rgba(0,0,0,0)',
                                            plot_bgcolor='rgba(0,0,0,0)',
                                            xaxis=dict(gridcolor='#444'),
                                            yaxis=dict(gridcolor='#444'),
                                            height=650
                                            )
                                        },
                                        # style={'height':'100%'},
                                        # className='h-100'
                                        
                                    ),
                                    # style={ 'minHeight':'75vh', 'height':'75vh', 'maxHeight':'75vh'},#, 'height':'70%'
                                    body=True,
                                    className='overflow-scroll'
                                ),
                        #     ],
                        #     style={'minHeight':'90vh', 'backgroundColor':'black'},
                        #     body=True,
                        #     # className='opacity-100'
                        # )
                    ],
                    
                    md=10,
                    
                ),
            ],
            # style={'minHeight':'90vh'}
            # align='stretch'
        ),
    ],
    fluid=True,
    id="outer-app-container"
)