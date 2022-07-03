# from matplotlib import container
import sys, os, signal
sys.path.append('/'.join(os.getcwd().split('/')[:-1]))
import schedule
import logging
from datetime import datetime
import config
import time
import argparse
import traceback

import StratTest.bot as bot
# TODO run single bots to see if db works - here
# TODO plug this bots spanning to the app
# TODO bot deployment

# TODO sanitize/validate these inputs

if __name__=='__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--exchange_subaccount", type=str, help="name of subaccount used for the strategy")
    parser.add_argument("--pair", type=str, help="currency pair in format ccy1/ccy2")
    parser.add_argument("--strategy", type=str, help="strategy to adopt, ie EMACrossOverLO")
    parser.add_argument("--frequency", type=str, help="bot bars frequency, ie '30m'")

    parser.add_argument("--sl_type", type=str, help="stop loss type, ie trailing or static")
    parser.add_argument("--sl_pctg", type=float, default=0.05, help="stop loss as a pctg, ie for 5% 0.05")
    parser.add_argument("--owned_ccy_size", type=float, help="owned currency amount, ie in case of GBP: 1000")
    parser.add_argument("--opening_position", type=str, help="Current or Next, determines if the bot should invest immediately in case of valid signal or wait for the next one generated")

    # parser.add_argument("--indicator", type=str, help="indicator used to generate signals, ie EMAIndicator")
    parser.add_argument("--short_ema", type=int, default=-999, help="short moving average, used for crossover indicators")
    parser.add_argument("--long_ema", type=int, default=-999, help="long moving average, used for crossover indicators")
    parser.add_argument("--window", type=int, default=-999, help="moving average used for bollinger bands indicators")
    parser.add_argument("--window_dev", type=float, default=-999.0, help="number of standard deviations used for bollinger bands indicators")

    # docker container info
    parser.add_argument("--cntr_id", type=str, default=None, help="id of container where the bot is running")
    parser.add_argument("--cntr_name", type=str, default=None, help="name of container where the bot is running")

    args = parser.parse_args()

    exchange_subaccount = args.exchange_subaccount

    pair = args.pair

    strategy = args.strategy
    short_ema = args.short_ema
    long_ema = args.long_ema
    window = args.window
    window_dev = args.window_dev
    container_id = args.cntr_id
    container_name = args.cntr_name

    frequency = args.frequency
    sl_type = args.sl_type
    sl_pctg = args.sl_pctg
    owned_ccy_size = args.owned_ccy_size
    opening_position = args.opening_position

    # Call getLogger with no args to set up the handler
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    logger_name = f'{strategy} logger - {datetime.now().isoformat()}'
    logger.addHandler(logging.FileHandler(f'{config.directory_path}/StratTest/Logging/{logger_name}.log'))


    # Before launching the strategy, assert that parameters are fine
    try:
        if strategy == 'EMACrossOverLO':
            assert short_ema >=0 and long_ema >=0, f"Not a valid combination of parameters passed for strategy {strategy}, requested {short_ema}, {long_ema}"

        elif strategy =='BollingerBandsLO':
            assert window >=0 and window_dev >=0, f"Not a valid combination of parameters passed for strategy {strategy}, requested {window}, {window_dev}"
    except:
        logger.error(f'{strategy} parameters are not valid: short_ema:{short_ema}, long_ema:{long_ema}, window:{window}, window_dev:{window_dev}')

    logger.info('Importing class')

    trading_bot = bot.TradingBot(
        exchange_subaccount=exchange_subaccount,
        pair=pair, 
        strategy=strategy, 
        frequency=frequency,
        sl_type=sl_type, 
        sl_pctg=sl_pctg, 
        owned_ccy_size=owned_ccy_size,
        opening_position=opening_position,
        # strategy will pick up only relevant parameters TODO: better way to package those
        short_ema=short_ema,
        long_ema=long_ema,
        window=window,
        window_dev=window_dev,
        sandbox=False,
        container_id=container_id,
        container_name=container_name
    )

    schedule.every(10).seconds.do(trading_bot.run_bot)


    def sigint_handler(signal, frame):
        logger.info(f'Initiating protocol termination')
        trading_bot._bot_termination_protocol(signal)
        
        print('Keyboard Interrupt error caught')
        logger.info(f'Exiting the bot after protocol termination')
        sys.exit(0)

    print('new bot')
    signal.signal(signal.SIGINT, sigint_handler)

    # check that pids match
    print('##### run_bot.py', os.getpid())

    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
            

        except Exception as e:
            print(e)
            traceback.print_exc()
            schedule.clear() # cancel all jobs
            print(schedule.get_jobs())
            logger.critical(f'Bot left the scheduled job: {e}')
            break
