import numpy as np
import os

# list to be updated/maintained every time a sub account is needed
# naming convention: EXCHANGENAME_SUBACCOUNTNAME
ccxt_exchanges = ['BITSTAMP_MAIN', 'BITSTAMP_BTCEMA', 'BITSTAMP_TESTING']

currencies = [
    'BTC_ADA',
    'BTC_AVE',
    'BTC_ETH',
    'USDT_AAVE',
    'USDT_ADA',
    'USDT_APE',
    'USDT_AVAX',
    'USDT_AXS',
    'USDT_BTC', 
    'USDT_CHZ',
    'USDT_COMP',
    'USDT_CRV',
    'USDT_CTSI',
    'USDT_DAI',
    'USDT_FTM', 
    'USDT_FTT',
    'USDT_GRT',
    'USDT_LINK',
    'USDT_MANA',
    'USDT_MATIC',
    'USDT_PAX',
    'USDT_SAND',
    'USDT_SHIB',
    'USDT_SUSHI',
    'USDT_UNI',
    # 'USDT_XLM', # only bull bear
    'USDT_XRP'
]

# mapping anchored to poloniex symbols used for data backtesting pipeline
currencies_mapping = {
    'BITSTAMP': {
        'GBP_BTC':'BTC/GBP',
        'GBP_ETH':'ETH/GBP',
        'BTC_ETH':'ETH/BTC',
        'USDT_BTC':'BTC/USDT', 
        'BTC_AAVE':'AAVE/BTC', 
        'USDT_SUSHI':'SUSHI/USD', # * not same
        'USDT_AUDIO':'AUDIO/USD' # * not same
    }
}

frequencies = ['1min', '15min', '30min', '60min', '120min', '240min', '480min']

strategies = {
    'Buy&Hold':{
        'ids':['', '']
    },
    # 'EMACrossOverLS':{
    #     'ids':['short_ema', 'long_ema'],
    #     'short_ema':np.arange(1,101),
    #     'long_ema':np.arange(1,201)
    # }, 
    'EMACrossOverLO':{
        'ids':['short_ema', 'long_ema'],
        'short_ema':np.arange(1,101),
        'long_ema':np.arange(1,201)
    },
    'BollingerBandsLO':{
        'ids':['window', 'window_dev'],
        'window':np.arange(1,101),
        'window_dev':np.arange(1,6)
    }, 
    # 'MultiIndic':{
    #     'ids':['', '']
    # }
}

min_files = np.arange(1,865)

n_processors = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

bot_script_path = '.'

# docker & app ui configuration
image_name = 'bot_image_1.04'
# host
# timezones
app_timezone = 'Europe/London'

# volumes
abs_path_logger = '/root/fed_rlt/RL_Trader'#
abs_path_logger_local = os.getcwd()
fun_bot_names  = [
    'Halie',
    'FlyingDroid',
    'Robottle',
    'Rusty',
    'CyBot',
    'Taco',
    'HeavyMetal',
    'TopHead',
    'GobletofWires',
    'RaspberryPie',
    'FishChips',
    'AnneDroid',
    'MegaByte',
    'Cyborgan',
    'Robottoms',
    'AstroBoy',
    'Airbender',
    'SpaceNomad',
    'Chappie',
    'Garth',
    'Johnny',
    'Marcus',
    'Kronos',
    'Omega',
    'Mona',
    'BoyBot',
    'Ultron',
    'Cherry',
    'Piper',
    'Simon',
    'Opium',
    'Alexa',
    'Duster',
    'Sully',
    'Cowbot',
    'Brainy',
    'UNO',
    'Logan',
    'Achilles',
    'Micro',
    'Machina',
    'RAM',
    'BadassCyborg',
    'EVA',
    'SilverHead',
    'MetallicSoul',
    'Automata',
    'Trek',
    'Olympus',
    'Technician',
    'QuickResponder',
    'Screwie',
    'OptimusPrime',
    'TheTerminator',
    'ASIMO',
    'Dante',
    'Data',
    'Wall-E',
    'R2D2'
]