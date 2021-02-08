"""
Created on Fri Oct  9 10:39:43 2020

@author: johnson
"""

import pandas as pd
import numpy as np
import datetime
import json
from os import pipe, path, listdir
from collections import defaultdict
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
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
        df[f'{drctn}_reg'] = df[f'iso3_{drctn}'].map(iso3_reg)
        df[f'{drctn}_subreg'] = df[f'iso3_{drctn}'].map(iso3_subreg)
        df[f'{drctn}_midreg'] = df[f'{drctn}_subreg'].map(midreg_dict)
        for loc in ['reg', 'midreg', 'subreg']:
            assert not df[f'{drctn}_{loc}'].isnull().values.any(), \
                df.loc[
                    df[f'{drctn}_{loc}'].isnull(), f'iso3_{drctn}'
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


def aggregate_locs(df, loc):
    return df.groupby(
        [f'orig_{loc}', f'dest_{loc}', 'query_date']
    )['flow'].sum().reset_index().assign(
        total_orig=df.groupby(
            [f'orig_{loc}', 'query_date'])['flow'].transform(sum)
    )


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


def main():
    df = (
        pd.read_csv(path.join(get_input_dir(), get_latest_data()))
          .pipe(standardize_col_names)
          .pipe(merge_region_subregion)
          .pipe(add_metadata)
    )

    # for naming outputs
    today = datetime.datetime.now().date()

    data_validation(df).to_csv(
        path.join(get_output_dir(), f'rolling_pct_change_{today}.csv'),
        index=False)
    drop_bad_rows(df).to_csv(
        path.join(get_output_dir(), f'model_input_{today}.csv'), index=False)

    # by "midregion"
    # aggregate_locs(df, 'midreg').to_csv(
    #     path.join(get_output_dir(), f'midreg_flows_{today}.csv'), index=False)

    # by HDI, GDP
    # df = bin_continuous_vars(df, ['hdi', 'gdp'])
    # for grp_var in ['hdi', 'gdp']:
    #     aggregate_locs(df, grp_var).to_csv(
    #         path.join(get_output_dir(), f'{grp_var}_flows_{today}.csv'),
    #         index=False)


if __name__ == "__main__":
    main()
