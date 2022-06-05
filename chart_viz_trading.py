from dash import Input, Output, State, callback, no_update, callback_context, MATCH, ALL
from dash.exceptions import PreventUpdate
from datetime import datetime
import os, signal, uuid
from subprocess import Popen, call
import dash_bootstrap_components as dbc
from chart_viz_config import bot_script_path
from chart_viz_trading_layout import new_bot_info, new_balance_fetched
from chart_viz_strategy_inputs_layout import dynamic_strategy_controls
from StratTest import db_update_tables as db_update
import json
import config
import ccxt
import json

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
        script_args = f"""--pair {pair} --strategy {strategy} --frequency {frequency} --sl_type trailing --sl_pctg {sl_bps/10000}
        --owned_ccy_size 33 --short_ema {strategy_param_1} --long_ema {strategy_param_2}
        """

        # spin up a new bot
        p = Popen([
            "python3", 
            script_path,
            "--pair", f"{pair}", # TODO check if exchange and app/data processing are using same convention
            "--strategy", f"{strategy}",
            "--frequency", f"{frequency}",
            "--sl_type", "trailing", # TODO make this dynamic from UI?
            "--sl_pctg", f"{sl_bps/10000}", # from bps to pctg
            "--owned_ccy_size", f"{33}", # TODO make dynamic from ui
            "--short_ema", f"{strategy_param_1}", # bot ui element strategy 1
            "--long_ema", f"{strategy_param_2}" # bot ui element strategy 2
        ])

        # MOCK SPIN UP NEW SCRIPT
        # new_bot_unique_id = str(uuid.uuid4())

        # # temp - use a json file to keep track of processes
        # # open existing file
        # with open("run_mock_script_store.json") as f:
        #     data = json.load(f)

        # # add new pid
        # data.update({new_bot_unique_id:[p.pid, 'active']})

        # # write back updated data
        # with open('run_mock_script_store.json', 'w') as f:
        #     json.dump(data, f)

        message = f"CREATED new {pair[0]} Bot at {datetime.now().isoformat()}. Script id: {p.pid}"
        
    # if a bot is being deleted - ie a btn liquidate has actually been clicked
    elif "trading-bot-btn-liquidate" in ctx_id.split('.')[0] and ctx_value is not None:
        
        # liquidate the targeted bot
        deleted_bot_unique_id = ctx_id.split('","type":')[0].split('{"index":"')[-1]
        print("in liquidate bot block", deleted_bot_unique_id)

        # # load processes log
        # with open("run_mock_script_store.json") as f:
        #     data = json.load(f)

        # p_id = data[deleted_bot_unique_id][0]

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

        print(str(live_bots_ui_children))
        print('(###)')
        print(existing_bots_list)
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


# handle display of strategy parameters
@callback(
    Output("trading-bot-strategy-parameter-elements", "children"),
    Input("trading-bot-strategy", "value")
)
def display_strategy_parameters(strategy):
    elements = dbc.Col([dbc.Label("Strategy parameters")]+ dynamic_strategy_controls(strategy, "bot"))
    return elements

# TODO harmonize currecy pairs with exchnage