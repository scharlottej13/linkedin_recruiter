import pandas as pd
import os
from datetime import datetime
import argparse
from configurator import Config
import csv
import subprocess


class Covariates:
    config = Config()
    cov_list = list(pd.read_csv(
        f"{config['directories.data']['processed']}/variance.csv"
    ).columns)

    def __init__(self):
        self.number_of_covs = len(self.cov_list)
        self.dep_var = 'flow_median'
        self.distance_covs = [
            'dist_pop_weighted',
            'dist_unweighted',
            'dist_biggest_cities']
        self.geo_covs = ['contig', 'schengen', 'eurozone', 'eea', 'eu'] + \
            [x for x in self.cov_list if 'area' in x  # area_orig, area_dest eg
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
             or 'users' in x or 'pop' in x or 'gdp' in x] + self.distance_covs

    def dummy_covariates(self):
        return list(set(self.geo_covs) - set(self.numeric_covariates()))


class ModelOptions(Covariates):
    config = Config()
    model_versions = f"{config['directories.data']['model']}/model_versions.csv"
    r_script = f"{config['directories']['code']}/model/gravity_model.R"

    def __init__(self, model_type, location, description,
                 covariates, min_n, min_prop, recip_only):
        super().__init__()
        self.type = model_type[0]
        self.location = location[0]
        self.short_description = description
        self.covariates = covariates
        self.min_n = min_n
        self.min_prop = min_prop
        self.recip_only = recip_only * 1
        self.model_version_id = \
            pd.read_csv(self.model_versions).sort_values(
                by='version_id')['version_id'].max()

    @property
    def model_version_id(self):
        return self._model_version_id

    @model_version_id.setter
    def model_version_id(self, value):
        self._model_version_id = value + 1

    def timestamp(self):
        return datetime.now().date()

    def data_version(self):
        return datetime.fromtimestamp(os.path.getctime(
            f"{self.config['directories.data']['processed']}/model_input.csv"
        )).date()

    def description(self):
        return f"{self.location}-{self.type}-{self.short_description}"

    def get_log_vars(self):
        return list(
            set(self.covariates).intersection(
                set(super().log_tformed_covariates())
            )
        )

    def get_factor_vars(self):
        # variables that R needs to change to factors aka dummy variables
        return list(
            set(self.covariates).intersection(
                set(super().dummy_covariates())
            )
        )

    def get_tform_func(self, x):
        if x in self.get_log_vars():
            if self.type == 'cohen':
                func = 'log10'
            else:
                func = 'log'
        elif x in self.get_factor_vars():
            func = 'factor'
        else:
            func = None
        if func:
            return f'{func}({x})'
        else:
            return x

    def formula(self):
        if self.type == 'cohen':
            dep_var_str = f'log10({self.dep_var})'
        else:
            dep_var_str = self.dep_var
        cov_list = [
            self.get_tform_func(x) for x in self.covariates
        ]
        return f"{dep_var_str}~{'+'.join(cov_list)}"

    def update_model_versions(self):
        new_row = {
            'version_id': self.model_version_id,
            'timestamp': self.timestamp(),
            'formula': self.formula(),
            'type': self.type,
            'location': self.location,
            'description': self.description(),
            'data_version': self.data_version(),
            'min_n': self.min_n,
            'min_prop': self.min_prop,
            'recip_only': self.recip_only
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
        subprocess.run(
            ["Rscript", f"{self.r_script}", f"{self.model_version_id}"]
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'description',
        help='short description of covariates, to be appended on'
    )
    parser.add_argument(
        '--model_type', type=lambda x: str.lower(x), nargs=1,
        choices=['cohen', 'poisson', 'nb'], default=['cohen'])
    parser.add_argument(
        '--location', help='location level', nargs=1, choices=['global', 'eu'],
        type=lambda x: str.lower(x), default=['eu'])
    parser.add_argument(
        '--covariates', help='list of strings', nargs='+',
        choices=Covariates.cov_list,
        default=['dist_pop_weighted', 'area_orig', 'area_dest',
                 'users_orig_median', 'users_dest_median', 'csl',
                 'contig'])
    parser.add_argument(
        '--min_n', help='minimum count', type=int, default=1)
    parser.add_argument(
        '--min_prop', help='min proportion of linkedin users in destination',
        type=int, default=0)
    parser.add_argument('--recip_only', action='store_true')
    args = parser.parse_args()
    my_model = ModelOptions(**vars(args))
    my_model.update_model_versions()
    my_model.launch_r_model()
