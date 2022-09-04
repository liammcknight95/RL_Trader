import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from RLT_utils.ml_data_class import MlDataClass
from sklearn.metrics import classification_report

# class for training model
class BaseRFC(MlDataClass): # data: pd.DataFrame, 
    def __init__(self, data, features: list, target: str, space: dict, cv_splits: int = 5, random_state: int = None):

        super().__init__(data)
        # self.data = data
        self.features = features
        self.target = target
        self.space = space
        self.cv_splits = cv_splits
        random_state = 5
        self.model = RandomForestClassifier(random_state=random_state)

    def train_cv_gridsearch(self):
        self.cv_inner = TimeSeriesSplit(n_splits=self.cv_splits)
        self.search = GridSearchCV(self.model, self.space, scoring='accuracy', n_jobs=-1, cv=self.cv_inner, refit=True)
        self.search.fit(self.X_train, self.y_train)
        self.grid_search_results = pd.DataFrame(self.search.cv_results_).sort_values(by='rank_test_score')
        print(f'Best accuracy score: {self.search.best_score_}, model: {self.search.best_estimator_}, params: {self.search.best_params_}')

    def make_predictions(self, trained_model):
        # call predict on best found parameters
        predictions = trained_model.predict(self.X_test)
        self.incorporate_predictions(predictions)

    def train_pipeline(self, return_lags):
        self.feature_factory(return_lags)
        self.dataset_split(target=self.target, features=self.features)
        self.train_cv_gridsearch()
        self.make_predictions(self.search)
        # print(classification_report(self.output_data['target_sign'], self.output_data['predictions']))
        return self.output_data

# in another file build a generic backtester