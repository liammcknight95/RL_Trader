import dash_bootstrap_components as dbc
from dash import dcc, html
from chart_viz_config import currencies, frequencies

def new_bot_info(bot_id):
    return dbc.Row(
        [
            dbc.Col(
                html.P(bot_id, id={"type":"trading-bot-info", "index":bot_id}),
                width=10
            ),

            dbc.Col(
                dbc.Button('Kill', id={"type":"trading-bot-btn-kill", "index":bot_id}, color='danger'),
                width=2
            )
        ]
    )

running_bots_ui = dbc.Card(
    [
        dbc.Label("Running Bots"),
        dbc.Row(
            [
                html.P("List the running strategies here - from database")
            ],
            id="trading-live-bots-list"
        )  
    ],
    body=True
)

new_bot_ui = dbc.Card(
    [
        dbc.Label("Create a new Bot"),

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
            [
                dbc.Button(
                    "New Bot", 
                    id="trading-new-bot", 
                    n_clicks=0,
                    style={"marginTop":"10px"}
                )
            ]
        ),

        html.Br(),

        html.P("", id="trading-amend-bot-message")

    ],
    body=True
)

current_balances_ui = dbc.Card(
    [
        dbc.Label('Exchange Balances'),
        html.P('Recap of existing bitstamp balances')
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