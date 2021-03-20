import pandas as pd
import time
import calendar
from datetime import datetime
from requests import get
from json import loads
import sys, os


pair = 'USDT_BTC'
start_date = '2020-04-03'
end_date = '2020-06-29'
start = calendar.timegm(datetime.strptime(start_date, "%Y-%m-%d").timetuple())
end = calendar.timegm(datetime.strptime(end_date, "%Y-%m-%d").timetuple())

trades_folder = os.path.realpath(os.path.join(os.getcwd(), 'trades'))

if not os.path.exists(trades_folder):
    os.makedirs(trades_folder)

for day in range(start, end, 60*60*24): #loop through days
    trades_day = []
    trades_day_file_name = os.path.join(trades_folder, f"{pair}-{datetime.utcfromtimestamp(day).strftime('%Y%m%d')}.csv.gz")
    if not os.path.exists(trades_day_file_name):

        for minute in range(day, day + 60*60*24, 60):# assuming no more than 1000 trades (poliniex api restriction) in 1 minute window
            print(datetime.utcfromtimestamp(minute).strftime('Fetching trades for %Y-%m-%d  %H:%M:%S'))
            response = get(f'https://poloniex.com/public?command=returnTradeHistory&currencyPair={pair}&start={minute}&end={minute+59}')
            if response.status_code == 200:
                trades = loads(response.text)
                trades_day += trades
            else:
                raise Exception(response.content)

        df = pd.DataFrame(trades_day)
        df.sort_values(by=['date'])
        df.to_csv(trades_day_file_name, index=False, compression='gzip')
