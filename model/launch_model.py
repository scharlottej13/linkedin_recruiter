import pandas as pd
import os
from datetime import datetime
import argparse
from utils.io import get_working_dir

"""
version_id: auto-increment
timestamp: set in code
data_version: comes from archive folder of model input files

formula: string [need a f'n]

type: set arg string
location: set arg string
description: string
min_n: set arg
min_dest_prop: set arg
"""


class ModelVersions:
    def __init__(self):
        self.last_model_version_id = pd.read_csv(
            f"{get_working_dir()}/model-outputs/model_versions.csv"
        ).sort_values(by='version_id').iloc[-1]['version_id']

    def model_version_id(self):
        return self.last_model_version_id + 1

    def timestamp():
        return datetime.now().date()

    def data_version():
        return datetime.fromtimestamp(os.path.getctime(
            f"{get_working_dir()}/processed-data/model_input.csv"
        )).date()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('type', help='model type', type=str.lower)
    parser.add_argument('location')
    parser.add_argument('description')
    parser.add_argument('min_n')
    parser.add_argument('min_prop')
    args = parser.parse_args()
    main(args.iso3, args.destination)
