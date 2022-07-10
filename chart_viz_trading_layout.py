import dash_bootstrap_components as dbc
from dash import dcc, html
import plotly.graph_objects as go
from chart_viz_config import ccxt_exchanges, strategies, frequencies

### RUNNING BOTS
def new_bot_info(bot_id, bot_description, bot_statuses):
    ''' Dynamically create a new ui element every time a bot spins up or is deleted '''
    return dbc.Col(
            [
                dbc.Row(
                    [

                        dbc.Col(
                            html.P(bot_description),
                            width=8
                        ),

                        dbc.Col(
                            [
                                dbc.Button('Show Data', id={"type":"trading-bot-btn-plot", "index":bot_id}),
                                dbc.Button('Liquidate', id={"type":"trading-bot-btn-liquidate", "index":bot_id}, color='danger'),
                            ],
                            width=4,
                            className="d-grid gap-2 d-md-flex justify-content-md-end",
                        )                  

                    ],

                    justify="between"
                )
            ] +

            [
                dbc.Row(
                    [
                        dbc.Col(
                            html.P(bot_status),
                            width=10
                        )
                    ]
                )
             for bot_status in bot_statuses],

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

        dbc.Modal(
            [
                dbc.ModalHeader(
                    dbc.ModalTitle(
                        "Header",
                        id="trading-live-bots-modal-title"
                    )
                ),

                dbc.ModalBody(
                    dbc.Card(
                        dcc.Graph(
                            id="trading-live-bots-px-chart",
                            figure={
                                'layout': go.Layout(
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                xaxis=dict(gridcolor='#444'),
                                yaxis=dict(gridcolor='#444'),
                                # height=650
                                )
                            },
                            # style={'height':'100%'},
                            # className='h-100'
                            
                        ),
                        # style={ 'minHeight':'75vh', 'height':'75vh', 'maxHeight':'75vh'},#, 'height':'70%'
                        body=True,
                        className='overflow-scroll'
                    ),
                    id="trading-live-bots-modal-body"
                ),
            ],
            id="trading-live-bots-modal",
            size="xl",
            is_open=False,
        ),

    ],
    body=True,
    #className='h-100',
    # style={'minHeight':'55vh'}
)

### RUNNING BOTS ORDERS
def new_order_info(order_id, order_general_info, order_details):
    ''' Dynamically create a new ui element every time a new oder is placed '''
    return dbc.Col(
        [
    
            dbc.Row(
                [
                    dbc.Col(
                        html.P(order_general_info, id={"type":"trading-order-general-info", "index":order_id}),
                        width=12
                    )
                ]
            ),

            dbc.Row(
                [
                    dbc.Col(
                        html.P(order_details, id={"type":"trading-order-details", "index":order_id}),
                        width=12
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

running_orders_ui = dbc.Card(
    [
        dbc.Row(
            dbc.Label(
                "Orders", 
                style={"text-align":"center"}
            ),
        ),

        html.Br(),

        dbc.Row(
            [
                html.P("List orders of running bots and recently closed ones - from database")
            ],
            id="trading-running-orders-list"
        ),

        dcc.Store(
            id="trading-running-orders-element-python-list", 
            storage_type="memory"
        ),

    ],
    body=True,
    # className='h-100',
    # style={'minHeight':'30vh'}
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

        dbc.Col(
            [
                dbc.Label("Database"),
                dcc.RadioItems(
                    ["Local", "Server"],
                    "Local",
                    id="trading-bot-db-settings",
                    inline=True,
                    persistence=True,
                    inputStyle={"marginRight": "3px"},
                    labelStyle={"marginRight": "15px"}
                )
            ],
            width=6
        ),


        dcc.Store(
            id="trading-db-settings-store", 
            storage_type="memory"
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
                            # value="Bitstamp",
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
            [
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
                ),
                dbc.Col(
                    [
                        dbc.Label("Opening Position - On Signal"),
                        dcc.RadioItems(
                            ["Current", "Next"],
                            "Current",
                            id="trading-bot-opening-position",
                            inline=True,
                            persistence=True,
                            inputStyle={"marginRight": "3px"},
                            labelStyle={"marginRight": "15px"}
                        )
                    ],
                    width=6
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
                    [
                        dbc.Row(running_bots_ui, className='h-50 overflow-scroll', style={'maxHeight':'50vh'}),
                        dbc.Row(running_orders_ui, className='h-50 overflow-scroll', style={'paddingTop':'20px', 'maxHeight':'50vh'}),
                    ],
                    width=6,
                ),

                dbc.Col(
                    current_balances_ui,
                    width=2
                )

            ],
        )

    ],
    fluid=True,
)