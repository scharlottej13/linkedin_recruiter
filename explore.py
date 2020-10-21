# -*- coding: utf-8 -*-
"""
Created on Fri Oct  9 10:39:43 2020

@author: johnson
"""

import pandas as pd
import numpy as np
import os
import datetime


def _working_dir():
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
    return os.path.join(_working_dir(), 'inputs')


def get_output_dir():
    return os.path.join(_working_dir(), 'outputs')


def merge_region_subregion(df):
    loc_mapper = pd.read_csv(
        os.path.join(get_input_dir(), 'UNSD-methodology.csv'),
        encoding='latin1')
    loc_mapper['ISO-alpha3 Code'] = loc_mapper['ISO-alpha3 Code'].str.lower()
    # add TWN, not recognized by UN as separate from China
    loc_mapper = loc_mapper.append(
        pd.DataFrame(
            {'Region Name': ['Asia'], 'Sub-region Name': ['Eastern Asia'],
             'ISO-alpha3 Code': ['twn']}), ignore_index=True)
    # create some dictionaries for mapping
    iso3_subreg = loc_mapper.set_index(
        'ISO-alpha3 Code')['Sub-region Name'].to_dict()
    iso3_reg = loc_mapper.set_index(
        'ISO-alpha3 Code')['Region Name'].to_dict()
    # paper from Abel & Cohen has different groups, call them "midregions"
    midreg_dict = pd.read_csv(
        os.path.join(get_input_dir(), 'abel_regions.csv')
    ).set_index('subregion_from')['midreg_from'].to_dict()
    # map from country to region, subregion, and midregion
    for flow in ['orig', 'dest']:
        df[f'{flow}_reg'] = df[f'countrycode_{flow}'].map(iso3_reg)
        df[f'{flow}_subreg'] = df[f'countrycode_{flow}'].map(iso3_subreg)
        df[f'{flow}_midreg'] = df[f'{flow}_subreg'].map(midreg_dict)
        for loc in ['reg', 'midreg', 'subreg']:
            assert not df[f'{flow}_{loc}'].isnull().values.any(), \
                df.loc[
                    df[f'{flow}_{loc}'].isnull(), f'countrycode_{flow}'
                ].unique()
    return df


def bin_continuous_vars(df, cont_vars):
    if type(cont_vars) is not list:
        cont_vars = list(cont_vars)
    cont_var_cols = []
    for var in cont_vars:
        cont_var_cols = cont_var_cols + \
            [x for x in df.columns if var in x]
    assert ((len(cont_var_cols) > 0) & (np.mod(len(cont_var_cols), 2) == 0)), \
        "Need origin and destination, one is missing"
    for col in cont_var_cols:
        labels = ['low', 'low-middle', 'middle', 'middle-high', 'high']
        df[f'{col}_bin'] = pd.qcut(
            df[f'{col}'], q=5, labels=labels
        )
    return df


# get that data
df = pd.read_csv(os.path.join(
    get_input_dir(), 'LinkedInRecruiter_dffromtobase_merged_gdp.csv'))
# basic renaming, order doesn't matter here
df.columns = df.columns.str.replace(
    '_x', '_orig').str.replace('_y', '_dest').str.replace(
        '_from', '_orig').str.replace('_to', '_dest')
df = df.rename(columns={'number_people_who_indicated': 'flow'})

df = merge_region_subregion(df)

# for naming outputs
today = datetime.datetime.now().date()

# various collapses by region level & date of data collection
# df.query('query_time_round == "2020-07-25 02:00:00"').groupby(
#     ['orig_midreg', 'dest_midreg'])['flow'].sum().to_csv(
#         os.path.join(get_output_dir(), f'july_midregion_flows_{today}.csv'))

df = bin_continuous_vars(df, ['hdi', 'gdp'])

df.query('query_time_round == "2020-07-25 02:00:00"').groupby(
    [x for x in df.columns if 'bin' in x and 'gdp' in x]
)['flow'].sum().to_csv(
    os.path.join(get_output_dir(), f'july_gdp_flows_{today}.csv'))
df.query('query_time_round == "2020-07-25 02:00:00"').groupby(
    [x for x in df.columns if 'bin' in x and 'hdi' in x]
)['flow'].sum().to_csv(
    os.path.join(get_output_dir(), f'july_hdi_flows_{today}.csv'))




















