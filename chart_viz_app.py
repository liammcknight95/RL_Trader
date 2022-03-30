# from tracemalloc import start
import dash
from dash import Input, Output, State, callback, dcc, html
import dash_bootstrap_components as dbc
from dash.long_callback import DiskcacheLongCallbackManager
import diskcache

import numpy as np
import pandas as pd
import time

# my modules
from chart_viz_charting_layout import charting_page_layout
import chart_viz_charting
from chart_viz_downloading_layout import downloading_page_layout
import chart_viz_downloading
import data_preprocessing as dp

cache = diskcache.Cache('./cache')
lcm = DiskcacheLongCallbackManager(cache)

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

app = dash.Dash(long_callback_manager=lcm, external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True)

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

@app.long_callback(
    output=Output("download-output-text", "children"),
    inputs=(Input("download-start-button", "n_clicks"),
        State("download-ccy-pairs", 'value'),
        State("download-date-range", 'start_date'),
        State("download-date-range", "end_date"),
        State("download-existing-file-data", "data")),
    running=[(Output("download-start-button", "disabled"), True, False)],
    prevent_initial_call=True
)
def download_missing_files(dwnld_click, pair, start_date, end_date, dwnld_data):

    if dwnld_click > 0:
        dwnld_df = pd.DataFrame(dwnld_data)
        print(dwnld_df)

        all_days_list = pd.date_range(start_date, end_date, freq='1D').astype('str').tolist()
        downloaded_days_list = dwnld_df[dwnld_df['file_number']==864]['date'].tolist() # magic number 864, robust?

        missing_days_list = [day for day in all_days_list if day not in downloaded_days_list]

        print(dwnld_click)
        # time.sleep(3)
        for date in missing_days_list:
            dp.get_lob_data(pair[0], date, date)
        return f"Download terminated {len(downloaded_days_list)} clicks:{dwnld_click}"
    else:
        return "Waiting for a btn click"

## TODO: check why other partial days have not been downloaded
## update chart at the end
## add progress bar
## check if multiprocessing is possible for this

if __name__ == "__main__":
    app.run_server(debug=True, port=8888)