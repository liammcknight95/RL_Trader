from RLT_utils.data_fetching import get_data
from sklearn.model_selection import train_test_split
import numpy as np
import pandas as pd

class MlDataClass():
    def __init__(self, input_data:pd.DataFrame):

        print('instanciated MlDataClass')
        self.input_data=input_data


    def feature_factory(self, lags:int=5, drop_na:bool=True) -> None:

        # price return based features
        try:
            self.input_data['target_return'] = self.input_data['returns'].shift(-1)
            self.input_data['target_sign'] = np.where(self.input_data['target_return']>0, 1, -1)

            lag_cols = []
            for lag in range(1, lags+1):
                col = f'ret_lag_{lag}'
                self.input_data[col] = self.input_data['returns'].shift(lag)
                lag_cols.append(col)

            if drop_na:# NAs can be problematic for the model
                self.input_data.dropna(inplace=True)

        except KeyError:
            print(f"No column named 'returns'")
            raise


    def dataset_split(self, target:str, features:list=[]) -> None:

        try:
            if not features:
                # if features list is not provided, use all columns
                features = [col for col in self.input_data.columns if col != target]
                print(f'Model features: {features}')

            self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
                self.input_data[features], 
                self.input_data[target], 
                test_size=0.2, 
                shuffle=False)

        except KeyError:
            print(f"No column named 'returns'")
            raise


    def incorporate_predictions(self, predictions:np.array) -> None:
        self.output_data = pd.DataFrame(self.y_test) # series into df
        self.output_data['predictions'] = predictions # add predictions
        self.output_data = pd.merge(self.X_test, self.output_data, left_index=True, right_index=True) # merge with features
        
        if 'Mid_Price' not in self.output_data.columns: # add price back if not in there
            self.output_data = pd.merge(self.output_data, self.input_data[['Mid_Price']], left_index=True, right_index=True, how='left')

        # reallign prediction back to actual returns - TODO: double check this is correct
        self.output_data[['target_sign', 'predictions']] = self.output_data[['target_sign', 'predictions']].shift(1)