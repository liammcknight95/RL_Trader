import gzip
import json
import glob, os

from datetime import datetime, timedelta, time

import pandas as pd
import numpy as np

class LOBData:

    # initialize class attributes: root_path is the root folder, security is the currency pair to unpack
    def __init__(self, raw_data_path, security, root_caching_folder, frequency = timedelta(seconds=10), levels=10):

        assert frequency >= timedelta(seconds=10), 'Frequency must be greater than 10 seconds'

        self.raw_data_path = raw_data_path
        self.security = security
        self.frequency = frequency
        self.caching_folder = f'{root_caching_folder}/{security}'
        self.cache_file = f'{self.caching_folder}/test-data-cache-1m.csv'
        self.levels = levels

        os.makedirs(self.caching_folder, exist_ok=True)

    def get_LOB_data(self): # TODO consider returning date rage

        if os.path.isfile(self.cache_file):
            return pd.read_csv(self.cache_file)

        else:
            all_files = []
            for root, subdirs, files in os.walk(f'{self.raw_data_path}/{self.security}'):
                for filename in files:
                    all_files.append(filename) if filename.endswith('.json.gz') else None
            all_files.sort()

            first = all_files[0].split('.')[0] # get 20200403_13 from 20200403_13.json.gz
            last = all_files[-1].split('.')[0]
            start_date = datetime.strptime(first, '%Y%m%d_%H')
            end_date = datetime.strptime(last, '%Y%m%d_%H')

            print('Processing raw hourly snapshot files:')
            processed_data = []

            # Loop through all time steps between start and end date instead
            # of looping through all_files list to check for missing files
            while start_date <= end_date:
                subdir = datetime.strftime(start_date, '%Y/%m/%d')
                filename = datetime.strftime(start_date, '%Y%m%d_%H.json.gz')
                path = f'{self.raw_data_path}/{self.security}/{subdir}/{filename}'
                print(path)
                raw_one_hour_data = self.load_data_file(path)

                for key in raw_one_hour_data.keys():
                    # unravel the nested json structure into a more manageable list of lists
                    processed_data.append(list(zip(
                        [i[0] for i in raw_one_hour_data.get(key)['asks'][0:self.levels]], # ask px
                        [i[1] for i in raw_one_hour_data.get(key)['asks'][0:self.levels]], # ask size
                        [i[0] for i in raw_one_hour_data.get(key)['bids'][0:self.levels]], # bid px
                        [i[1] for i in raw_one_hour_data.get(key)['bids'][0:self.levels]], # bid size
                        list(range(self.levels)), # ob level - assuming same for both
                        [key[-15:]] * self.levels  # datetime part of the key
                    )))

                start_date += timedelta(hours=1)
            
            # unravel nested structure and force data types
            df = pd.DataFrame([y for x in processed_data for y in x], #flatten the list of lists structure
                            columns = ['Ask_Price', 'Ask_Size', 'Bid_Price', 'Bid_Size','Level', 'Datetime'])

            df['Ask_Price'] = df['Ask_Price'].astype('float64')
            df['Ask_Size'] = df['Ask_Size'].astype('float64')
            df['Bid_Price'] = df['Bid_Price'].astype('float64')
            df['Bid_Size'] = df['Bid_Size'].astype('float64')
            df['Level'] = df['Level'].astype('int64')
            df['Datetime'] = pd.to_datetime(df['Datetime'], format='%Y%m%d_%H%M%S')

            resample_freq = '1min'
            resampled_data = df.groupby([pd.Grouper(key='Datetime', freq=resample_freq), pd.Grouper(key='Level')]).last().reset_index()


            resampled_data.to_csv(self.cache_file)
            return df

    def load_data_file(self, path_string):

        try:
            # load raw data
            with gzip.open(path_string, 'r') as f:  # gzip
                json_bytes = f.read()               # bytes
                json_string = json_bytes.decode('utf-8')

                frozen = json_string.count('"isFrozen": "1"')
                if frozen > 0:
                    print(f'Frozen {frozen} snapshots')
            one_hour_data = self.load_json(json_string)

        except IOError as e:
            print(e.errno)
            print(e)
            # TODO Handle missing files

        except Exception as e:
            print(e.errno)
            print(e)

        return one_hour_data

    def load_json(self, json_string):
        try:
            json_object = json.loads(json_string)

        except json.JSONDecodeError as e:
            print(f'Malformed JSON in file at position {e.pos}')

            if '}0254}' in json_string:
                fixed_json_string = json_string.replace('}0254}', '}')
                return self.load_json(fixed_json_string)

            if e.msg == 'Expecting value':
                prev_snapshot_start = json_string.rindex('{', 0, e.pos)

                if prev_snapshot_start == 0:
                    # {"BTC_ETH-20201008_030000": ,"BTC_ETH-20201008_030010": {"asks
                    fixed_json_string = json_string[:1] + json_string[e.pos+1:]

                else:
                    # 5634},"BTC_ETH-20200903_095550": ,"BTC_ETH-20200903_095600": {"as
                    prev_snapshot_end = json_string.rindex('}', 0, e.pos) + 1
                    #prev_snapshot = json_string[prev_snapshot_start:prev_snapshot_end]
                    fixed_json_string = json_string[:prev_snapshot_end] + json_string[e.pos:]

            elif e.msg == 'Extra data':
                if json_string[e.pos-2:e.pos] == '}}':

                    print(json_string[e.pos-12:e.pos+12])

                    # 922}},"BTC_
                    #fixed_json_string = json_string[:e.pos-1] + json_string[e.pos:]
                    fixed_json_string = json_string.replace('}}', '}') + '}' # at the end should be }}
                    #print(fixed_json_string[e.pos-13112:e.pos+13112])

                else:
                    # en": "0", "seq": 945674867}, "seq": 945674845},"BTC_ETH-20
                    previous_comma = json_string.rindex(',', 0, e.pos)
                    fixed_json_string = json_string[:previous_comma] + json_string[e.pos:]

            else:
                # "seq": 933840511}": 933840515},"BTC_ET
                # "seq": 934014002}4001},"BTC_
                next_comma = json_string.index(',', e.pos)
                fixed_json_string = json_string[:e.pos] + json_string[next_comma:]
            return self.load_json(fixed_json_string)

        return json_object

# TODO add method which returns data with different frequency

root_path = '/home/pawel/Documents/LOB-data/new' # path where zipped files are stored
root_caching_folder = '/home/pawel/Documents/LOB-data/cache' # processed cached data folder
security = 'BTC_ETH3'

# instantiate class
data = LOBData(root_path, security, root_caching_folder)
df = data.get_LOB_data()

print(df.shape)
