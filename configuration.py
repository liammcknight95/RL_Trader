import os
import configparser

def config():
    '''
    Function that returns project configuration.
    If there is no config.ini file in project root folder it creates it.
    If this file exists it loads an existing configuration.
    Can be used like this:
    config = config()
    raw_lob_data_folder = config['folders']['raw_lob_data']
    Returns: ConfigParser object
    '''

    config = configparser.ConfigParser()

    if os.path.isfile('project.conf'):
        config.read('project.conf')

    else:
        config['folders'] = {
            'experiments': '~/Experiments',
            'resampled_data': '~/Experiments/resampled',
            'raw_lob_data': '~/Experiments/input/raw/lob',
            'raw_trade_data': '~/Experiments/input/raw/trades'
            }
        config['buckets'] = {
            'lob_data': 'limit-order-books-polonie-limitorderbooksnapshots-1ggf6vguvne3r',
            'trade_data': 'trades-poloniex'
            }
        config['other'] = {
            'cross_account_access': 'no',
            'cross_account_access_role': 'arn:aws:iam::589435931329:role/S3CrossAccountAccess',
            }

        with open('project.conf', 'w') as configfile:    # save
            config.write(configfile)

    return config