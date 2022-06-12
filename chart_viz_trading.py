from dash import Input, Output, State, callback, no_update, callback_context, MATCH, ALL
from dash.exceptions import PreventUpdate
from datetime import datetime
import os, signal, uuid
from subprocess import Popen, call
import dash_bootstrap_components as dbc
from chart_viz_config import bot_script_path, fun_bot_names, image_name, abs_path_logger, currencies_mapping
from chart_viz_trading_layout import new_bot_info, new_balance_fetched
from chart_viz_strategy_inputs_layout import dynamic_strategy_controls
from StratTest import db_update_tables as db_update
import json
import config
import ccxt
import json
import random
import docker
import time

def new_container(client, fun_bot_name):
    ''' Recursive function that tries to create a container with a random name,
        handling cases where an active container name is picked a second time.
    '''
    try:
        container_obj = client.containers.run(
            image=image_name,
            detach=True, # -d, returns a container object
            tty=True, # -t
            extra_hosts={'host.docker.internal':'host-gateway'},
            volumes={f'{abs_path_logger}/StratTest/Logging':{'bind':'/RL_Trader/StratTest/Logging', 'mode':'rw'}},
            name=fun_bot_name,
            pid_mode='host' # use the host PID namespace inside the container
        )
        print(f'New container called {fun_bot_name}')

        return container_obj

    except Exception as e:
        if 'You have to remove (or rename)' in str(e):
            print('name clash, chosing another name...')
            fun_bot_name = random.choice(fun_bot_names)
            return new_container(client, fun_bot_name)

        else: 
            print('container never created')
            return "_"
            # handle what happens here in app

@callback(
    Output("trading-amend-bot-message", "children"),
    Input("trading-new-bot", "n_clicks"),
    Input({'type': 'trading-bot-btn-liquidate', 'index': ALL}, "n_clicks"),
    State("trading-ccy-pairs", "value"),
    State("trading-bot-strategy", "value"),
    State("trading-store-freqs", "value"),
    State("trading-bot-stop-loss", "value"),
    State("bot-strategy-param-1", "value"),
    State("bot-strategy-param-2", "value"),
    prevent_initial_call=True
)
def handle_active_bots_universe(n_click_new_bot, n_click_liquidate_bot, pair, strategy, frequency, sl_bps, strategy_param_1, strategy_param_2):

    ctx_id = callback_context.triggered[0]['prop_id']
    ctx_value = callback_context.triggered[0]['value']
    print('bot msg', callback_context.triggered)

    # if a new bot is being created
    if ctx_id.split('.')[0] == "trading-new-bot":

        # launch the new bot
        script_path = os.path.join(bot_script_path, "run_bot.py") # run_mock_script

        # spin up a new bot
        # new container
        client = docker.from_env() # docker client
        container_obj = new_container(client, random.choice(fun_bot_names)) # ui name for bot returned
        fun_bot_name = container_obj.name

        # time.sleep(1)
        command_list = [
            "python3", 
            os.path.join(bot_script_path, "run_bot.py"), # run_mock_script
            "--pair", f"{pair}", # TODO check if exchange and app/data processing are using same convention
            "--strategy", f"{strategy}",
            "--frequency", f"{frequency}",
            "--sl_type", "trailing", # TODO make this dynamic from UI?
            "--sl_pctg", f"{sl_bps/10000}", # from bps to pctg
            "--owned_ccy_size", f"{33}", # TODO make dynamic from ui
            "--short_ema", f"{strategy_param_1}", # bot ui element strategy 1
            "--long_ema", f"{strategy_param_2}" # bot ui element strategy 2
        ]
        exec_results = container_obj.exec_run(
            cmd=command_list,
            stdin=True, # -i
            tty=True, # -t
            detach=True # return exec results
        )
        # Script id: {p.pid}
        # time.sleep(1)
        print('here')
        message = f"CREATED new {pair[0]} Bot at {datetime.now().isoformat()}. . Name:{fun_bot_name}"
        
    # if a bot is being deleted - ie a btn liquidate has actually been clicked
    elif "trading-bot-btn-liquidate" in ctx_id.split('.')[0] and ctx_value is not None:
        
        # liquidate the targeted bot
        deleted_bot_unique_id = ctx_id.split('","type":')[0].split('{"index":"')[-1]
        print("in liquidate bot block", deleted_bot_unique_id)

        # get program id using bot_id from - button id contains bot id that is used in database
        delete_bot_df = db_update.select_single_bot(config.pg_db_configuration(), bot_id=deleted_bot_unique_id)
        delete_bot_df_pid = delete_bot_df['bot_script_pid'].values[0]

        try:
            os.kill(int(delete_bot_df_pid), signal.SIGINT) # simulates KeyboardInterrupt
            message = f"DELETED Bot at {datetime.now().isoformat()}. PID: {delete_bot_df_pid}. Unique id: {deleted_bot_unique_id}"

        except Exception as e:
            message = f"TRIED to delete Bot at {datetime.now().isoformat()}. {e}. PID: {delete_bot_df_pid}.  Unique id: {deleted_bot_unique_id}"   
        
    else:
        message = 'No action performed'

    return message


@callback(
    Output("trading-live-bots-list", "children"),
    Output("trading-live-bots-element-python-list", "data"),
    Input("trading-amend-bot-message", "children"),
    Input("trading-live-bots-interval-refresh", "n_intervals"),
    State("trading-live-bots-element-python-list", "data"),
)
def populate_running_bots_list(amend_bot_message, refresh_live_bots, existing_bots_list):

    live_bots_ui_children = []
    active_bots_df = db_update.select_all_active_bots(config.pg_db_configuration())
    bot_ids = active_bots_df['bot_id']

    for bot_id in bot_ids:
        live_bots_ui_children.append(new_bot_info(bot_id))

    if str(live_bots_ui_children) == existing_bots_list:
        print('NO UPDATE')
        return no_update, no_update

    else:
        print('UI UPDATED')
        existing_bots_list = str(live_bots_ui_children) # assign same value

        # print(str(live_bots_ui_children))
        # print('(###)')
        # print(existing_bots_list)
        return live_bots_ui_children, existing_bots_list


@callback(
    Output("trading-non-zero-balances-free-list", "children"),
    Output("trading-non-zero-balances-used-list", "children"),
    Output("trading-non-zero-balances-total-list", "children"),
    Input("trading-live-bots-list", "children")
)
def populate_non_zero_balances(bots_list):
    print('in update balance block')
    # fetch balances - TODO better way than creating exchange obj every time
    exchange = ccxt.bitstamp(
        {
            'apiKey': config.BITSTAMP_API_KEY,
            'secret': config.BITSTAMP_API_SECRET
        }
    )

    balances = exchange.fetch_balance()

    # non zero balances
    balances_free = [new_balance_fetched(ccy, balances['free'][ccy], 'free') for ccy in balances['free'].keys() if balances['free'][ccy]!=0]
    balances_used = [new_balance_fetched(ccy, balances['used'][ccy], 'used') for ccy in balances['used'].keys() if balances['used'][ccy]!=0]
    balances_total = [new_balance_fetched(ccy, balances['total'][ccy], 'total') for ccy in balances['total'].keys() if balances['total'][ccy]!=0]

    return balances_free, balances_used, balances_total


# handle display of symbols - manual filter - given a selected exchange
@callback(
    Output("trading-ccy-pairs", "options"),
    Output("trading-ccy-pairs", "value"),
    Input("trading-ccxt-exchanges", "value")
)
def display_exchange_symbols(exchange):
    if exchange is not None:
        options=[
            {"label": cur, "value": cur} for cur in currencies_mapping[exchange].values()
        ]
        value=[options[0]["value"]] # first option as default
        return options, value
    else:
        raise PreventUpdate
        


# handle display of strategy parameters
@callback(
    Output("trading-bot-strategy-parameter-elements", "children"),
    Input("trading-bot-strategy", "value")
)
def display_strategy_parameters(strategy):
    elements = dbc.Col([dbc.Label("Strategy parameters")]+ dynamic_strategy_controls(strategy, "bot"))
    return elements
