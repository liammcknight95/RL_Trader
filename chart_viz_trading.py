from dash import html, Input, Output, State, callback, no_update, callback_context, MATCH, ALL
from dash.exceptions import PreventUpdate
from datetime import datetime
import os, signal, uuid
from subprocess import Popen, call
import dash_bootstrap_components as dbc
from chart_viz_config import bot_script_path, fun_bot_names, image_name, abs_path_logger_local, abs_path_logger, currencies_mapping, strategies
from chart_viz_trading_layout import new_bot_info, new_order_info, new_balance_fetched
from chart_viz_strategy_inputs_layout import dynamic_strategy_controls
from StratTest import db_update_tables as db_update
from StratTest import bot_plots
from StratTest import bot_balances
import json
import config
import ccxt
import json
import random
import docker
from docker.types import Mount
import time
import numpy as np

# os.environ["DOCKER_HOST"] = f"ssh://root@{configssh_server_ip_address}" 
# pg_db_configuration = config.pg_db_configuration(location='local')

# databse configuration options
@callback(
    Output("trading-db-settings-store", "data"),
    Input("trading-bot-db-settings", "value"),
    # prevent_initial_call=True
)
def get_db_configurations(config_type):
    ''' Select whether to authenticate to db local instance or the serer one. Useful for 
        development and debugging.
    '''
    try:
        print(config_type)
        pg_db_configuration = config.pg_db_configuration(location=config_type)

        # needs to be a json serializable object
        pg_db_configuration_dict = {}
        for key in pg_db_configuration.keys():
            pg_db_configuration_dict[key] = pg_db_configuration[key]

        return pg_db_configuration_dict#json.dumps(pg_db_configuration_dict)
    except Exception as e:
        print(e)
        return {}


def new_container(client, fun_bot_name, abs_path_logger):
    ''' Recursive function that tries to create a container with a random name,
        handling cases where an active container name is picked a second time.
    '''
    try:
        container_obj = client.containers.run(
            image=image_name,
            detach=True, # -d, returns a container object  # false for development mode
            tty=True, # -t
            extra_hosts={'host.docker.internal':'host-gateway'},
            volumes={f'{abs_path_logger}/StratTest/Logging':{'bind':'/RL_Trader/StratTest/Logging', 'mode':'rw'}},
            name=fun_bot_name,
            pid_mode='host', # use the host PID namespace inside the container
            auto_remove=True,
            mounts=[Mount(
                target="/RL_Trader/StratTest",
                source=f"{abs_path_logger}/StratTest",
                type='bind'
            )] # for development mode
        )
        print(f'New container called {fun_bot_name}')

        return container_obj

    except Exception as e:
        if 'You have to remove (or rename)' in str(e):
            print('name clash, chosing another name...')
            fun_bot_name = random.choice(fun_bot_names)
            return new_container(client, fun_bot_name, abs_path_logger)

        else: 
            print(e, 'container never created')
            return "_"
            # handle what happens here in app

@callback(
    Output("trading-amend-bot-message", "children"),
    Input("trading-new-bot", "n_clicks"),
    Input({'type': 'trading-bot-btn-liquidate', 'index': ALL}, "n_clicks"),
    State("trading-ccxt-exchanges", "value"),
    State("trading-ccy-pairs", "value"),
    State("trading-owned-ccy-size", "value"),
    State("trading-bot-opening-position", "value"),
    State("trading-bot-strategy", "value"),
    State("trading-bot-freqs", "value"),
    State("trading-bot-stop-loss-bps", "value"),
    State("trading-bot-stop-loss-type", "value"),
    State("bot-strategy-param-1", "value"),
    State("bot-strategy-param-2", "value"),
    State("trading-bot-db-settings", "value"),
    State("trading-db-settings-store", "data"),
    prevent_initial_call=True
)
def handle_active_bots_universe(n_click_new_bot, n_click_liquidate_bot, exchange_subaccount, pair, owned_ccy_size, opening_position, strategy, frequency, sl_bps, sl_type, strategy_param_1, strategy_param_2, config_type, pg_db_configuration):

    ctx_id = callback_context.triggered[0]['prop_id']
    ctx_value = callback_context.triggered[0]['value']
    print('bot msg', callback_context.triggered)
    print(config_type)
    # if a new bot is being created
    if ctx_id.split('.')[0] == "trading-new-bot":

        try:
            # spin up a new bot
            # new container
            if config_type == 'local': 
                print('in local block')
                os.environ["DOCKER_HOST"] = ""
                client = docker.from_env()
                path_logger=abs_path_logger_local
            elif config_type == 'server': 
                os.environ["DOCKER_HOST"] = f"ssh://root@{config.ssh_server_ip_address}" 
                client = docker.from_env(use_ssh_client=True)
                path_logger=abs_path_logger

            container_obj = new_container(client, random.choice(fun_bot_names), path_logger) # ui name for bot returned
            fun_bot_name = container_obj.name
            fun_bot_id = container_obj.id
            print(fun_bot_name, fun_bot_id)
            print(opening_position)
            print(f'#### {strategy_param_1}, {strategy_param_2} ####')

            # check that key parameters are not None
            assert pair and strategy and frequency and sl_type and sl_bps and owned_ccy_size and opening_position and strategy_param_1 and strategy_param_2
            
            command_list = [
                "python3", 
                os.path.join(bot_script_path, "StratTest/run_bot.py"), # run_mock_script
                "--exchange_subaccount", f"{exchange_subaccount}", # subaccount used for the strategy
                "--pair", f"{pair}",
                "--strategy", f"{strategy}",
                "--frequency", f"{frequency}",
                "--sl_type", f"{sl_type}", # stop loss strategy
                "--sl_pctg", f"{sl_bps/10000}", # from bps to pctg
                "--owned_ccy_size", f"{owned_ccy_size}", # how much is owned of a certain ccy at the beginning
                "--opening_position", f"{opening_position}",
                f"--{strategies[strategy]['ids'][0]}", f"{strategy_param_1}", # bot ui element strategy 1
                f"--{strategies[strategy]['ids'][1]}", f"{strategy_param_2}", # bot ui element strategy 2
                "--cntr_id", f"{fun_bot_id}",# container id where bot is running - unique
                "--cntr_name", f"{fun_bot_name}",# container name where bot is running - not unique
                "--database_setup", f"{config_type}" # type of database connectivity setup
            ]

            print(' '.join(command_list))
            
            exec_results = container_obj.exec_run(
                cmd=command_list,
                stdin=True, # -i
                tty=True, # -t
                detach=True, # return exec results
            )

            message = f"CREATED new {pair}, exec results: {exec_results}, Bot at {datetime.now().isoformat()}. . Name:{fun_bot_name}"
        
        except Exception as e:
            print(e)
            message = f"Bot NOT created, check the inputs"

    # if a bot is being deleted - ie a btn liquidate has actually been clicked
    elif "trading-bot-btn-liquidate" in ctx_id.split('.')[0] and ctx_value is not None:
        
        try:
            # liquidate the targeted bot
            deleted_bot_unique_id = ctx_id.split('","type":')[0].split('{"index":"')[-1]
            print("in liquidate bot block", deleted_bot_unique_id)

            # get program id and container id using bot_id from - button id contains bot id that is used in database
            delete_bot_df = db_update.select_single_bot(pg_db_configuration, bot_id=deleted_bot_unique_id)
            delete_bot_df_pid, delete_bot_container_id, bot_container_name = delete_bot_df["bot_script_pid"].values[0], delete_bot_df["bot_container_id"].values[0], delete_bot_df["bot_container_name"].values[0]
            print("container id: ", delete_bot_container_id, "pid: ", delete_bot_df_pid)
            # get a container object, execture program to kill bot process and finally kill container
            # client = docker.from_env(use_ssh_client=True) # docker client
            if config_type == 'local': 
                os.environ["DOCKER_HOST"] = ""
                client = docker.from_env()
            elif config_type == 'server': 
                os.environ["DOCKER_HOST"] = f"ssh://root@{config.ssh_server_ip_address}" 
                client = docker.from_env(use_ssh_client=True)
            delete_bot_container_obj = client.containers.get(delete_bot_container_id)
            delete_bot_container_obj.exec_run(f"kill -SIGINT {delete_bot_df_pid}") # simulates KeyboardInterrupt
            time.sleep(5) # allow some time for bot termination protocol
            delete_bot_container_obj.kill()

            message = f"DELETED Bot at {datetime.now().isoformat()}. NAME: {bot_container_name} PID: {delete_bot_df_pid}  Unique id: {deleted_bot_unique_id}" 

        except Exception as e:
            message = f"TRIED to delete Bot at {datetime.now().isoformat()}. {e}. NAME: {bot_container_name} PID: {delete_bot_df_pid}  Unique id: {deleted_bot_unique_id}"   
        
    else:
        message = "No action performed"

    return message


@callback(
    Output("trading-live-bots-list", "children"),
    Output("trading-live-bots-element-python-list", "data"),
    Input("trading-amend-bot-message", "children"),
    Input("trading-live-bots-interval-refresh", "n_intervals"),
    State("trading-live-bots-element-python-list", "data"),
    State("trading-db-settings-store", "data"),
    prevent_initial_call=True
)
def populate_running_bots_list(amend_bot_message, refresh_live_bots, existing_bots_list, pg_db_configuration):
    ''' Refresh running bots ui, the presence of a list with stored UI elements is there to avoid
        too many unnecessary refreshes. With many bots refreshing slightly asynchronously on different 
        containers, it will likely lead to a refesh every 5 seconds anyway
    '''

    live_bots_ui_children = []
    active_bots_df = db_update.select_active_bots_status(pg_db_configuration)
    # TODO: group all info and issue related to a certain bot in 1 row

    active_bots_df["bot_description"] = active_bots_df["bot_container_name"].astype(str) + \
    ": " + active_bots_df["bot_exchange"] + \
    " - " + active_bots_df["bot_pair"] + \
    " - " + active_bots_df["bot_owned_ccy_start_position"].astype(str) + \
    " - " + active_bots_df["bot_strategy"] + \
    " - " + active_bots_df["bot_freq"] + \
    " - " +  active_bots_df["bot_stop_loss_type"] + " stop loss of " +\
    (active_bots_df["bot_stop_loss_pctg"]*100).map('{:.2f}%'.format) +\
    active_bots_df['bot_strategy_parameters'].apply(lambda x: ' '.join([f" - {key}={x[key]}" for key in x.keys() if x[key]!=-999])) # show params

    active_bots_df["bot_last_status"] = "Update: " + active_bots_df["last_update"].astype(str) + \
        " - Status: " + active_bots_df["health_status"] + \
        "  " + active_bots_df["health_status_error"].astype(str)

    bot_ids = active_bots_df["bot_id"].unique()
    bot_descriptions = active_bots_df["bot_description"].unique()

    for bot_id, bot_description in zip(bot_ids, bot_descriptions):

        single_bot_df = active_bots_df[active_bots_df['bot_id']==bot_id]
        bot_statuses = single_bot_df["bot_last_status"].to_list()

        live_bots_ui_children.append(new_bot_info(bot_id, bot_description, bot_statuses))

        live_bots_ui_children.append(html.P(''))
        

    if str(live_bots_ui_children) == existing_bots_list:
        print("NO UPDATE")
        return no_update, no_update

    else:
        print("UI UPDATED")
        existing_bots_list = str(live_bots_ui_children) # assign same value

        # print(str(live_bots_ui_children))
        # print("(###)")
        # print(existing_bots_list)
        return live_bots_ui_children, existing_bots_list


# TODO write callback that populates ordersof running bots as well as "recently" close orders of deleted bots
@callback(
    Output("trading-running-orders-list", "children"),
    Output("trading-running-orders-element-python-list", "data"),
    Input("trading-live-bots-interval-refresh", "n_intervals"),
    State("trading-running-orders-element-python-list", "data"),
    State("trading-db-settings-store", "data"),
    prevent_initial_call=True
)
def populate_recent_bot_orders(refresh_live_bots, existing_orders_list, pg_db_configuration):
    ''' Refresh recent orders ui, the presence of a list with stored UI elements is there to avoid
        too many unnecessary refreshes. With many bots refreshing slightly asynchronously on different 
        containers, it will likely lead to a refesh every 5 seconds anyway
    '''
    running_orders_ui_children = []
    running_orders_df = db_update.select_running_orders(pg_db_configuration)
    running_orders_df["order_description"] = running_orders_df["bot_container_name"].astype(str) + \
    ": " + running_orders_df["bot_exchange"] + \
    " - " + running_orders_df["order_timestamp_placed"].astype(str)

    order_ids = running_orders_df["order_id"].to_list()
    order_general_infos = running_orders_df["order_description"].to_list()
    order_details = running_orders_df["order_trades"].astype(str).to_list()

    for order_id, general_info, detail in zip(order_ids, order_general_infos, order_details):
        running_orders_ui_children.append(new_order_info(order_id, general_info, detail))
        running_orders_ui_children.append(html.P(''))
        

    if str(running_orders_ui_children) == existing_orders_list:
        print("NO UPDATE")
        return no_update, no_update

    else:
        print("UI UPDATED")
        existing_orders_list = str(running_orders_ui_children) # assign same value

        # print(str(live_bots_ui_children))
        # print("(###)")
        # print(existing_bots_list)
        return running_orders_ui_children, existing_orders_list  

@callback(
    Output("trading-current-subacc-name", "children"),
    Output("trading-non-zero-balances-free-list", "children"),
    Output("trading-non-zero-balances-used-list", "children"),
    Output("trading-non-zero-balances-total-list", "children"),
    Output("trading-total-balances-pie-chart", "figure"),
    Input("trading-live-bots-list", "children"),
    Input("trading-ccxt-exchanges", "value"),
    prevent_initial_call=True
)
def populate_non_zero_balances(bots_list, exchange_subaccount):
    print('fetched_balances')
    positive_balances_df = bot_balances.get_all_subacc_balances(target_ccy='GBP')
    

    current_subacc_df = positive_balances_df[positive_balances_df['account']==exchange_subaccount].copy()

    balances_free = [new_balance_fetched(ccy, current_subacc_df.loc[ccy]['free'], 'free') for ccy in current_subacc_df.index if current_subacc_df.loc[ccy]['free']>0]
    balances_used = [new_balance_fetched(ccy, current_subacc_df.loc[ccy]['used'], 'used') for ccy in current_subacc_df.index if current_subacc_df.loc[ccy]['used']>0]
    balances_total = [new_balance_fetched(ccy, current_subacc_df.loc[ccy]['total'], 'total') for ccy in current_subacc_df.index if current_subacc_df.loc[ccy]['total']>0]

    # charting total balances
    positive_balances_df = positive_balances_df.reset_index().rename(columns={'index':'ccy'})
    positive_balances_df['recap'] = positive_balances_df['total_GBP'].sum().round(2).astype(str)
    balances_sunb_chart = bot_balances.plot_all_balances_sunb(positive_balances_df, target_ccy='GBP')

    return exchange_subaccount, balances_free, balances_used, balances_total, balances_sunb_chart


### SINGLE BOT STRATEGY VISUALIZATION

# populate strategy data plotting
@callback(
    Output("trading-live-bots-modal", "is_open"),
    Output("trading-live-bots-modal-title", "children"),
    Output("trading-live-bots-performance-recap", "children"),
    Output("trading-live-bots-px-chart", "figure"),
    # Output("trading-live-bots-chart-launch-dt", "children"),
    Output("trading-live-bots-chart-last-updt-dt", "children"),
    Output("trading-live-bots-orders-table", "data"),
    Output("trading-live-bots-orders-table", "columns"),
    Input({"type": "trading-bot-btn-plot", "index": ALL}, "n_clicks"),
    State("trading-live-bots-modal", "is_open"),
    State("trading-db-settings-store", "data"),
    prevent_initial_call=True
)
def plot_strategy_data(show_data_btn, modal_is_open, pg_db_configuration):

    ctx_id = callback_context.triggered[0]['prop_id']
    ctx_value = callback_context.triggered[0]['value']
    print('#####', type(ctx_id.split('.')[0]), ctx_value)
    if "trading-bot-btn-plot" in ctx_id.split('.')[0] and ctx_value is not None:
        modal_is_open = not modal_is_open
    
        if modal_is_open:
            plot_bot_unique_id = ctx_id.split('","type":')[0].split('{"index":"')[-1]
            static_df = db_update.select_single_bot(pg_db_configuration, bot_id=plot_bot_unique_id)
    
            launch_dt = static_df.iloc[0]['bot_start_date']
            launch_dt_message = f"launched on {launch_dt.strftime('%m/%d/%Y at %H:%M:%S %Z')}"

            modal_title = static_df["bot_container_name"].astype(str) + \
                " - " + static_df["bot_pair"] + \
                " - " + static_df["bot_strategy"] + \
                " (" + launch_dt_message + ")"


            bars_df = db_update.select_bot_distinct_bars(plot_bot_unique_id, pg_db_configuration)
            orders_df = db_update.select_all_bot_orders(plot_bot_unique_id, ('filled', 'pending', ), pg_db_configuration)
            print(bars_df.head(2))
            figure = bot_plots.live_bot_strategy(bars_df, orders_df, ['bar_param_1', 'bar_param_2'])
            
            last_update_time = bars_df.iloc[-1]['bar_record_timestamp']
            last_update_message = f"Last Updated: {last_update_time.strftime('%m/%d/%Y at %H:%M:%S %Z')}"

            if orders_df.shape[0]>0:
                orders_df['placed_at'] = orders_df['order_timestamp_placed'].dt.strftime('%Y-%m-%d %H:%M:%S %z')
                order_tbl_subset = ['placed_at', 'order_exchange_trade_id', 'order_status', 'order_price_filled', 'order_quantity_filled', 'order_fee']
                orders_tbl_data = orders_df[order_tbl_subset].to_dict('records')
                orders_tbl_columns = [{"name": i.replace("order_", ""), "id": i} for i in order_tbl_subset]
              
            
                if orders_df.shape[0]>=2:
                    # get order table and performance
                    performance_df = bot_balances.get_bot_performance_df(orders_df)
                    initial_position = static_df['bot_owned_ccy_start_position'].values[0]
                    position_ccy = static_df['bot_pair'].values[0].split("/")[1]
                    current_notional = (initial_position + performance_df['base_ccy_cum_net'].iloc[-1])
                    gross_notional = (initial_position + performance_df['base_ccy_cum_gross'].iloc[-1])

                    net_perf = (current_notional / initial_position) - 1
                    gross_perf = (gross_notional / initial_position) - 1

                    perf_recap = f"Net Performance: {net_perf*100:.2f}% (Gross: {gross_perf*100:.2f}%) - Notional: {current_notional:.2f} {position_ccy}"
                    
                else: # there is 1 order, but has not been closed yet
                    perf_recap = 'No orders closed yet'
            
            else: # placeholder table
                orders_tbl_data = [{}]
                orders_tbl_columns = [{"name": i.replace("order_", ""), "id": i} for i in ['']]
                perf_recap = 'No orders executed yet'

            # TODO finish plotting - get params dynamically
        # else:
        #     figure = {}
        #     print('do nothing')

        return modal_is_open, modal_title, perf_recap, figure, last_update_message, orders_tbl_data, orders_tbl_columns

    else:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update


# handle display of symbols - manual filter - given a selected exchange
@callback(
    Output("trading-ccy-pairs", "options"),
    Output("trading-ccy-pairs", "value"),
    Input("trading-ccxt-exchanges", "value")
)
def display_exchange_symbols(exchange_subaccount):
    if exchange_subaccount is not None:
        exchange = exchange_subaccount.split('_')[0]
        options=[
            {"label": cur, "value": cur} for cur in currencies_mapping[exchange].values()
        ]
        value=options[0]["value"] # first option as default
        return options, value
    else:
        raise PreventUpdate
        


# handle display of strategy parameters
@callback(
    Output("trading-bot-strategy-parameter-elements", "children"),
    Input("trading-bot-strategy", "value")
)
def display_strategy_parameters(strategy):
    elements = dbc.Col(dynamic_strategy_controls(strategy, "bot"))
    return elements
