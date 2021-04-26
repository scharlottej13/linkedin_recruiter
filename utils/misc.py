"""Miscellaneous"""
from os import path
import pandas as pd
from pycountry import countries, historic_countries
from utils.io import get_input_dir


def get_location_hierarchy():
    """Add columns for country groups using UNSD or Abel/Cohen methods.
    UNSD: https://unstats.un.org/unsd/methodology/m49/overview/
    Abel/Cohen: https://www.nature.com/articles/s41597-019-0089-3
    """
    loc_df = pd.read_csv(
        path.join(get_input_dir(), 'UNSD-methodology.csv'), usecols=[3, 5, 11],
        header=0, names=['region', 'subregion', 'iso3']
    ).append(pd.DataFrame(
        # manually fill missing entries
        {'region': ['Asia', 'Oceania'],
         'subregion': ['Eastern Asia', 'Micronesia'],
         'iso3': ['twn', 'nru']}), ignore_index=True)
    # paper from Abel & Cohen has different groups, call them "midregions"
    return loc_df.assign(iso3=loc_df['iso3'].str.lower()).merge(
        pd.read_csv(path.join(get_input_dir(), 'abel_regions.csv')),
        how='left').set_index('iso3')


def iso2_to_iso3(x):
    """Helper function to get iso3 from iso2."""
    if x:
        country_info = countries.get(alpha_2=x)
        if country_info:
            iso3 = country_info.alpha_3
        elif historic_countries.get(alpha_2=x):
            iso3 = historic_countries.get(alpha_2=x).alpha_3
        # Kosovo is not UN official
        elif x == 'XK':
            iso3 = 'XKX'
        else:
            KeyError, f'iso3 for {x} not found'
        return iso3.lower()
    # sometimes x is Null to begin with, this f'n doesn't need to care
    else:
        return x


def no_duplicates(df, id_cols, value_col, verbose=False):
    check_cols = id_cols + [value_col]
    dups = df[df[id_cols].duplicated(keep=False)][check_cols]
    if len(dups) > 0:
        # try to fix duplicates
        # variance should be 0 if all values of value_col are the same
        var = dups.groupby(id_cols)[value_col].var()
        if (var == 0).values.all():
            return True
        else:
            if verbose:
                print(f"Flow values differ, check it!:\n {var[var != 0]}")
            return False
    else:
        return True


def test_no_duplicates():
    id_cols = ['a', 'b']
    value_col = 'c'
    df = pd.DataFrame(
        {'a': ['x', 'x', 'r', 'r'], 'b': ['y', 'y', 'p', 'p'],
         'c': [1, 1, 1, 2]}
    )
    # this should return False
    assert not no_duplicates(df, id_cols, value_col)
    df.at[3, 'c'] = 1
    # and this should return True
    assert no_duplicates(df, id_cols, value_col)
