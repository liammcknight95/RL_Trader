import dash_bootstrap_components as dbc
from chart_viz_config import strategies

def dynamic_strategy_controls(strategy, input_type):
    ''' Dynamically render trading strategy inputs
        strategy: str, the type of strategyto use from the engine
        input_type: str, either "backtest" or "bot"
    '''
    if strategy == 'EMACrossOverLS' or strategy == 'EMACrossOverLO':
        return [
            dbc.Row(
                [
                    dbc.Col(
                        [
                        dbc.Label("Short EMA"),
                        dbc.Input(
                            id=f"{input_type}-strategy-param-1", 
                            type="number", 
                            min=strategies[strategy]['short_ema'].min(), 
                            max=strategies[strategy]['short_ema'].max(), 
                            value=15,
                            persistence=True
                        ),
                        ]
                    )
                ]
            ),

            dbc.Row(
                [
                    dbc.Col(
                        [
                        dbc.Label("Long EMA"),
                        dbc.Input(
                            id=f"{input_type}-strategy-param-2", 
                            type="number", 
                            min=strategies[strategy]['long_ema'].min(), 
                            max=strategies[strategy]['long_ema'].max(), 
                            value=30,
                            persistence=True
                        ),
                        ]
                    )
                ]
            ),
        ]

    elif strategy == 'BollingerBandsLO':
        return [
            dbc.Row(
                [
                    dbc.Col(
                        [
                        dbc.Label("MA window"),
                        dbc.Input(
                            id=f"{input_type}-strategy-param-1", 
                            type="number", 
                            min=strategies[strategy]['window'].min(), 
                            max=strategies[strategy]['window'].max(), 
                            value=15,
                            persistence=True
                        ),
                        ]
                    )
                ]
            ),

            dbc.Row(
                [
                    dbc.Col(
                        [
                        dbc.Label("Standard deviation factor"),
                        dbc.Input(
                            id=f"{input_type}-strategy-param-2", 
                            type="number", 
                            min=strategies[strategy]['window_dev'].min(), 
                            max=strategies[strategy]['window_dev'].max(), 
                            value=1,
                            persistence=True
                        ),
                        ]
                    )
                ]
            ),
        ]


    elif strategy == 'MultiIndic':
        return [
            dbc.Row(
                [
                    dbc.Col(
                        [
                        dbc.Label("Short EMA"),
                        dbc.Input(
                            id=f"{input_type}-strategy-param-1", 
                            type="number", 
                            min=strategies[strategy]['short_ema'].min(), 
                            max=strategies[strategy]['short_ema'].max(), 
                            value=15,
                            persistence=True
                        ),
                        ]
                    )
                ],
                style={'display': 'none'}
            ),

            dbc.Row(
                [
                    dbc.Col(
                        [
                        dbc.Label("Long EMA"),
                        dbc.Input(
                            id=f"{input_type}-strategy-param-2", 
                            type="number", 
                            min=strategies[strategy]['long_ema'].min(), 
                            max=strategies[strategy]['long_ema'].max(), 
                            value=30,
                            persistence=True
                        ),
                        ]
                    )
                ],
                style={'display': 'none'}
            ),
        ]

    elif strategy == 'Buy&Hold':
        return [
            dbc.Row(
                [
                    dbc.Col(
                        [
                        dbc.Input(
                            id=f"{input_type}-strategy-param-1",
                            persistence=True
                        ),
                        ]
                    )
                ],
                style={'display': 'none'}
            ),

            dbc.Row(
                [
                    dbc.Col(
                        [
                        dbc.Input(
                            id=f"{input_type}-strategy-param-2",
                            persistence=True
                        ),
                        ]
                    )
                ],
                style={'display': 'none'}
            ),
        ]