"""
Created on Fri Oct  9 10:39:43 2020

@author: johnson
"""

import datetime
import json
from collections import defaultdict
from itertools import product
from os import listdir, path, pipe

import numpy as np
import pandas as pd
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from haversine import haversine


def _get_working_dir():
    pc = path.abspath("N:/johnson/linkedin_recruiter")
    mac = path.abspath("/Users/scharlottej13/Nextcloud/linkedin_recruiter")
    if path.exists(pc):
        return pc
    elif path.exists(mac):
        return mac
    else:
        raise AssertionError(f"could not find {pc} or {mac}")


def get_input_dir():
    return path.join(_get_working_dir(), 'inputs')


def get_output_dir():
    return path.join(_get_working_dir(), 'outputs')


def get_latest_data():
    # data collected by Tom, thx Tom!
    file = 'LinkedInRecruiter_dffromtobase_merged_gdp'
    files = [x for x in listdir(get_input_dir()) if x.startswith(f'{file}')]
    if len(files) == 1:
        return files[0]
    else:
        # TODO build this out, not sure it matters right now
        raise NotImplementedError


def standardize_col_names(df):
    replace_dict = {
        '_x': '_orig', '_y': '_dest', '_from': '_orig', 'population': 'pop',
        '_to': '_dest', 'linkedin': '', 'countrycode': 'iso3'
    }
    for k, v in replace_dict.items():
        df.columns = df.columns.str.replace(k, v)
    drop_cols = ['Unnamed: 0', 'query_time_round', 'normalized1', 'normalized2']
    return (
        df.rename(columns={'number_people_who_indicated': 'flow'})
          .assign(query_date=df['query_time_round'].str[:-9])
          .drop(drop_cols, axis=1, errors='ignore')
    )


def prep_country_area():
    """Clean up file with country areas.
    Downloaded from Food and Agriculture Organization
    http://www.fao.org/faostat/en/#data/RL
    """
    df = pd.read_csv(path.join(get_input_dir(), 'FAO/FAOSTAT_data_2-1-2021.csv'))
    df = df.dropna(axis=0, subset=['Value']).assign(
        # some iso3 codes are numeric, OK locations not in LI data
        # convert to sq km from hectares
        iso3=df['Area Code'].str.lower(), Value=df['Value'] * 10)
    return df.set_index('iso3')['Value'].to_dict()


def prep_internet_usage():
    """Prep file for internet usage (as proportion of population)."""
    internet_dict = pd.read_csv(path.join(
        get_input_dir(), 'API_IT/API_IT.NET.USER.ZS_DS2_en_csv_v2_1928189.csv'),
        header=2, usecols=['Country Code', '2018'],
        converters={'Country Code': lambda x: str.lower(x)}
    ).dropna(axis=0, subset=['2018']).set_index('Country Code')['2018'].to_dict()
    # these are probably not very accurate, I just googled them
    internet_dict.update({'tca': 81.0, 'imn': 71.0})
    return {k: v / 100 for k, v in internet_dict.items()}


def merge_region_subregion(df):
    """Add columns for country groups using UNSD or Abel/Cohen methods.
    UNSD: https://unstats.un.org/unsd/methodology/m49/overview/
    Abel/Cohen: https://www.nature.com/articles/s41597-019-0089-3
    """
    loc_df = pd.read_csv(
        path.join(get_input_dir(), 'UNSD-methodology.csv'), usecols=[3, 5, 11]
    ).append(pd.DataFrame(
        {'Region Name': ['Asia', 'Oceania'],
         'Sub-region Name': ['Eastern Asia', 'Micronesia'],
         'ISO-alpha3 Code': ['twn', 'nru']}), ignore_index=True)
    loc_df = loc_df.assign(iso3=loc_df['ISO-alpha3 Code'].str.lower())
    # create some dictionaries for mapping
    subreg = loc_df.set_index('iso3')['Sub-region Name'].to_dict()
    reg = loc_df.set_index('iso3')['Region Name'].to_dict()
    # paper from Abel & Cohen has different groups, call them "midregions"
    midreg = pd.read_csv(path.join(get_input_dir(), 'abel_regions.csv')
                         ).set_index('subregion_from')['midreg_from'].to_dict()
    # map from country to region, subregion, and midregion
    for drctn in ['orig', 'dest']:
        df[f'{drctn}_reg'] = df[f'iso3_{drctn}'].map(reg)
        df[f'{drctn}_subreg'] = df[f'iso3_{drctn}'].map(subreg)
        df[f'{drctn}_midreg'] = df[f'{drctn}_subreg'].map(midreg)
        for loc in ['reg', 'midreg', 'subreg']:
            assert not df[f'{drctn}_{loc}'].isnull().values.any(), \
                df.loc[
                    df[f'{drctn}_{loc}'].isnull(), f'iso3_{drctn}'
                ].unique()
    return df


def bin_continuous_vars(df, cont_vars: list, q: int = 5):
    """Returns dataframe w/ added columns for quantiles of continuous vars.
    q <- number of quantiles
    User passes in a list of continuous variables, eg. ['gdp', 'hdi'],
    and then all columns in data containing that string are identified & binned
    """
    assert q == 5, NotImplementedError
    if type(cont_vars) is not list:
        cont_vars = list(cont_vars)
    mapper = defaultdict(list)
    for var in cont_vars:
        mapper.update({var: [x for x in df.columns if var in x]})
        cols = mapper[var]
        assert ((len(cols) > 0) & (np.mod(len(cols), 2) == 0)), \
            f"Need origin and destination, one is missing from {cols}"
    labels = ['Low', 'Low-middle', 'Middle', 'Middle-high', 'High']
    for var, col_list in mapper.items():
        for col in col_list:
            df[f'bin_{col}'] = pd.qcut(df[f'{col}'], q=q, labels=labels)
    return df


def prep_lat_long(country_dict, min_wait=1, use_cache=True):
    cache_path = path.join(get_input_dir(), 'latlong.json')
    if not use_cache:
        print("Querying Nominatim")
        # need user_agent per ToS of Nominatim
        # https://www.openstreetmap.org/copyright
        geolocator = Nominatim(user_agent='scharlottej13@gmail.com')
        # wrap in automatic error handling for timeout errors
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=min_wait)
        geo_dict = defaultdict(tuple)
        for country in country_dict.keys():
            loc = geocode(country)
            # lat, long of center of country, differs from
            # Cohen et al. use distance between capitals, but I think this is
            # more realistic for big countries, negligible for small countries
            geo_dict.update({country: (loc.latitude, loc.longitude)})
        # cache result, do not test the gods of osm
        print("Saving results to cache")
        with open(cache_path, 'w') as fp:
            json.dump(geo_dict, fp)
    else:
        assert path.exists(cache_path)
        print("Reading lat/long from cache")
        with open(cache_path, 'r') as fp:
            geo_dict = json.load(fp)
    # error w/ Dominica, != Dominican Republic
    geo_dict.update({'Dominica': [15.4150, -61.3710]})
    # convert to iso3 for consistency
    return {country_dict[k]: v for k, v in geo_dict.items()}


def add_metadata(df):
    """So meta."""
    country_dict = df[
        ['country_dest', 'iso3_dest']
    ].drop_duplicates().set_index('country_dest')['iso3_dest'].to_dict()
    for k, v in {
        # pull lat/long based on countries in data
        'geoloc': prep_lat_long(country_dict),
        'area': prep_country_area(), 'internet': prep_internet_usage()
    }.items():
        for x in ['orig', 'dest']:
            df[[f'{k}_{x}']] = df[f'iso3_{x}'].map(v)
    return df.assign(
        distance=df.apply(
            lambda x: haversine(x['geoloc_orig'], x['geoloc_dest']), axis=1),
        prop_users_orig=df['users_orig'] / df['pop_orig'],
        prop_users_dest=df['users_dest'] / df['pop_dest']
    )


def collapse(df, var, id_cols=None, value_col='flow'):
    if id_cols is None:
        id_cols = [f'orig_{var}', f'dest_{var}', 'query_date']
    return df.groupby(id_cols)[value_col].sum().reset_index()


def data_validation(df, diff_col='query_date'):
    # check percent difference between the two dates of data collection
    value_cols = ['flow', 'users_orig', 'users_dest']
    id_cols = ['iso3_dest', 'iso3_orig']
    assert not df[id_cols + [diff_col]].duplicated().values.any()
    assert not (df['flow'] == 0).values.any()
    # % chg f'n from previous row, pivot so rows are each query date
    # 1st unstack moves the id cols to the index
    # 2nd unstack(0) reshapes so value variables are columns
    return pd.pivot_table(
        df, values=value_cols, index=diff_col, columns=id_cols).fillna(
        0).pct_change(fill_method='ffill').unstack().unstack(0).reset_index(
    ).merge(
        # lastly, merge on original values
        df[id_cols + value_cols + [diff_col]],
        on=id_cols + [diff_col], how='right', suffixes=('_pct_change', '')
    ).assign(flow_std=df.groupby(id_cols)['flow'].transform('std'))


def drop_bad_rows(df):
    # found these manually using standard deviation
    big = ((df['query_date'] == '2020-10-08') &
           (df['iso3_dest'] == 'caf') &
           (df['iso3_orig'].isin(['usa', 'ind', 'gbr', 'deu', 'esp', 'can', 'pol', 'nld'])))
    # few of these, they do not belong
    same = (df['iso3_dest'] == df['iso3_orig'])
    return df[~(big | same)]


def square_data(df):
    """Add rows of set(origin country) * set(destination country).
    
    Create a "square" dataframe with cartesian product
    of origin countries and destination countries.
    NOTE: Should this be within query_date or across all query_dates?
    I think this depends on the model, but for now make it across
    """
    rows = product(df['country_orig'].unique(), df['country_dest'].unique(),
                   df['query_date'].unique())
    idx = pd.DataFrame.from_records(
        rows, columns=['country_orig', 'country_dest', 'query_date'])
    # drop these rows, cannot capture "internal" migration aspirations
    idx = idx.loc[~(idx['country_orig'] == idx['country_dest'])]
    df = df.merge(
        idx, how='outer', on=['country_orig', 'country_dest', 'query_date'])
    return df


def main():
    df = (
        pd.read_csv(path.join(get_input_dir(), get_latest_data()))
          .pipe(standardize_col_names)
          .pipe(merge_region_subregion)
          .pipe(add_metadata)
          .pipe(bin_continuous_vars, ['hdi', 'gdp'])
    )
    df = square_data(df)
    # for naming outputs
    today = datetime.datetime.now().date()

    data_validation(df).to_csv(
        path.join(get_output_dir(), f'rolling_pct_change_{today}.csv'),
        index=False)
    drop_bad_rows(df).to_csv(
        path.join(get_input_dir(), f'model_input_{today}.csv'), index=False)

    # collapse by HDI, GDP, and "midregion"
    # for grp_var in ['hdi', 'gdp', 'midreg']:
    #     collapse(df, grp_var).to_csv(
    #         path.join(get_output_dir(), f'{grp_var}_flows_{today}.csv'),
    #         index=False)


if __name__ == "__main__":
    main()
