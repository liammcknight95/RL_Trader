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
        title_font_family='sans-serif',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig, dwnld_df_filt.to_dict('records')
