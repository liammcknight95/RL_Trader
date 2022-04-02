# from tracemalloc import start
import dash
from dash import Input, Output, State, callback, dcc, html
import dash_bootstrap_components as dbc
from dash.long_callback import DiskcacheLongCallbackManager
import diskcache

import numpy as np
import pandas as pd
import time, os, sys, shutil, glob
from datetime import datetime, timedelta

# my modules
from configuration import config
from chart_viz_charting_layout import charting_page_layout
import chart_viz_charting
from chart_viz_downloading_layout import downloading_page_layout
import chart_viz_downloading
import data_preprocessing as dp

import multiprocessing as mp
from p_tqdm import p_map

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
app.layout = dbc.Container([
    navbar,
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
], className="h-100", fluid=True, style={'padding':'0px'})


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
    running=[(Output("download-start-button", "disabled"), True, False)],
    prevent_initial_call=True
)
def download_missing_files(dwnld_click, pairs, freqs, start_date, end_date, numb_processors, min_redown_file, dwnld_data, rsmpl_data):

    if dwnld_click > 0:

        all_days_in_range = pd.date_range(start_date, end_date, freq='1D').astype('str').tolist()
        dwnld_df = pd.DataFrame(dwnld_data)
        rsmpld_df = pd.DataFrame(rsmpl_data)
        
        all_inputs = get_day_pair_inputs(dwnld_df, rsmpld_df, pairs, freqs, all_days_in_range, min_redown_file)
        print(f'Executing the following download jobs: {all_inputs} \nOn {numb_processors} different processors')

        # for bar progress tqdm
        std_err_backup = sys.stderr
        file_prog = open('progress.txt', 'w')
        sys.stderr = file_prog

        # with mp.Pool(processes=numb_processors) as pool:
        #     results = pool.starmap(dp.get_lob_data, all_inputs)

        temp_input_df = pd.DataFrame(all_inputs, columns=['pair', 'date_start', 'date_end', 'resampling_frequency'])
        results = p_map(dp.get_lob_data,
            temp_input_df['pair'].tolist(), 
            temp_input_df['date_start'].tolist(), 
            temp_input_df['date_end'].tolist(), 
            temp_input_df['resampling_frequency'].tolist(), 
            **{"num_cpus": numb_processors}
        )

        file_prog.close()
        sys.stderr = std_err_backup

        return f"Download terminated for {len(all_inputs)} files using {numb_processors} processors clicks:{dwnld_click}"
    else:
        return "Waiting for a btn click"


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



## TODO: check why other partial days have not been downloaded
## update chart at the end
## add progress bar
## check if multiprocessing is possible for this

if __name__ == "__main__":
    app.run_server(debug=True, port=8888)