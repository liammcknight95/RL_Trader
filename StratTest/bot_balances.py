import pandas as pd
import numpy as np
import config
import ccxt
import plotly_express as px


def get_exchange_object(account):
    ''' Create and return an exchange object for a given subaccount '''

    exchange = ccxt.bitstamp(
        {
            'apiKey': config.exchange_keys[account]['KEY'],
            'secret': config.exchange_keys[account]['SECRET']
        }
    )

    return exchange


def get_balances_conversion_rates(positive_balances_df, target_ccy='GBP', account='BITSTAMP_MAIN'):
    ''' Function that returns a dictionary of last prices for conversion rates to be used 
        as a mapping on the positive_balances_df.
        positive_balances_df: pd DataFrame of positive balances across subaccounts
        target_ccy: str, currency to convert all balances into. Default GBP
        account: str, name of account to create exchange object. Default main bitstamp account
    '''

    conversion_rates_dict = {}
    exchange = get_exchange_object(account) # does not really matter what account is passed here

    for balance_ccy in positive_balances_df.index.unique():
        # loop through each currency with balance
        if target_ccy != balance_ccy:
            try:
                response = exchange.fetchTicker(f'{balance_ccy}/{target_ccy}')
                conversion_rates_dict[balance_ccy] = response['last']
            except Exception as e:
                # if symbol not found, try the reverse?
                # TODO handle logic when currency is expressed as flipped/reversed
                # test/cleanup
                if type(e).__name__ == 'BadSymbol':
                    try:
                        response = exchange.fetchTicker(f'{target_ccy}/{balance_ccy}')
                        conversion_rates_dict[balance_ccy] = 1/response['last']
                    except Exception as e:
                        if type(e).__name__ == 'BadSymbol':
                            print(f'{balance_ccy}/{target_ccy} not found')
                else:
                    print(type(e), e)
                    pass

        else:
            conversion_rates_dict[balance_ccy] = 1

    return conversion_rates_dict


def get_all_subacc_balances(target_ccy='GBP'):
    ''' Function that fetches all subaccount balances and return an easy to use dataframe '''

    accounts = config.exchange_keys.keys()
    all_accounts_list = []

    for account in accounts:

        exchange = get_exchange_object(account)
        balances = exchange.fetch_balance()

        # keep track of all free, used and total balances
        balances_free = pd.DataFrame.from_dict(balances['free'], orient='index', columns=['free'])
        balances_used = pd.DataFrame.from_dict(balances['used'], orient='index', columns=['used'])
        balances_total = pd.DataFrame.from_dict(balances['total'], orient='index', columns=['total'])

        df_subaccount = pd.concat([balances_free, balances_used, balances_total], axis=1)
        df_subaccount['account'] = account # keep track of account balance belongs to
        all_accounts_list.append(df_subaccount)

    all_accounts_df = pd.concat(all_accounts_list)
    positive_balances_df = all_accounts_df[all_accounts_df['total']>0].copy() # filter out zero balances

    # get conversion rate mapping
    conversion_rates_dict = get_balances_conversion_rates(
        positive_balances_df, 
        target_ccy=target_ccy,
        account=account # using last account from loop above, makes no difference
    )

    # convert all balances in a common currency
    positive_balances_df['conversion_price'] = positive_balances_df.index.map(conversion_rates_dict)
    positive_balances_df[f'total_{target_ccy}'] = positive_balances_df['total']*positive_balances_df['conversion_price']

    return positive_balances_df


def plot_all_balances_sunb(positive_balances_df, target_ccy='GBP'):

    balances_fig = px.sunburst(
        positive_balances_df,
        path=["recap", "ccy", "account"],
        color="ccy",
        values=f"total_{target_ccy}",
        color_discrete_map={'(?)':'rgba(255, 0, 0, 0.0);'}, # fully transparent color
    )

    balances_fig.update_layout(
        margin = dict(t=5, l=5, r=5, b=5),
        # title=f'<b>All Accounts Recap</b>',
        # title_x=.5,
        template="plotly_dark",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        autosize=True
    )

    return balances_fig


def get_bot_performance_df(df_orders):
    ### NOTE works for long only, for short trades buy and sell would need to be inverted

    if df_orders.shape[0]>=2:
        if df_orders.shape[0] % 2 == 1: # if number of orders is odd, not all buys match a sell, need to drop last order
            df_orders = df_orders.iloc[:-1 , :]
        # create index to pivot per trade
        df_orders['trade_grouper'] = np.floor(df_orders.index / 2)

        # pivot to have buy and sell for the same trade on the same row
        perf_df = df_orders.pivot(index='trade_grouper', columns='order_direction', values=['order_quantity_filled', 'order_price_filled', 'order_fee'])
        print('####here', perf_df['order_quantity_filled']['buy'], perf_df['order_quantity_filled']['sell'].sum(), perf_df.shape[0])
        assert (perf_df['order_quantity_filled']['buy'] == perf_df['order_quantity_filled']['sell']).sum() == perf_df.shape[0], 'buy and sell trade do not all match quantity filled'
        
        perf_df['return'] = (perf_df['order_price_filled']['sell'] - perf_df['order_price_filled']['buy']) / perf_df['order_price_filled']['buy']
        perf_df['notional_entry'] = perf_df['order_quantity_filled']['buy'] * perf_df['order_price_filled']['buy']
        perf_df['notional_exit'] = perf_df['order_quantity_filled']['sell'] * perf_df['order_price_filled']['sell']

        # gross notional results
        perf_df['base_ccy_trade_gross'] = perf_df['notional_exit'] - perf_df['notional_entry']
        perf_df['base_ccy_cum_gross'] = perf_df['base_ccy_trade_gross'].cumsum()

        # net notional results
        perf_df['base_ccy_trade_net'] = perf_df['base_ccy_trade_gross'] - (perf_df['order_fee']['buy']+perf_df['order_fee']['sell'])
        perf_df['base_ccy_cum_net'] = perf_df['base_ccy_trade_net'].cumsum()
        return perf_df
    
