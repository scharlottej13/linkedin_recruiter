import pandas as pd
import os
from datetime import datetime
import argparse
from utils.io import get_working_dir


class ModelOptions:
    def __init__(self):


    def model_version_id(self):
        # add 1 to the last model version id
        return pd.read_csv(
            f"{get_working_dir()}/model-outputs/model_versions.csv"
        ).sort_values(by='version_id')['version_id'].max() + 1

    def timestamp():
        return datetime.now().date()

    def data_version():
        return datetime.fromtimestamp(os.path.getctime(
            f"{get_working_dir()}/processed-data/model_input.csv"
        )).date()

    def description(self):
        return f"{self.location}-{self.model_type}-{self.description}"

    def formula(self):
        raise NotImplementedError


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'model_type', help='model type', type=str.lower(),
        choices=['cohen', 'poisson', 'nb'])
    parser.add_argument(
        'location', help='location level', choices=['global', 'eu'],
        type=str.lower())
    parser.add_argument(
        'description',
        help='short description of covariates, to be appended on'
    )
    parser.add_argument(
        'covariates', help='txt file with new line separated list',
        type=lambda x: open(x, 'r'))
    parser.add_argument(
        'min_n', help='minimum number of people', type=int, default=1)
    parser.add_argument(
        'min_prop', help='min proportion of linkedin users in destination',
        type=int, default=0)
    args = parser.parse_args()
    my_model = ModelOptions(**vars(args))
