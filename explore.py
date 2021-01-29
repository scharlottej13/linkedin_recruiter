"""
Created on Fri Oct  9 10:39:43 2020

@author: johnson
"""

import pandas as pd
import numpy as np
import datetime
import json
from os import pipe, path
from collections import defaultdict
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from haversine import haversine


def _get_working_dir():
    pc = path.abspath("N:/johnson/linkedin_recruiter")
    mac = path.abspath("/Users/scharlottej13/Nextcloud/linkedin_recruiter")
    if path.exists(pc):
        return
    elif path.exists(mac):
        return mac
    else:
        raise AssertionError(f"could not find {pc} or {mac}")


def get_input_dir():
    return path.join(_get_working_dir(), 'inputs')


def get_output_dir():
    return path.join(_get_working_dir(), 'outputs')


def standardize_col_names(df):
    replace_dict = {'_x': '_orig', '_y': '_dest', '_from': '_orig',
                    '_to': '_dest', 'linkedin': ''}
    for k, v in replace_dict.items():
        df.columns = df.columns.str.replace(k, v)
    # df.columns = df.columns.str.replace(
    #     '_x', '_orig').str.replace('_y', '_dest').str.replace(
    #     '_from', '_orig').str.replace(
    #     '_to', '_dest').str.replace('linkedin', '')
    return (df.rename(columns={'number_people_who_indicated': 'flow'})
            .assign(query_date=df['query_time_round'].str[:-9])
            .drop(['Unnamed: 0', 'query_time_round'], axis=1, errors='ignore'))


def prep_country_area():
    """Clean up file with country areas in sq km.
    Downloaded data from World Bank
    https://data.worldbank.org/indicator/AG.LND.TOTL.K2
    """
    # TO DO Tom merges on population, could make sure it's all from
    # the same place and download straight from World Bank too
    df = pd.read_csv(path.join(get_input_dir(), 'worldbank_sqkm_2021_01_28.csv'))
    print(f"World Bank Data {df.iloc[-1][0]}")
    df = df.dropna(axis=0, subset=['Country Code']).assign(
        iso3=df['Country Code'].str.lower())
    # the most recent year w/ data for all countries is 2017
    # close enough for now, but could update this later
    df['area'] = df['2017 [YR2017]'].copy()
    # some missing values are just '..'
    df = df.loc[df['area'] != '..']
    return df.set_index('iso3')['area'].to_dict()


def merge_region_subregion(df):
    loc_mapper = pd.read_csv(
        path.join(get_input_dir(), 'UNSD-methodology.csv'), encoding='latin1')
    # manual additions missing from UNSD list
    loc_mapper = loc_mapper.append(
        pd.DataFrame(
            {'Region Name': ['Asia', 'Oceania'],
             'Sub-region Name': ['Eastern Asia', 'Micronesia'],
             'ISO-alpha3 Code': ['twn', 'nru']}
        ), ignore_index=True)
    loc_mapper = loc_mapper.assign(iso3=loc_mapper['ISO-alpha3 Code'].str.lower())
    # create some dictionaries for mapping
    iso3_subreg = loc_mapper.set_index('iso3')['Sub-region Name'].to_dict()
    iso3_reg = loc_mapper.set_index('iso3')['Region Name'].to_dict()
    # paper from Abel & Cohen has different groups, call them "midregions"
    midreg_dict = pd.read_csv(
        path.join(get_input_dir(), 'abel_regions.csv')
    ).set_index('subregion_from')['midreg_from'].to_dict()
    midreg_dict.update({'Micronesia': 'Oceania'})
    # map from country to region, subregion, and "midregion"
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
                raise KeyError
            df[f'{prefix}_{var}'] = pd.qcut(df[f'{col}'], q=5, labels=labels)
    return df


def get_haversine_distance(df):
    return df.assign(distance=df.apply(
        lambda x: haversine(x['geoloc_orig'], x['geoloc_dest']), axis=1))


def add_distance(df, min_wait=1, use_cache=True):
    cache_path = path.join(get_input_dir(), 'latlong.json')
    if not use_cache:
        # need user_agent per ToS of Nominatim
        # https://www.openstreetmap.org/copyright
        geolocator = Nominatim(user_agent='scharlottej13@gmail.com')
        # wrap in automatic error handling for timeout errors
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=min_wait)
        geo_dict = defaultdict(tuple)
        for country in df.country_dest.unique():
            loc = geocode(country)
            geo_dict.update({country: (loc.latitude, loc.longitude)})
        # cache result, do not test the gods of osm
        print("Saving results to cache")
        with open(cache_path, 'w') as fp:
            json.dump(geo_dict, fp)
    else:
        assert path.exists(cache_path)
        print("Reading from cache")
        with open(cache_path, 'r') as fp:
            geo_dict = json.load(fp)

    # grab square km from World Bank
    wb_dict = prep_country_area()

    return (df.assign(
        # could also use an apply? I think this looks cleaner
        geoloc_dest=df['country_dest'].map(geo_dict),
        geoloc_orig=df['country_orig'].map(geo_dict),
        area_dest=df['countrycode_dest'].map(wb_dict),
        area_orig=df['countrycode_orig'].map(wb_dict))
            .pipe(get_haversine_distance))


def norm_flow(df, loc):
    # assuming these are the id variables
    assert not df.duplicated(
        [f'orig_{loc}', f'dest_{loc}', 'query_date']
    ).values.any()
    df = df.assign(
        flow_rate=(df['flow'] / df['users_orig']) * 100000,
        total=df.groupby([f'orig_{loc}', 'query_date'])['flow'].transform(sum))
    df['percent'] = (df['flow'] / df['total']) * 100
    return df


def aggregate_locs(df, loc):
    return df.groupby(
        [f'orig_{loc}', f'dest_{loc}', 'query_date']
    )['flow'].sum().reset_index().assign(
        total_orig=df.groupby(
            [f'orig_{loc}', 'query_date'])['flow'].transform(sum)
    )


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
# right now I just change the filename manually
df = (
    pd.read_csv(path.join(get_input_dir(), 'LinkedInRecruiter_dffromtobase_merged_gdp_10.csv'))
        .pipe(standardize_col_names)
        .pipe(merge_region_subregion)
        .pipe(add_distance)
)

# for naming outputs
today = datetime.datetime.now().date()

# OK what do we need to save?
# TO DO
# build in archive saving
# data_validation(df).to_csv(
#     path.join(get_output_dir(), f'compare_to_july_query_{today}.csv'),
#     index=False)

df.to_csv(path.join(get_output_dir(), f'model_input_{today}.csv'), index=False)

# by "midregion"
# aggregate_locs(df, 'midreg').to_csv(
#     path.join(get_output_dir(), f'midreg_flows_{today}.csv'), index=False)

# by HDI, GDP
# df = bin_continuous_vars(df, ['hdi', 'gdp'])
# for grp_var in ['hdi', 'gdp']:
#     aggregate_locs(df, grp_var).to_csv(
#         path.join(get_output_dir(), f'{grp_var}_flows_{today}.csv'),
#         index=False)
