import data_preprocessing as dp
from datetime import timedelta, date
import numpy as np


def get_data(pair, start_date:str, end_date:str='', frequency:int=1800):
    ''' 
        Load data from data_preprocessing module
        pair: string, the currency pair to download data for
        start_date: date string in the format %Y-%m-%d
        end_date: optional, date string in the format %Y-%m-%d. Default value "today"
        frequency: integer, expressed in number of seconds
    '''

    if not end_date:
        end_date = date.today().isoformat()

    df_data = dp.import_data(
        pair, 
        start_date, 
        end_date,
        frequency=timedelta(seconds=frequency),
        depth=100,
        include_trades=False
    ).sort_index() # make sure data is sorted
    df_data['returns'] = np.log(df_data['Mid_Price']/df_data['Mid_Price'].shift(1))
    print(df_data.columns)
    return df_data