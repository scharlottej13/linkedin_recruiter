import getpass
from configparser import ConfigParser, ExtendedInterpolation
from pathlib import Path
from typing import Dict, Iterable, Optional


class Config:
    def __init__(
        self,
        config_dir: Optional[Path] = None,
        config_files: Optional[Iterable[Path]] = None,
        interpolate_vars: Optional[Dict[str, str]] = None,
    ):
        self.config_dir = (
            Path(__file__).parent
            if config_dir is None
            else Path(config_dir)
        )
        config_files = (
            ["base.ini", "local.ini"]
            if config_files is None
            else [Path(file) for file in config_files]
        )

        interpolate_vars = (
            {"username": getpass.getuser()}
            if interpolate_vars is None
            else interpolate_vars
        )
        self.parser = ConfigParser(
            defaults=interpolate_vars,
            interpolation=ExtendedInterpolation(),
            converters={"path": Path},
        )
        self.config_files = self.parser.read(
            self.config_dir / file for file in config_files
        )

    def __getitem__(self, item):
        return self.parser[item]
