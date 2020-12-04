"""
Created on Fri Oct  9 10:39:43 2020

@author: johnson
"""

import pandas as pd
import numpy as np
import os
import datetime
from collections import defaultdict
# from countryinfo import CountryInfo


def _get_working_dir():
    n_drive = os.path.abspath("N:/johnson/linkedin_recruiter")
    nextcloud = os.path.abspath(
        "/Users/scharlottej13/Nextcloud/linkedin_recruiter")
    if os.path.exists(n_drive):
        return n_drive
    elif os.path.exists(nextcloud):
        return nextcloud
    else:
        AssertionError, f"could not find {n_drive} or {nextcloud}"


def get_input_dir():
    return os.path.join(_get_working_dir(), 'inputs')


def get_output_dir():
    return os.path.join(_get_working_dir(), 'outputs')


def merge_region_subregion(df):
    loc_mapper = pd.read_csv(
        os.path.join(get_input_dir(), 'UNSD-methodology.csv'),
        encoding='latin1')
    loc_mapper['ISO-alpha3 Code'] = loc_mapper['ISO-alpha3 Code'].str.lower()
    # manual additions missing from UNSD list
    loc_mapper = loc_mapper.append(
        pd.DataFrame(
            {'Region Name': ['Asia', 'Oceania'],
             'Sub-region Name': ['Eastern Asia', 'Micronesia'],
             'ISO-alpha3 Code': ['twn', 'nru']}
        ), ignore_index=True)
    # create some dictionaries for mapping
    iso3_subreg = loc_mapper.set_index(
        'ISO-alpha3 Code')['Sub-region Name'].to_dict()
    iso3_reg = loc_mapper.set_index(
        'ISO-alpha3 Code')['Region Name'].to_dict()
    # paper from Abel & Cohen has different groups, call them "midregions"
    midreg_dict = pd.read_csv(
        os.path.join(get_input_dir(), 'abel_regions.csv')
    ).set_index('subregion_from')['midreg_from'].to_dict()
    midreg_dict.update({'Micronesia': 'Oceania'})
    # map from country to region, subregion, and midregion
    for drctn in ['orig', 'dest']:
        df[f'{drctn}_reg'] = df[f'countrycode_{drctn}'].map(iso3_reg)
        df[f'{drctn}_subreg'] = df[f'countrycode_{drctn}'].map(iso3_subreg)
        df[f'{drctn}_midreg'] = df[f'{drctn}_subreg'].map(midreg_dict)
        for loc in ['reg', 'midreg', 'subreg']:
            assert not df[f'{drctn}_{loc}'].isnull().values.any(), \
                df.loc[
                    df[f'{drctn}_{loc}'].isnull(), f'countrycode_{drctn}'
                ].unique()
    return df


def bin_continuous_vars(df, cont_vars):
    if type(cont_vars) is not list:
        cont_vars = list(cont_vars)
    cont_var_col_map = defaultdict(list)
    for var in cont_vars:
        cont_var_col_map.update({var: [x for x in df.columns if var in x]})
        columns = cont_var_col_map[var]
        print(f"Found these columns to bin: {columns}")
        assert ((len(columns) > 0) & (np.mod(len(columns), 2) == 0)), \
            "Need origin and destination, one is missing"
    for var, col_list in cont_var_col_map.items():
        labels = ['Low', 'Low-middle', 'Middle', 'Middle-high', 'High']
        for col in col_list:
            if 'dest' in col:
                prefix = 'dest'
            elif 'orig' in col:
                prefix = 'orig'
            else:
                KeyError
            df[f'{prefix}_{var}'] = pd.qcut(df[f'{col}'], q=5, labels=labels)
    return df


def calcuate_distance(df):
    """Calculate great ciricle distance between capital cities by country."""
    # https://pypi.org/project/countryinfo/#capital_latlng
    df = df.assign(capitol_latlng_from=lambda x: CountryInfo('country_from'))
    # and so on
    # country = CountryInfo('Singapore')
    # country.capital_latlng()
    # # returns array, approx latitude and longitude for country capital
    # [1.357107, 103.819499]
    raise NotImplementedError


def norm_flow(df, loc):
    df = df.assign(
        flow_rate=(df['flow'] / df['users_orig']) * 100000,
        total=(df.groupby(f'orig_{loc}'))['flow'].transform(sum))
    df['percent'] = (df['flow']/df['total']) * 100
    return df


def data_validation(df, baseline='2020-07-25', diff_col='query_date'):
    # first check percent difference between the two dates of data collection
    value_cols = ['flow', 'users_orig', 'users_dest']
    id_cols = ['countrycode_dest', 'countrycode_orig']
    query_rounds = list(df[f'{diff_col}'].unique())
    query_rounds.remove(baseline)
    dfs = []
    for query_round in query_rounds:
        check_df = df.query(f"{diff_col} in {[query_round, baseline]}")
        assert not check_df[id_cols + [diff_col]].duplicated().values.any()
        # % chg f'n from previous row, so pivot first to fill in 0s
        # iloc[1:] b/c now the baseline is NA
        # 1st unstack moves the id cols to the index
        # 2nd unstack(0) reshapes so value variables are columns
        check_df = pd.pivot_table(
            check_df, values=value_cols, index=diff_col, columns=id_cols
        ).fillna(0).pct_change().iloc[1:].unstack().unstack(0).reset_index(
            ).merge(
                check_df[id_cols + value_cols + [diff_col]],
                on=id_cols, how='right', suffixes=('_diff', '')
            )
        dfs.append(check_df)
    return pd.concat(dfs)


# get that data
# TO DO add this to argparse or something
# right now I just change the filename manually
df = pd.read_csv(os.path.join(
    get_input_dir(), 'LinkedInRecruiter_dffromtobase_merged_gdp_5.csv'))
# basic renaming
df.columns = df.columns.str.replace(
    '_x', '_orig').str.replace('_y', '_dest').str.replace(
        '_from', '_orig').str.replace(
            '_to', '_dest').str.replace('linkedin', '')
df = df.rename(columns={'number_people_who_indicated': 'flow'})
# remove time from query_time_round column
df['query_date'] = df['query_time_round'].str[:-9]

df = merge_region_subregion(df)

# for naming outputs
today = datetime.datetime.now().date()

# OK what do we need to save?
# data_validation(df).to_csv(
#     os.path.join(get_output_dir(), f'compare_to_july_query_{today}.csv'),
#     index=False)

# by "midregion"
value_vars = ['flow', 'users_orig', 'users_dest']
norm_flow(
    df.groupby(
        ['orig_midreg', 'dest_midreg', 'query_date']
    )[value_vars].sum().reset_index(), 'midreg'
).to_csv(os.path.join(get_output_dir(), f'midreg_flows_{today}.csv'),
         index=False)

# by HDI, GDP
df = bin_continuous_vars(df, ['hdi', 'gdp'])
for grp_var in ['hdi', 'gdp']:
    id_cols = [f'orig_{grp_var}', f'dest_{grp_var}', 'query_date']
    norm_flow(
        df.groupby(id_cols)[value_vars].sum().reset_index(), grp_var
    ).to_csv(
        os.path.join(get_output_dir(), f'{grp_var}_flows_{today}.csv'),
        index=False)
