# from tracemalloc import start
import dash
from dash import Input, Output, callback, dcc, html
import dash_bootstrap_components as dbc

import numpy as np
import pandas as pd

# my modules
from chart_viz_charting_layout import charting_page_layout
import chart_viz_charting
from chart_viz_downloading_layout import downloading_page_layout


navbar = dbc.Navbar(
    dbc.Container(
        [
        dbc.Row(
            [
                dbc.Col(dbc.NavItem(dbc.NavLink("Charting", href="/charting")), width=3),
                dbc.Col(dbc.NavItem(dbc.NavLink("Downloading", href="/downloading")), width=3),
            ],
            justify='start'
        )
    ],
    fluid=True
    ),
    color="dark",
    dark=True,
)

app = dash.Dash(external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True)

app.layout = html.Div([
    navbar,
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])


@callback(Output('page-content', 'children'),
              Input('url', 'pathname'))
def display_page(pathname):
    if pathname == '/charting':
        return charting_page_layout
    elif pathname == '/downloading':
        return downloading_page_layout
    else:
        return 'Nothing to display at this path'


if __name__ == "__main__":
    app.run_server(debug=True, port=8888)