"""
Created on Fri Oct  9 10:39:43 2020

@author: johnson
"""

import datetime
import json
from collections import defaultdict
from os import listdir, path, pipe

import numpy as np
import pandas as pd
import pycountry
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from haversine import haversine


def _get_working_dir(custom_dir):
    pc = "N:/johnson/linkedin_recruiter"
    mac = "/Users/scharlottej13/Nextcloud/linkedin_recruiter"
    check_dirs = [pc, mac]
    if custom_dir:
        check_dirs.insert(0, custom_dir)
    for check_dir in check_dirs:
        if path.exists(check_dir):
            return check_dir
    # if this line is exectued, that means no path was returned
    assert any([path.exists(x) for x in check_dirs]), \
        f"Working directory not found, checked:\n {check_dirs}"


def get_input_dir(custom_dir=None):
    # TODO read in filepaths from config, then set in init
    return path.join(_get_working_dir(custom_dir), 'inputs')


def get_latest_data():
    # data collected by Tom, thx Tom!
    file = 'LinkedInRecruiter_dffromtobase_merged_gdp'
    files = [x for x in listdir(get_input_dir()) if x.startswith(f'{file}')]
    if len(files) == 1:
        return files[0]
    else:
        # TODO build this out, not sure it matters right now
        raise NotImplementedError


def save_output(df, filename):
    """Auto archive output saving."""
    today = datetime.datetime.now().date()
    active_dir = get_input_dir()
    archive_dir = path.join(active_dir, '_archive')
    if not path.exists(archive_dir):
        mkdir(archive_dir)
    df.to_csv(path.join(active_dir, f'{filename}.csv'), index=False)
    df.to_csv(path.join(archive_dir, f'{filename}_{today}.csv'), index=False)


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
    # some iso3 codes are numeric, OK locations not in LI data
    df = df.dropna(axis=0, subset=['Value']).assign(
        # convert to sq km from hectares (?)
        # *should* 1:100, but when you check the values it's 1:10
        iso3=df['Area Code'].str.lower(), Value=df['Value'] * 10)
    return df.set_index('iso3')['Value'].to_dict()


def _alpha2_iso3(x):
    if pd.isnull(x):
        return None
    else:
        return pycountry.countries.get(alpha_2=x).alpha_3.lower()


def prep_language():
    """Prep data on language overlap & proximity from CEPII.

    Paper clearly defines: col, csl, cnl, lp1, lp2. Not sure
    about the other columns.
    """
    df = pd.read_stata(
        path.join(get_input_dir(), 'CEPII_language.dta'),
        columns=['iso_o', 'iso_d', 'col', 'csl', 'cnl', 'lp1', 'lp2']
    ).rename(columns={'iso_o': 'iso3_orig', 'iso_d': 'iso3_dest'})
    df[['iso3_orig', 'iso3_dest']] = df[['iso3_orig', 'iso3_dest']].apply(
        lambda x: x.str.lower(), axis=1)
    return df


def prep_internet_usage():
    """Prep file for internet usage (as proportion of population).

    Downloaded from World Bank - International Telecommunication Union (ITU)
    World Telecommunication/ICT Indicators Database
    """
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
        path.join(get_input_dir(), 'UNSD-methodology.csv'), usecols=[3, 5, 11],
        header=0, names=['region', 'subregion', 'iso3']
    ).append(pd.DataFrame(
        # manually fill missing entries
        {'region': ['Asia', 'Oceania'],
         'subregion': ['Eastern Asia', 'Micronesia'],
         'iso3': ['twn', 'nru']}), ignore_index=True)
    # paper from Abel & Cohen has different groups, call them "midregions"
    loc_df = loc_df.assign(iso3=loc_df['iso3'].str.lower()).merge(
        pd.read_csv(path.join(get_input_dir(), 'abel_regions.csv')),
        how='left').set_index('iso3')
    df = df.merge(
        loc_df, how='left', left_on='iso3_orig', right_index=True).merge(
            loc_df, how='left', left_on='iso3_dest', right_index=True,
            suffixes=('_orig', '_dest'))
    new_cols = [f'{x}_{y}' for x in ['region', 'subregion', 'midregion']
                for y in ['orig', 'dest']]
    assert df[new_cols].notnull().values.any(), \
        f"Found null values:\n{df[new_cols.isnull(), new_cols]}"
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
        # TODO grab username from config
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
        assert path.exists(cache_path), f'{cache_path} not found, please check'
        print("Reading lat/long from cache")
        with open(cache_path, 'r') as fp:
            geo_dict = json.load(fp)
    # error w/ Dominica, != Dominican Republic
    geo_dict.update({'Dominica': [15.4150, -61.3710]})
    # convert to iso3 for consistency
    return {country_dict[k]: v for k, v in geo_dict.items()}


def prep_complements(df):
    """Create dataframe of only complementary origin, destination pairs.

    We know that not all countries of origin are represented in these data,
    since LinkedIn only shows us the top 75 origin locations per desired
    destination, by number of users. Return dataframe of only complement pairs.

    NOTE: Should this be within query_date or across all query_dates?
    I think this depends, but for now make it within
    """
    id_cols = ['query_date', 'country_orig', 'country_dest']
    # create list of tuples [(date, orig, dest)], quick to loop over &
    # easily make a dataframe from it again at the end
    data_pairs = df[id_cols].to_records(index=False).tolist()
    complements = [(date, dest, orig) for date, orig, dest in data_pairs]
    # TODO good place for a test I think
    keep_pairs = list(set(data_pairs) & set(complements))
    return pd.DataFrame.from_records(keep_pairs, columns=id_cols)


def add_metadata(df):
    """So meta.

    This function is a wrapper for a bunch of smaller functions
    that prep the metadata to be merged on. Split into parts (1)
    where two columns are created separately for origin and destination
    and (2) where one column is created from the origin, destination pair
    """
    # (1) two new columns, separate for origin + destination
    # pull lat/long based on countries in data
    country_dict = df[
        ['country_dest', 'iso3_dest']
    ].drop_duplicates().set_index('country_dest')['iso3_dest'].to_dict()
    # dictionary of {'new_col': function()}, where each function returns
    # metadata that is being added
    for k, v in {
        'geoloc': prep_lat_long(country_dict),
        'area': prep_country_area(), 'internet': prep_internet_usage(),
        'prop': None
    }.items():
        for x in ['orig', 'dest']:
            if k != 'prop':
                df[f'{k}_{x}'] = df[f'iso3_{x}'].map(v)
            else:
                df[f'{k}_{x}'] = df[f'users_{x}'] / df[f'pop_{x}']
    # (2) one new column, based on origin/destination pair
    complement_df = prep_complements(df)
    df = df.merge(
        border_df, how='left', indicator='border').merge(
            complement_df, how='left', indicator='complement').merge(
                prep_language(), how='left')
    df[['complement', 'border']] = df[['complement', 'border']].apply(
        lambda x: x.map({'left_only': 0, 'both': 1}), axis=1)
    return df.assign(distance=df.apply(
        lambda x: haversine(x['geoloc_orig'], x['geoloc_dest']), axis=1))


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


def main():
    df = (
        pd.read_csv(path.join(get_input_dir(), get_latest_data()))
          .pipe(standardize_col_names)
    )
    # does fun stuff like pct change, std., identify new country pairs, etc.
    save_output(data_validation(df), 'rolling_pct_change')

    (df.pipe(merge_region_subregion)
       .pipe(drop_bad_rows)
       .pipe(add_metadata)
       .pipe(bin_continuous_vars, ['hdi', 'gdp'])
       .pipe(save_output, 'model_input'))

    # collapse by HDI, GDP, and "midregion"
    # for grp_var in ['hdi', 'gdp', 'midreg']:
    #     save_output(collapse(df, grp_var), f'{grp_var}')


if __name__ == "__main__":
    main()
