import dash_bootstrap_components as dbc
from dash import dcc, html
from chart_viz_config import currencies, frequencies
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
                            id="download-ccy-pairs",
                            options=[
                                {"label": cur, "value": cur} for cur in currencies
                            ],
                            value="USDT_BTC",
                            multi=True
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
                            id="download-store_freqs",
                            options=[
                                {"label": freq, "value": freq} for freq in frequencies
                            ],
                            value="30min",
                            multi=True
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
                    id="download-date-range",
                    display_format='MMM Do, YY',
                    min_date_allowed=date(2021, 1, 1),
                ),
            ]
        ),
    ],
    style={'minHeight':'800px', 'height':'100%'},
    body=True,
)

data_overview = dbc.Card(
    dcc.Graph(
        id="download-data-overview",
        figure={
            'layout': go.Layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=600
            )
        }
    ),
    style={'minHeight':'800px', 'height':'100%'},
    body=True,
),

downloading_page_layout = dbc.Container(
    [
        html.Br(),
        dbc.Row(
            [
                dbc.Col(controls, width=4),
                dbc.Col(data_overview, md=8,
                ),
            ],
            style={'maxHeight':'80vh'}
        ),
    ],
    fluid=True,
    id="download-container"
)