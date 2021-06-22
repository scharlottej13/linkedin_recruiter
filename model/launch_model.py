import pandas as pd
import os
from datetime import datetime
import argparse
from utils.io import get_working_dir
import csv
import subprocess


class Covariates:
    cov_list = list(pd.read_csv(
        f"{get_working_dir()}/processed-data/variance.csv"
    ).columns)

    def __init__(self):
        self.number_of_covs = len(self.cov_list)
        self.dep_var = 'flow_median'
        self.distance_covs = [x for x in self.cov_list if 'dist' in x]
        self.geo_covs = ['contig', 'schengen', 'eurozone', 'eea', 'eu'] + \
            [x for x in self.cov_list if 'area' in x
             or 'region' in x or 'country' in x]
        self.colonizer_covs = ['col45', 'curcol', 'smctry', 'colony', 'comcol']
        self.language_covs = ['cnl', 'csl', 'col', 'prox1', 'prox2', 'lp1',
                              'lp2', 'comlang_ethno']
        self.money_covs = ['gdp_dest', 'gdp_orig', 'internet_dest',
                           'internet_orig']
        self.people_covs = [
            x for x in self.cov_list if 'users' in x
            or 'pop' in x or 'prop' in x]
        self.rank_covs = [x for x in self.cov_list if 'rank' in x]

    def dependent_variables(self):
        return [x for x in self.cov_list if 'flow' in x or 'rate' in x]

    def numeric_covariates(self):
        return \
            self.rank_covs + self.people_covs + self.money_covs + \
            self.distance_covs + ['area_orig', 'area_dest', 'cnl', 'csl',
                                  'lp2', 'prox2']

    def log_tformed_covariates(self):
        return \
            [x for x in self.numeric_covariates() if 'area' in x
             or 'users' in x or 'pop' in x] + self.distance_covs

    def dummy_covariates(self):
        return list(set(self.geo_covs) - set(self.numeric_covariates()))


class ModelOptions(Covariates):
    model_versions = f"{get_working_dir()}/model-outputs/model_versions.csv"
    r_script = f"{get_working_dir()}/model-outputs/not_that_kind_of_model.R"

    def __init__(self, model_type, location, description,
                 covariates, min_n, min_prop):
        super().__init__()
        self.type = model_type[0]
        self.location = location[0]
        self.short_description = description
        self.covariates = covariates
        self.min_n = min_n
        self.min_prop = min_prop

    def model_version_id(self):
        # add 1 to the last model version id
        return pd.read_csv(self.model_versions).sort_values(
            by='version_id')['version_id'].max() + 1

    def timestamp(self):
        return datetime.now().date()

    def data_version(self):
        return datetime.fromtimestamp(os.path.getctime(
            f"{get_working_dir()}/processed-data/model_input.csv"
        )).date()

    def description(self):
        return f"{self.location}-{self.type}-{self.short_description}"

    def log_vars(self):
        return list(
            set(self.covariates).intersection(
                set(super().log_tformed_covariates())
            )
        )

    def other_numeric_vars(self):
        # numeric covariates that should not be log transformed
        return list(
            set(self.covariates).intersection(
                set(super().numeric_covariates())
                ) - set(self.log_vars())
            )

    def factor_vars(self):
        # variables that R needs to change to factors aka dummy variables
        return list(
            set(self.covariates).intersection(
                set(super().dummy_covariates())
            )
        )

    def formula(self):
        x = [
            f'log({x})' if x in self.log_vars() else x for x in self.covariates
        ]
        return f"log({self.dep_var})~{'+'.join(x)}"

    def update_model_versions(self):
        new_row = {
            'version_id': self.model_version_id(),
            'timestamp': self.timestamp(),
            'formula': self.formula(),
            'type': self.type,
            'location': self.location,
            'description': self.description(),
            'data_version': self.data_version(),
            'factors': self.factor_vars(),
            'min_n': self.min_n,
            'min_prop': self.min_prop
        }
        # read header automatically
        with open(self.model_versions, "r") as f:
            reader = csv.reader(f)
            for header in reader:
                break
        # add row to CSV file
        with open(self.model_versions, "a") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writerow(new_row)

    def launch_r_model(self):
        subprocess.call(
            ["Rscript", f"{self.r_script}",
             "--args", f"{self.model_version_id}"]
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'model_type', help='model type', type=lambda x: str.lower(x), nargs=1,
        choices=['cohen', 'poisson', 'nb'])
    parser.add_argument(
        'location', help='location level', nargs=1, choices=['global', 'eu'],
        type=lambda x: str.lower(x))
    parser.add_argument(
        'description',
        help='short description of covariates, to be appended on'
    )
    parser.add_argument('covariates', help='list of strings', nargs='+',
                        choices=Covariates.cov_list)
    parser.add_argument(
        '--min_n', help='minimum number of people', type=int, default=1)
    parser.add_argument(
        '--min_prop', help='min proportion of linkedin users in destination',
        type=int, default=0)
    args = parser.parse_args()
    my_model = ModelOptions(**vars(args))
    my_model.update_model_versions()
    # my_model.launch_r_model()
