from dash import Input, Output, State, callback, no_update, callback_context, MATCH, ALL
from datetime import datetime
import os, signal, uuid
from subprocess import Popen, call
import dash_bootstrap_components as dbc
from chart_viz_config import bot_script_path
from chart_viz_trading_layout import new_bot_info, new_balance_fetched
from chart_viz_strategy_inputs_layout import dynamic_strategy_controls
import json
import config
import ccxt

@callback(
    Output("trading-amend-bot-message", "children"),
    Input("trading-new-bot", "n_clicks"),
    Input({'type': 'trading-bot-btn-liquidate', 'index': ALL}, "n_clicks"),
    State("trading-ccy-pairs", "value"),
    prevent_initial_call=True
)
def handle_active_bots_universe(n_click_new_bot, n_click_liquidate_bot, pair):

    ctx_id = callback_context.triggered[0]['prop_id']
    ctx_value = callback_context.triggered[0]['value']
    print('bot msg', callback_context.triggered)

    # if a new bot is being created
    if ctx_id.split('.')[0] == "trading-new-bot":

        # launch the new bot
        script_path = os.path.join(bot_script_path, "run_mock_script.py")
        p = Popen(['python3', script_path])
        new_bot_unique_id = str(uuid.uuid4())

        # temp - use a json file to keep track of processes
        # open existing file
        with open("run_mock_script_store.json") as f:
            data = json.load(f)

        # add new pid
        data.update({new_bot_unique_id:[p.pid, 'active']})

        # write back updated data
        with open('run_mock_script_store.json', 'w') as f:
            json.dump(data, f)

        message = f"CREATED new {pair[0]} Bot at {datetime.now().isoformat()}. Unique id: {new_bot_unique_id}"
        
    # if a bot is being deleted - ie a btn liquidate has actually been clicked
    elif "trading-bot-btn-liquidate" in ctx_id.split('.')[0] and ctx_value is not None:
        
        # liquidate the targeted bot
        deleted_bot_unique_id = ctx_id.split('","type":')[0].split('{"index":"')[-1]
        print("in liquidate bot block", deleted_bot_unique_id)

        # load processes log
        with open("run_mock_script_store.json") as f:
            data = json.load(f)

        p_id = data[deleted_bot_unique_id][0]

        try:
            os.kill(int(p_id), signal.SIGKILL)
            data[deleted_bot_unique_id] = [p_id, 'liquidated']
            with open('run_mock_script_store.json', 'w') as f:
                json.dump(data, f)
            message = f"DELETED Bot at {datetime.now().isoformat()}. Unique id: {deleted_bot_unique_id}"

        except Exception as e:
            message = f"TRIED to delete Bot at {datetime.now().isoformat()}. {e}. PID: {p_id}.  Unique id: {deleted_bot_unique_id}"   
        
    else:
        message = 'No action performed'

    return message


@callback(
    Output("trading-live-bots-list", "children"),
    Input("trading-amend-bot-message", "children"),
    State("trading-live-bots-list", "children"),
)
def populate_running_bots_list(amend_bot_message, existing_bots_list):

    # check the callback being triggered
    ctx = callback_context.triggered[0]['prop_id']#.split('.')[0]
    print(ctx)

    # on app load or page reload
    if ctx.split('.')[0] == '':
        print('in page load block')
        live_bots_ui_children = []

        with open("run_mock_script_store.json") as f:
            bots = json.load(f)
        
        for bot_id in bots.keys():
            if bots[bot_id][1] == 'active':
                live_bots_ui_children.append(new_bot_info(bot_id))
        
        return live_bots_ui_children

    # if new bot has been created:
    elif ctx.split('.')[0] == 'trading-amend-bot-message':
        print('amending blocks')
        message_words = amend_bot_message.split()
        ui_action = message_words[0]
        bot_id = message_words[-1] # extract the unique ID from the ui message

        if ui_action == 'CREATED':
            existing_bots_list.append(new_bot_info(bot_id))

        elif ui_action == 'DELETED':
            print('deleting....')
            # find string matching unique uuid
            existing_bots_list = [elem for elem in existing_bots_list if bot_id not in str(elem)]
            ...
        return existing_bots_list

    else:
        print('#### Not captured')
        return no_update


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