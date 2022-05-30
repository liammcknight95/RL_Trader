import dash_bootstrap_components as dbc
from dash import dcc, html
from chart_viz_config import strategies, currencies, frequencies

### RUNNING BOTS
def new_bot_info(bot_id):
    ''' Dynamically create a new ui element every time a bot spins up or is deleted '''
    return dbc.Row(
        [
            dbc.Col(
                html.P(bot_id, id={"type":"trading-bot-info", "index":bot_id}),
                width=10
            ),

            dbc.Col(
                dbc.Button('Liquidate', id={"type":"trading-bot-btn-liquidate", "index":bot_id}, color='danger'),
                width=2
            )
        ]
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
            interval=1*2000, # in milliseconds
            n_intervals=0
        ),

        dcc.Store(
            id="trading-live-bots-element-python-list", 
            storage_type="memory"
        ),

    ],
    body=True
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
                        dbc.Label("Pair"),
                        dcc.Dropdown(
                            id="trading-ccy-pairs",
                            options=[
                                {"label": cur, "value": cur} for cur in currencies
                            ],
                            value=["USDT_BTC"],
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
                        dbc.Label("Frequency"),
                        dcc.Dropdown(
                            id="trading-store-freqs",
                            className="dark-dd-border",
                            options=[
                                {"label": freq, "value": freq} for freq in frequencies
                            ],
                            value="30min",
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
            dbc.Col(
                [
                    dbc.Label("Strategy"),
                    dcc.Dropdown(
                        id="trading-bot-strategy",
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
                        dbc.Label("Stop Loss"),
                        dbc.Input(
                            id="trading-bot-stop-loss", 
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
    body=True
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
    body=True
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
                    width=4
                ),

                dbc.Col(
                    current_balances_ui,
                    width=4
                )

            ]
        )

    ],
    fluid=True
)