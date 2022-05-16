from datetime import date, datetime, timedelta
from dash import Input, Output, callback
from dash.exceptions import PreventUpdate
from chart_viz_strategy_inputs_layout import dynamic_strategy_controls
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
    # end_date = pd.to_datetime('2022-01-20').date()
    return max_date, initial_viz_month, start_date, end_date


# handle display of strategy parameters
@callback(
    Output("strategy-parameter-elements", "children"),
    Input("strategy-backtest-strategy", "value")
)
def display_strategy_parameters(strategy):
    elements = dbc.Col([dbc.Label("Strategy parameters")]+ dynamic_strategy_controls(strategy, "backtest"))
    return elements