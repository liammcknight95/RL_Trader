import pandas as pd
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
                if type(e).__name__ == 'BadSymbol':
                    print(f'{target_ccy} not found')

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
        # title="All balances",
        color="ccy",
        values=f"total_{target_ccy}",
        color_discrete_map={'(?)':'rgba(255, 0, 0, 0.0);'}, # fully transparent color
        # color_discrete_sequence=[medimumvioletred, seagreen],
        # height=800,
    )

    balances_fig.update_layout(
        margin = dict(t=0, l=0, r=0, b=0),
        template="plotly_dark",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        autosize=True
    )

    return balances_fig