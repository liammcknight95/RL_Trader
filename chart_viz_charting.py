from datetime import date, datetime, timedelta
from dash import Input, Output, callback
from dash.exceptions import PreventUpdate
from chart_viz_charting_layout import dynamic_strategy_controls
import data_preprocessing as dp
from StratTest.engine import TradingStrategy
import dash_bootstrap_components as dbc
import pandas as pd
from decorators.log_exceptions import exception_handler 

logged = exception_handler('chart_viz_charting: {func.__name__}')


# handle dynamic start and end date
@callback(
    Output("chart-date-picker-range", "max_date_allowed"),
    Output("chart-date-picker-range", "initial_visible_month"),
    Output("chart-date-picker-range", "start_date"),
    Output("chart-date-picker-range", "end_date"),
    Input("outer-app-container", "children")
)
def dynamic_start_end_dates(container_refresh):
    max_date = datetime.today().date()
    initial_viz_month = datetime.today() - timedelta(90)
    start_date = datetime.today().date()- timedelta(90)
    end_date = datetime.today().date() - timedelta(1)
    end_date = pd.to_datetime('2022-01-20').date()
    return max_date, initial_viz_month, start_date, end_date


# handle display of strategy parameters
@callback(
    Output("strategy-parameter-elements", "children"),
    Input("strategy-input", "value")
)
def display_strategy_parameters(strategy):
    elements = dbc.Col([dbc.Label("Strategy parameters")]+ dynamic_strategy_controls(strategy))
    return elements


# @callback(
#     Output("chart-data-session", "data"),
#     Input("currency-variable", "value"),
#     Input("chart-date-picker-range", "start_date"),
#     Input("chart-date-picker-range", "end_date")
# )
# @logged
# def cache_dataset(pair, start_date, end_date):
#     # fill this out with the logic to cache data when the inputs are changed
#     # no need to redownload the data simply when strategy parameters change
#     # decide what to do when only frequency changes
#     print(start_date, end_date, pair)
#     df_data = dp.import_data(
#         pair, 
#         start_date, 
#         end_date, 
#         include_trades=False, 
#         frequency=timedelta(seconds=60), 
#         depth=100
#     )

#     print(df_data.head())
#     print(df_data.shape)
#     # print(df_data.reset_index().to_dict('records'))
#     return df_data.reset_index().to_dict('records')


# @callback(
#     Output("strategy-graph", "figure"),
#     # Input("chart-data-session", "data"),
#     Input("strategy-input", "value"),
#     Input("data-frequency-variable", "value"),
#     Input("strategy-transaction-cost", "value"),
#     Input("strategy-stop-loss", "value"),
#     Input("strategy-param-1", "value"),
#     Input("strategy-param-2", "value"),
#     # prevent_initial_call=True
# )
# @logged
# def make_graph(strategy, frequency, transaction_cost, stop_loss, param1, param2):
#     # if cached_data is None:
#     #     raise PreventUpdate
#     # load cached data
#     data = get_minute_by_minute_cache()
#     print(data)
#     data['Datetime'] = pd.to_datetime(data['Datetime'])
#     data = data.set_index('Datetime')
#     print(data.iloc[1])
#     # convert frequency from timedelta to seconds
#     resample_freq = pd.to_timedelta(frequency)

#     trading_strategy = TradingStrategy(data, frequency=resample_freq)
#     trading_strategy.add_strategy(
#         strategy, 
#         execution_type='current_bar_close',#'next_bar_open', 'current_bar_close, 'cheat_previous_close
#         stop_loss_bps=stop_loss,
#         comms_bps=transaction_cost,
#         indicators_params=dict(    
#             # short_ema=short_ema,
#             # long_ema=long_ema
#             window=param1, 
#             window_dev=param2
#     ), # abstract parameter name
#     print_trades=False
# )
#     print(trading_strategy.df)

#     fig = trading_strategy.trading_chart(plot_strategy=True)
#     return fig