import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from RLT_utils.ml_data_class import MlDataClass

# class for training model
class BaseRFC(MlDataClass): # data: pd.DataFrame, 
    def __init__(self, data, features: list, target: str, space: dict, cv_splits: int = 5, random_state: int = None):

        super().__init__(data)
        # self.data = data
        # self.features = features
        # self.target = target
        # self.space = space
        self.cv_splits = 5#cv_splits
        random_state = 5
        self.model = RandomForestClassifier(random_state=random_state)

    def train_cv_gridsearch(self):
        self.cv_inner = TimeSeriesSplit(n_splits=self.cv_splits)
        self.search = GridSearchCV(self.model, self.space, scoring='accuracy', n_jobs=-1, cv=self.cv_inner, refit=True)
        self.search.fit(self.X_train, self.y_train)
        print(f'Best accuracy score: {self.search.best_score_}, model: {self.search.best_estimator_}')
        
    def make_predictions(self, trained_model):
        predictions = trained_model.predict(self.X_test)
        results_df = pd.DataFrame(self.y_test)
        results_df['predictions'] = predictions
        results_df = pd.merge(self.X_test, results_df, left_index=True, right_index=True)
        # reallign prediction back to actual returns
        results_df[['target_sign', 'predictions']] = results_df[['target_sign', 'predictions']].shift(1)
        results_df.dropna(inplace=True)

        return results_df

# in another file build a generic backtester