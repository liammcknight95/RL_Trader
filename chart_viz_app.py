# from tracemalloc import start
from __future__ import annotations
import dash
from dash import Input, Output, State, callback, dcc, html
import dash_bootstrap_components as dbc
from dash.long_callback import DiskcacheLongCallbackManager
from dash.exceptions import PreventUpdate
import diskcache
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import time, os, sys, shutil, glob
from datetime import datetime, timedelta
import uuid
from flask_caching import Cache
import logging

from torch import preserve_format

# my modules
from configuration import config
from chart_viz_config import strategies
from chart_viz_charting_layout import charting_page_layout
import chart_viz_charting
from chart_viz_downloading_layout import downloading_page_layout
import chart_viz_downloading
import data_preprocessing as dp
from StratTest.engine import TradingStrategy

import multiprocessing as mp
import tqdm
# from p_tqdm import p_map
from decorators.log_exceptions import exception_handler 

# main info logger
log_main = logging.getLogger('app_viz_logger') 
log_main.setLevel(logging.DEBUG)    
log_format = logging.Formatter('[%(asctime)s] [%(levelname)s] - %(message)s')

# writing to file                                                     
file_handler = logging.FileHandler("./logs/app_viz_info.log")                             
file_handler.setLevel(logging.DEBUG)                                        
file_handler.setFormatter(log_format)                          
log_main.addHandler(file_handler)  

# exception handler decorator
logged = exception_handler('chart_viz_app: {func.__name__}')

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
    style={'height':'5vh'}
)

app = dash.Dash(long_callback_manager=lcm, external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True)
app.title = "RL Trader"

# handle caching
session_id = str(uuid.uuid4())
cache = Cache(app.server, config={
    # 'CACHE_TYPE': 'redis',
    # 'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'localhost:6379'),

    # Alternatively, save on the filesystem with the following config:
    # Note that filesystem cache doesn't work on systems with ephemeral
    # filesystems like Heroku.
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': './caches',
    # should be equal to maximum number of users on the app at a single time
    # higher numbers will store more data in the filesystem / redis cache
    'CACHE_THRESHOLD': 3
})


app.layout = dbc.Container([
    navbar,
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content'),
    html.Div(session_id, id='session-id', style={'display': 'none'}),
], className="h-100", fluid=True, style={'padding':'0px'})

@logged
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
        State("download-ccy-pairs", "value"),
        State("download-store-freqs", "value"),
        State("download-date-range", "start_date"),
        State("download-date-range", "end_date"),
        State("download-number-processors", "value"),
        State("download-min-files-redownload", "value"),
        State("download-existing-file-data", "data"),
        State("resample-existing-file-data", "data")),
    running=[(Output("download-start-button", "disabled"), True, False),
        (Output("download-start-button", "children"), "Download in Progress", "Download") 
    ],
    prevent_initial_call=True
)
def download_missing_files(dwnld_click, pairs, freqs, start_date, end_date, numb_processors, min_redown_file, dwnld_data, rsmpl_data):
    print(f'### in long allback {dwnld_click}')
    if dwnld_click > 0:

        all_days_in_range = pd.date_range(start_date, end_date, freq='1D').astype('str').tolist()
        dwnld_df = pd.DataFrame(dwnld_data)
        rsmpld_df = pd.DataFrame(rsmpl_data)
        
        all_inputs = get_day_pair_inputs(dwnld_df, rsmpld_df, pairs, freqs, all_days_in_range, min_redown_file)
        print(f'Executing the following download jobs: {all_inputs} \nOn {numb_processors} different processors')

        # for bar progress
        # size_of_step
        # std_err_backup = sys.stderr
        # file_prog = open('progress.txt', 'w')
        # sys.stderr = file_prog

        with mp.Pool(processes=numb_processors) as pool:
            results = pool.starmap(dp.get_lob_data, all_inputs)
        # temp_input_df = pd.DataFrame(all_inputs, columns=['pair', 'date_start', 'date_end', 'resampling_frequency'])
        # results = p_map(dp.get_lob_data,
        #     temp_input_df['pair'].tolist(), 
        #     temp_input_df['date_start'].tolist(), 
        #     temp_input_df['date_end'].tolist(), 
        #     temp_input_df['resampling_frequency'].tolist(), 
        #     **{"num_cpus": numb_processors}
        # )

        # file_prog.close()
        # sys.stderr = std_err_backup

        return f"Download terminated for {len(all_inputs)} files using {numb_processors} processors clicks:{dwnld_click}"
    else:
        return "Click the button below to start the download"


def get_day_pair_inputs(dwnld_df, rsmpld_df, pairs, freqs, all_days_in_range, min_redown_file):
    ''' Create a list of unique inputs to either download and resample or just resample 
        Get LOB will run the appropriate checks to avoid redownload
    '''
    all_inputs = []
    for pair in pairs:
        print(dwnld_df)

        if dwnld_df.shape[0]>0:
            downloaded_days_list = dwnld_df[(dwnld_df['pair']==pair)&(dwnld_df['file_number']>=min_redown_file)]['date'].tolist() # magic number 864, robust?
            delete_partial_days(dwnld_df, pair, min_redown_file)

        else: # cover scenario where there no data dwnld yet between dates
            downloaded_days_list = []

        resampling_frequency = timedelta(seconds=datetime.strptime(freqs,'%Mmin').minute * 60)

        missing_days_list = [day for day in all_days_in_range if day not in downloaded_days_list]
        inputs_dwnld = [(pair, date, date, resampling_frequency) for date in missing_days_list]

        all_inputs += inputs_dwnld

        if rsmpld_df.shape[0]>0:
            resampled_days_list = rsmpld_df[(rsmpld_df['pair']==pair)&(rsmpld_df['file_number']==1)]['date'].tolist()
        else: # cover scenario where there no data dwnld yet between dates
            resampled_days_list = []

        missing_resampled_list = [day for day in all_days_in_range if day not in resampled_days_list]
        inputs_rsmpld = [(pair, date, date, resampling_frequency) for date in missing_resampled_list]

        all_inputs += inputs_rsmpld

    all_inputs_unique = list(set(all_inputs))

    return all_inputs_unique


def delete_partial_days(dwnld_df, pair, min_redown_file):
    ''' Function that deletes raw data and relevant levels of aggregation if a day has not been fully downloaded '''

    configuration = config()
    raw_data_folder = f"{configuration['folders']['raw_lob_data']}"
    resampled_data_folder = f"{configuration['folders']['resampled_data']}"
    levels = 100

    # get list of all dates to delete to allow redownload
    days_to_delete = dwnld_df[(dwnld_df['pair']==pair)&(dwnld_df['file_number']<min_redown_file)]['date'].tolist()

    # delete raw data folder
    date_splits = [date.split('-') for date in days_to_delete] # create list of lists with [year, month, day] format
    raw_paths_to_delete = [f"{raw_data_folder}/{pair}/{date_split[0]}/{date_split[1]}/{date_split[2]}" for date_split in date_splits]

    print('folders to be deleted: ', raw_paths_to_delete)

    for raw_file_path in raw_paths_to_delete:
        if os.path.exists(raw_file_path):
            print(' here I delete:', raw_file_path)
            shutil.rmtree(raw_file_path)
            while os.path.exists(raw_file_path): # check if it still exists
                time.sleep(0.05) # wait 50ms between calls
                pass

    # delete any resampled parquet file
    resampled_folders = glob.glob(f"{resampled_data_folder}/{pair}/{levels}_levels/*")
    resampled_frequencies = [folder.split('/')[-1] for folder in resampled_folders]
    resampled_paths_to_delete = [
        f"{resampled_data_folder}/{pair}/{levels}_levels/{freq}/{date}" 
            for date in days_to_delete 
                for freq in resampled_frequencies]

    print('Resampled files to be deleted:', resampled_paths_to_delete)

    for resampled_file in resampled_paths_to_delete:
        if os.path.exists(resampled_file):
            os.remove(resampled_file)
            while os.path.exists(raw_file_path): # check if it still exists
                time.sleep(0.02) # wait 20ms between calls
                pass



## update chart at the end
## add progress bar
## check if multiprocessing is possible for this

def get_minute_by_minute_cache(session_id, pair, start_date, end_date):
    @cache.memoize()
    def query_and_serialize_data(session_id, pair, start_date, end_date):
        df_data = dp.import_data(
            pair, 
            start_date, 
            end_date, 
            include_trades=False, 
            frequency=timedelta(seconds=60), 
            depth=100,
            s3_download=False
        )
        return df_data.reset_index().to_dict('records')
    return pd.DataFrame(query_and_serialize_data(session_id, pair, start_date, end_date))



@callback(
    Output("chart-data-store-ref", "children"),
    Input("currency-variable", "value"),
    Input("chart-date-picker-range", "start_date"),
    Input("chart-date-picker-range", "end_date")
)
@logged
def trigger_new_cache(pair, start_date, end_date):
    ''' Placeholder to trigger new minute by minute data load '''
    log_main.info(f'{session_id} new chart data store generated: {pair}, {start_date} | {end_date}')
    return f'{pair}|{start_date}|{end_date}'



@callback(
    Output("strategy-graph", "figure"),
    Output("strategy-gross-return-stat", "children"),
    Output("strategy-net-return-stat", "children"),
    Output("strategy-trades-number-stat", "children"),
    Output("strategy-sharpe-ratio-stat", "children"),
    Output("strategy-single-trades", "figure"),
    Input("chart-data-store-ref", "children"),
    Input("strategy-input", "value"),
    Input("data-frequency-variable", "value"),
    Input("strategy-transaction-cost", "value"),
    Input("strategy-stop-loss", "value"),
    Input("strategy-param-1", "value"),
    Input("strategy-param-2", "value"),
    State("session-id", "children"),
    prevent_initial_call=True
)
@logged
def make_graph(store_ref, strategy, frequency, transaction_cost, stop_loss, param1, param2, session_id):

    # if cached_data is None:
    #     raise PreventUpdate
    # load cached data
    print("##### triggering this BLOCK")
    pair, start_date, end_date = store_ref.split('|')
    data = get_minute_by_minute_cache(session_id, pair, start_date, end_date)
    if data.shape[0]>0:
        # print(data)
        data['Datetime'] = pd.to_datetime(data['Datetime'])
        data = data.set_index('Datetime')
        # print(data.iloc[1])
        # convert frequency from timedelta to seconds
        resample_freq = pd.to_timedelta(frequency)

        trading_strategy = TradingStrategy(data, frequency=resample_freq)
        trading_strategy.add_strategy(
            strategy, 
            execution_type='current_bar_close',#'next_bar_open', 'current_bar_close, 'cheat_previous_close
            stop_loss_bps=stop_loss,
            comms_bps=transaction_cost,
            indicators_params={
                strategies[strategy]['ids'][0]:param1,
                strategies[strategy]['ids'][1]:param2,
            },
        print_trades=False
    )
        # print(trading_strategy.df)

        fig_strategy = trading_strategy.trading_chart(plot_strategy=True)

        gross_return = f"{trading_strategy.cum_gross_return:.2%}"
        net_return = f"{trading_strategy.stats_cum_net_return:.2%}"
        trades_number = f"{trading_strategy.trades_df.shape[0]}"
        sharpe_ratio = f"{trading_strategy.max_drawdown:.2%}"

        fig_trades = trading_strategy.stats_plot()

    else:
        fig_strategy = {
            'layout': go.Layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=770,
            annotations=[{
                        "text": "No matching data found",
                        "xref": "paper",
                        "yref": "paper",
                        "showarrow": False,
                        "font": {
                            "size": 28,
                            "color":"white"
                        }
                    }]
            )
        }

        gross_return = "N/A"
        net_return = "N/A"
        trades_number = "N/A"
        sharpe_ratio = "N/A"

        fig_trades = {
            'layout': go.Layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
            )
        }

    return fig_strategy, gross_return, net_return, trades_number, sharpe_ratio, fig_trades

if __name__ == "__main__":
    app.run_server(debug=True, port=8888)