import dash_bootstrap_components as dbc
from dash import dcc, html
from chart_viz_config import ccxt_exchanges, strategies, currencies, currencies_mapping, frequencies

### RUNNING BOTS
def new_bot_info(bot_id, bot_description, bot_status):
    ''' Dynamically create a new ui element every time a bot spins up or is deleted '''
    return dbc.Col(
        [
    
            dbc.Row(
                [
                    dbc.Col(
                        html.P(bot_description, id={"type":"trading-bot-info", "index":bot_id}),
                        width=10
                    ),

                    dbc.Col(
                        dbc.Button('Liquidate', id={"type":"trading-bot-btn-liquidate", "index":bot_id}, color='danger'),
                        width=2
                    )
                ]
            ),

            dbc.Row(
                [
                    dbc.Col(
                        html.P(bot_status, id={"type":"trading-bot-status", "index":bot_id}),
                        width=10
                    ),
                ]
            )
        ],
        width=12,
        style={
            "backgroundColor":"#444", 
            "paddingTop":"15px",

        }
    )

running_bots_ui = dbc.Card(
    [
        dbc.Row(
            dbc.Label(
                "Running Bots", 
                style={"text-align":"center"}
            ),
        ),

        html.Br(),

        dbc.Row(
            [
                html.P("List the running strategies here - from database")
            ],
            id="trading-live-bots-list"
        ),

        dcc.Interval(
            id="trading-live-bots-interval-refresh",
            interval=1*5000, # in milliseconds
            n_intervals=0
        ),

        dcc.Store(
            id="trading-live-bots-element-python-list", 
            storage_type="memory"
        ),

    ],
    body=True,
    className='h-100'
)

### NEW BOTS
new_bot_ui = dbc.Card(
    [
        dbc.Row(
            dbc.Label(
                "Create a new Bot", 
                style={"text-align":"center"}
            )
        ),

        html.Br(),

        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Exchange"),
                        dcc.Dropdown(
                            id="trading-ccxt-exchanges",
                            options=[
                                {"label": exch, "value": exch} for exch in ccxt_exchanges
                            ],
                            value="Bitstamp",
                            multi=False,
                            persistence=True
                        ),
                    ],
                    width=6
                ),

                dbc.Col(
                    [
                        dbc.Label("Frequency"),
                        dcc.Dropdown(
                            id="trading-bot-freqs",
                            className="dark-dd-border",
                            options=[
                                {"label": freq, "value": freq[:-2]} for freq in frequencies # drop "in" of "min": ie 30m
                            ],
                            value="30m",
                            multi=False,
                            persistence=True
                        ),
                    ],
                    width=6
                ),

            ]
        ),

        html.Br(),

        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Pair"),
                        dcc.Dropdown(
                            id="trading-ccy-pairs",
                            multi=False,
                            persistence=True
                        ),
                    ],
                    width=6
                ),

                dbc.Col(
                    [
                        dbc.Label("Owned Amount"),
                        dbc.Input(
                                id="trading-owned-ccy-size", 
                                type="number", 
                                min=0, 
                                max=10000, 
                                step=0.000001,
                                value=0,
                                persistence=True
                        ),
                    ],
                    width=6
                ),

            ]
        ),


        html.Br(),

        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Stop Loss Bps"),
                        dbc.Input(
                            id="trading-bot-stop-loss-bps", 
                            type="number", 
                            min=0, 
                            max=10000, 
                            value=0,
                            persistence=True
                    ),
                    ],
                ),  
                dbc.Col(
                    [
                        dbc.Label("Stop Loss Type"),
                        dcc.Dropdown(
                            id="trading-bot-stop-loss-type",
                            className="dark-dd-border",
                            options=[
                                {"label": sl_type, "value": sl_type} for sl_type in ["static", "trailing"]
                            ],
                            value="trailing",
                            multi=False,
                            persistence=True
                        ),
                    ],
                    width=6
                ),
            ]
        ),

        html.Br(),
        html.Br(),

        dbc.Row(
            dbc.Col(
                [
                    dbc.Label("Strategy Type & Parameters"),
                    dcc.Dropdown(
                        id="trading-bot-strategy",
                        options=[
                            {"label": col, "value": col} for col in strategies.keys()
                        ],
                        value="BollingerBandsLO",
                        persistence=True
                    ),
                ],
                width=6
            )
        ),

        html.Br(),

        dbc.Row(
            id="trading-bot-strategy-parameter-elements"
        ),

        html.Br(),
        html.Br(),

        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Button(
                            "New Bot", 
                            id="trading-new-bot", 
                            n_clicks=0,
                            style={"marginTop":"10px"},
                            className="d-grid col-12"
                        ),
                        html.Br(),
                        
                        html.P("", id="trading-amend-bot-message")
                    ],
                )
            ]
        ),


    ],
    body=True,
    className='h-100'
)

### BALANCES
def new_balance_fetched(ccy, balance, balance_type):
    return dbc.Row(
        [
            dbc.Col(
                html.P(f'{ccy} - {balance:,}', 
                id={"type":"trading-balance-info", "index":f"{ccy}-{balance_type}"}),
                width=12
            ),
        ]
    )


current_balances_ui = dbc.Card(
    [
        dbc.Row(
            dbc.Label(
                'Balances', 
                style={"text-align":'center'}
            )
        ),
        html.Br(),
        dbc.Label('Free'),
        dbc.Row(
            [
                html.P("List all the non zero free balances")
            ],
            id="trading-non-zero-balances-free-list"
        ),
        html.Br(),

        dbc.Label('Used'),
        dbc.Row(
            [
                html.P("List all the non zero used balances")
            ],
            id="trading-non-zero-balances-used-list"
        ),
        html.Br(),

        dbc.Label('Total'),
        dbc.Row(
            [
                html.P("List all the non zero total balances")
            ],
            id="trading-non-zero-balances-total-list"
        )
    ],
    body=True,
    className='h-100'
)


trading_page_layout = dbc.Container(
    [
        html.Br(),

        dbc.Row(
            [
                dbc.Col(
                    new_bot_ui,
                    width=4
                ),

                dbc.Col(
                    running_bots_ui,
                    width=6
                ),

                dbc.Col(
                    current_balances_ui,
                    width=2
                )

            ]
        )

    ],
    fluid=True
)