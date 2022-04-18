import dash_bootstrap_components as dbc
from dash import dcc, html
from chart_viz_config import currencies, frequencies, min_files, n_processors
from datetime import date
import plotly.graph_objects as go

controls = dbc.Card(
    [

        dbc.Row(
            html.P('Controls', style={'fontSize':'22px', 'fontWeight':'bold'})
        ),

        html.Br(),

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
                            value=["USDT_BTC"],
                            multi=True,
                            persistence=True
                        ),
                    ],
                ),
            ]
        ),

        html.Br(),
        html.Br(),

        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Frequency"),
                        dcc.Dropdown(
                            id="download-store-freqs",
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

                dbc.Col(
                    [
                        dbc.Label("File Type"),
                        dcc.Checklist(
                            ['Quotes', 'Trades'],
                            ['Quotes'],
                            id='download-file-type-checklist',
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
        html.Br(),

        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("# of Processors"),
                        dcc.Dropdown(
                            id="download-number-processors",
                            options=[
                                {"label": freq, "value": freq} for freq in n_processors
                            ],
                            value=5,
                            multi=False,
                            persistence=True
                        ),
                    ],
                ),  
                dbc.Col(
                    [
                        dbc.Label("Min Files Re-download"),
                        dcc.Dropdown(
                            id="download-min-files-redownload",
                            options=[
                                {"label": freq, "value": freq} for freq in min_files
                            ],
                            value=860,
                            multi=False,
                            persistence=True
                        ),
                    ],
                ),  
            ]
        ),

        html.Br(),
        html.Br(),

        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Select date range"),
                        dcc.DatePickerRange(
                            id="download-date-range",
                            display_format='MMM Do, YY',
                            min_date_allowed=date(2021, 1, 1),
                            persistence=True
                        ),
                    ],
                    width=6
                ),
                dbc.Col(
                    [
                        html.P(
                            'Click the button below to start the download', 
                            id='download-output-text',
                            # style={'marginTop':'20px'}
                        ),

                        dbc.Button(
                            [
                                # dbc.Spinner(
                                #     id='download-spinner', 
                                #     color='primary', 
                                #     size='sm'
                                #     ), 
                                ' Download'
                            ], 
                            id='download-start-button', 
                            n_clicks=0,
                            style={'marginTop':'10px'}
                        )
                        # dbc.Progress(
                        #     id='download-pbar',
                        #     style={'margin-top': 15}
                        # ),
                        # dcc.Interval(
                        #     id='download-timer_progress',
                        #     interval=2000
                        # ),
                    ],
                    width=6
                ),

            ]
        ),

        html.Br(),
        # html.Br(),

        # dbc.Row(
        #     [

        #         dbc.Col(
        #             [
        #                 dbc.Button(
        #                     [dbc.Spinner(id='download-spinner', size='sm'), ' Download'], 
        #                     id='download-start-button', 
        #                     n_clicks=0,
        #                     style={'marginTop':'38px'}
        #                 )
        #             ],
        #             width=6
        #         ),

        #     ],
        #     justify='start'
        # ),

    ],
    style={'minHeight':'400px', 'maxHeight':'90vh', 'height':'90vh'},
    body=True,
)

data_overview = dbc.Card(
    [
        dbc.Row(
            [
                dbc.Col(
                    dcc.Graph(
                        id="download-overview-chart-raw-data",
                        figure={
                            'layout': go.Layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            xaxis=dict(gridcolor='#444'),
                            yaxis=dict(gridcolor='#444')
                            )
                        },
                        style={'height':'30vh'}
                    ),
                )
            ],
        ),
        dbc.Row(
            [
                dbc.Col(
                    dcc.Graph(
                        id="download-overview-chart-resampled-data",
                        figure={
                            'layout': go.Layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            xaxis=dict(gridcolor='#444'),
                            yaxis=dict(gridcolor='#444')
                            )
                        },
                        style={'height':'30vh'}
                    ),
                )
            ],
        ),
        dbc.Row(
            [
                dbc.Col(
                    dcc.Graph(
                        id="download-overview-chart-trades-data",
                        figure={
                            'layout': go.Layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            xaxis=dict(gridcolor='#444'),
                            yaxis=dict(gridcolor='#444')
                            )
                        },
                        style={'height':'30vh'}
                    ),
                )
            ],
        ),

        dcc.Store(
            id='download-existing-file-data'
        ),

        dcc.Store(
            id='resample-existing-file-data'
        )
    ],
    style={'minHeight':'400px', 'maxHeight':'90vh', 'height':'90vh'},
    # className="auto",
    body=True,
),

downloading_page_layout = dbc.Container(
    [
        html.Br(),
        dbc.Row(
            [
                dbc.Col(controls, width=4),
                dbc.Col(data_overview, md=8,),
            ],
            className="h-100"
        ),
    ],
    fluid=True,
    id="download-container"
)