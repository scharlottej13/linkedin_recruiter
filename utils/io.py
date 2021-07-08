"""Input/output related functions."""
from os import mkdir, path
from datetime import datetime
from configurator import Config


def save_output(df, filename, subdir='processed', archive=True):
    """Auto archive output saving."""
    config = Config()
    active_dir = config['directories.data'][subdir]
    df.to_csv(path.join(active_dir, f'{filename}.csv'), index=False)
    if archive:
        today = datetime.now().date()
        archive_dir = path.join(active_dir, '_archive')
        if not path.exists(archive_dir):
            mkdir(archive_dir)
        df.to_csv(
            path.join(archive_dir, f'{filename}_{today}.csv'), index=False)
