from dash import Input, Output, State, callback, no_update, callback_context, MATCH, ALL
from datetime import datetime
import os, signal, uuid
from subprocess import Popen, call
from chart_viz_config import bot_script_path
from chart_viz_trading_layout import new_bot_info
import json

@callback(
    Output("trading-amend-bot-message", "children"),
    Input("trading-new-bot", "n_clicks"),
    Input({'type': 'trading-bot-btn-kill', 'index': ALL}, "n_clicks"),
    State("trading-ccy-pairs", "value"),
    prevent_initial_call=True
)
def spin_up_new_bot(n_click_new_bot, n_click_kill_bot, pair):

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
        
    # if a bot is being deleted - ie a btn kill has actually been clicked
    elif "trading-bot-btn-kill" in ctx_id.split('.')[0] and ctx_value is not None:
        
        # kill the targeted bot
        deleted_bot_unique_id = ctx_id.split('","type":')[0].split('{"index":"')[-1]
        print("in killing bot block", deleted_bot_unique_id)

        # load processes log
        with open("run_mock_script_store.json") as f:
            data = json.load(f)

        p_id = data[deleted_bot_unique_id][0]

        try:
            os.kill(int(p_id), signal.SIGKILL)
            data[deleted_bot_unique_id] = [p_id, 'killed']
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