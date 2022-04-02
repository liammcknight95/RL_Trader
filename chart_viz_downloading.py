### to do: check what files have already been cached on a given locaition (config file)
# show gant chart with cached frequencies as well as raw data downloaded
from datetime import date, datetime, timedelta
from dash import Input, Output, State, callback

import plotly.express as px
import pandas as pd
from configuration import config
import glob


configuration = config()
raw_data_folder = configuration['folders']['raw_lob_data']
resampled_data_folder = configuration['folders']['resampled_data']

@callback(
    Output("download-overview-chart-raw-data", "figure"),
    Output("download-existing-file-data", "data"),
    Input("download-ccy-pairs", "value"),
    Input("download-date-range", 'start_date'),
    Input("download-date-range", "end_date"),
    Input("download-output-text", "children")
)
def chart_downloads(pairs, start_date, end_date, finished_dwnld):

    dwnld_df_list = []
    for pair in pairs:
        # get raw data download history
        raw_file_path = f'{raw_data_folder}/{pair}'
        print(raw_file_path)
        day_folders = glob.glob(raw_file_path + '/**/*/*/')
        # print(day_folders)

        number_daily_list = []
        for day_path in day_folders:
            number_daily_list.append(len(glob.glob(f'{day_path}/*')))

        day_dates_lists = [day.split('/')[-4:-1] for day in day_folders]
        day_dates_strings = ['-'.join(day_date_list) for day_date_list in day_dates_lists]

        temp_df = pd.DataFrame([day_dates_strings, number_daily_list], index=['date', 'file_number']).T
        temp_df['pair'] = pair
        dwnld_df_list.append(temp_df)

    dwnld_df = pd.concat(dwnld_df_list)
    dwnld_df_filt = dwnld_df[(dwnld_df['date']>=start_date)&(dwnld_df['date']<=end_date)]

    fig = px.bar(
        dwnld_df_filt, 
        x='date', 
        y='file_number', 
        color='pair', 
        barmode="group", 
        template="plotly_dark",
        title='Raw Data'
    )
    fig.update_layout(
        title_x=0.5,
        title_font_size=18,
        xaxis_range=[ # timedelta to visualize very first entry
            (pd.to_datetime(start_date) - timedelta(1)).strftime(format='%Y-%m-%d'), 
            (pd.to_datetime(end_date) + timedelta(1)).strftime(format='%Y-%m-%d')
        ],
        title_font_family='sans-serif',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig, dwnld_df_filt.to_dict('records')

@callback(
    Output("download-overview-chart-resampled-data", "figure"),
    Output("resample-existing-file-data", "data"),
    Input("download-ccy-pairs", "value"),
    Input("download-date-range", 'start_date'),
    Input("download-date-range", "end_date"),
    Input("download-store-freqs", "value"),
    Input("download-output-text", "children")
)
def chart_resampled(pairs, start_date, end_date, frequency, finished_dwnld):
    resampled_df_list = []
    levels = 100
    for pair in pairs:
        freq_seconds = f"{datetime.strptime(frequency,'%Mmin').minute * 60}s"

        resampled_folders = glob.glob(f"{resampled_data_folder}/{pair}/{levels}_levels/{freq_seconds}/*")
        resampled_dates = [file.split('/')[-1] for file in resampled_folders if "." not in file] # parquet only
        temp_df = pd.DataFrame([resampled_dates], index=['date']).T
        temp_df['pair'] = pair
        temp_df['frequency'] = freq_seconds
        resampled_df_list.append(temp_df)

    resampled_files_df = pd.concat(resampled_df_list)
    resampled_files_df['file_number'] = 1
    resampled_files_df_filt = resampled_files_df[(resampled_files_df['date']>=start_date)&(resampled_files_df['date']<=end_date)]

    fig = px.bar(
        resampled_files_df_filt, 
        x='date', 
        y='file_number', 
        color='pair', 
        barmode="group", 
        template="plotly_dark",
        title=f'Resampled Data {frequency}'
    )
    fig.update_layout(
        title_x=0.5,
        title_font_size=18,
        xaxis_range=[ # timedelta to visualize very first entry
            (pd.to_datetime(start_date) - timedelta(1)).strftime(format='%Y-%m-%d'), 
            (pd.to_datetime(end_date) + timedelta(1)).strftime(format='%Y-%m-%d')
        ],
        xaxis_ticks='outside',
        title_font_family='sans-serif',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig, resampled_files_df_filt.to_dict('records')

@callback(
    Output("download-pbar", "value"),
    Output("download-pbar", "label"),
    Input("download-timer_progress", "n_intervals"),
    prevent_initial_call=True)
def callback_progress(n_intervals: int):
    
    try:
        with open('progress.txt', 'r') as file:
            str_raw = file.read()
        last_line = list(filter(None, str_raw.split('\n')))[-1]
        percent = float(last_line.split('%')[0])
        
    except:
        percent = 0
    
    finally:
        text = f'{percent:.0f}%'
        return percent, text