import pandas as pd
import numpy as np
import dask.dataframe as dd

import data_preprocessing as dp

from datetime import datetime, timedelta
import math
import re
import multiprocessing as mp

pair = 'USDT_BTC'
date_start = '2021-06-01'
date_end = '2022-02-13'

# prepare inputs for multi processing
date_daterange = pd.date_range(date_start, date_end, freq='1D').astype('str').tolist()
processes = 5
multiple = math.ceil(len(date_daterange) / processes) # round up
slice_idx = np.arange(0, len(date_daterange), multiple)
date_slices = [date_daterange[i:i+multiple] for i in slice_idx]
inputs = [(pair, date_list[0], date_list[-1]) for date_list in date_slices]
print(inputs)

# time taken to process 10 file with 5 processes: 3min 39s (85/90% RAM)
with mp.Pool(processes=processes) as pool:
    results = pool.starmap(dp.get_lob_download_only, inputs)