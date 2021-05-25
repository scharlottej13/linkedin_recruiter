import pandas as pd
from utils.io import get_working_dir


class ModelVersions:
    def __init__(self):
        self.last_model_version_id = pd.read_csv(
            f"{get_working_dir()}/model-outputs/model_versions.csv"
        ).sort_values(by='version_id').iloc[-1]['version_id']
        self._model_version_id = self.last_model_version_id

    def next_model_version_id(self):
        return self.model_version_id + 1

    @property
    def model_version_id(self):
        print("Getting model version id")
        return self._model_version_id

    @model_version_id.setter
    def model_version_id(self, x):
        print("Setting model version id")
        assert x > self.last_model_version_id
        self._model_version_id = x


