"""Prep dyadic LinkedIn Recruiter data for all countries."""

import datetime
from collections import defaultdict
from os import listdir, path, pipe, mkdir
import re

import numpy as np
import pandas as pd
from pycountry import countries, historic_countries


def _get_working_dir(custom_dir):
    pc = "N:/johnson/linkedin_recruiter"
    mac = "/Users/scharlottej13/Nextcloud/linkedin_recruiter"
    check_dirs = [pc, mac]
    if custom_dir:
        check_dirs.insert(0, custom_dir)
    for check_dir in check_dirs:
        if path.exists(check_dir):
            return check_dir
    # if this line is exectued, no path was returned
    assert any([path.exists(x) for x in check_dirs]), \
        f"Working directory not found, checked:\n {check_dirs}"


def get_input_dir(custom_dir=None):
    # TODO read in filepaths from config, then set in init
    # don't love how this f'n is called all the time
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
        '_to': '_dest', 'linkedin': '', 'countrycode': 'iso3',
        'number_people_who_indicated': 'flow', 'max': ''}
    df.columns = df.columns.to_series().replace(replace_dict, regex=True)
    drop = ['Unnamed: 0', 'query_time_round', 'normalized1', 'normalized2']
    return (df.assign(query_date=df['query_time_round'].str[:-9])
              .drop(drop, axis=1, errors='ignore'))


def prep_country_area():
    """Clean up file with country areas.

    Downloaded from Food and Agriculture Organization
    http://www.fao.org/faostat/en/#data/RL
    """
    return pd.read_csv(
        path.join(get_input_dir(), 'FAO/FAOSTAT_data_2-1-2021.csv'),
        converters={
            'Area Code': lambda x: str.lower(x),
            'Value': lambda x: x * 10
        }).dropna(subset=['Value']).set_index('Area Code')['Value'].to_dict()


def prep_geo():
    """Prep data on relevant geographic variables from CEPII.

    Includes: distance, contiguity, colonial relationships
    dist: Geodesic distances from lat/long of most populous cities
    distcap: geodesic distance between capital cities
    distw: population weighted distance, theta = 1
    distwecs: population weighted distance, theta = -1
    contig: share a border
    comcol, colony, col45, curcol: colonial relationships
    """
    return pd.read_excel(
        path.join(get_input_dir(), 'CEPII_distance/dist_cepii.xls'),
        converters=dict(zip(['iso_o', 'iso_d'], [lambda x: str.lower(x)]*2))
    ).set_index(['iso_o', 'iso_d'])


def _get_iso3(x):
    """Helper function to get iso3 from iso2."""
    country_info = countries.get(alpha_2=x)
    if country_info:
        return country_info.alpha_3
    elif historic_countries.get(alpha_2=x):
        return historic_countries.get(alpha_2=x).alpha_3
    else:
        print(f"{x} not found")


def prep_geo2():
    """Prep data on distance from Maciej Danko.

    Includes: origin, dest - origin and destination country names
    origin.NC, dest.NC - number of cities used to calculate distances (max 50)
    pop_weighted - population weighted distances
    average - average distances (no pop weights)
    biggest_cit - distance between biggest cities
    """
    df = pd.read_csv(
        path.join(get_input_dir(), 'maciej_distance/DISTANCE.csv',
        keep_default_na=False,
        # NA iso2 in origin/dest columns is not a null value
        na_values=dict(zip(['variable', 'src_ref_db', 'values'], ['NA']))
    ))
    df = df[
        (df['variable'] == 'dist_pop_weighted') &
        (df['src_ref_db'] == 'maps{R}&geosphere{R}')
    ]
    # I think this is Micronesia, should be FM TODO check w/ Maciej
    df[['origin2', 'dest2']] = df[['origin2', 'dest2']].replace('MIC', 'FM')
    # create dictionary of {iso2: iso3}, faster than looping through whole df?
    iso2s = df['origin2'].unique()
    iso2_3 = dict(zip(iso2s, [_get_iso3(x) for x in iso2s]))
    df[['origin2', 'dest2']] = df[['origin2', 'dest2']].apply(
        lambda x: x.map(iso2_3))
    return df.set_index(['origin2', 'dest2'])[['values']]


def prep_language():
    """Prep data on language overlap & proximity from CEPII.

    Paper clearly defines: col, csl, cnl, lp1, lp2. Not sure
    about the other columns.
    """
    return pd.read_stata(
        path.join(get_input_dir(), 'CEPII_language/CEPII_language.dta'),
        columns=['iso_o', 'iso_d', 'col', 'csl', 'cnl', 'lp1', 'lp2']
    ).assign(iso_o=lambda x: x['iso_o'].str.lower(),
             iso_d=lambda x: x['iso_d'].str.lower()).set_index(
                 ['iso_o', 'iso_d'])


def prep_internet_usage():
    """Prep file for internet usage (as proportion of population).

    Downloaded from World Bank - International Telecommunication Union (ITU)
    World Telecommunication/ICT Indicators Database
    """
    internet_dict = pd.read_csv(
        path.join(
            get_input_dir(),
            'API_IT/API_IT.NET.USER.ZS_DS2_en_csv_v2_1928189.csv'),
        header=2, usecols=['Country Code', '2018'],
        converters={'Country Code': lambda x: str.lower(x)}
    ).dropna(subset=['2018']).set_index('Country Code')['2018'].to_dict()
    # these are probably not very accurate, I just googled them
    internet_dict.update({'tca': 81.0, 'imn': 71.0})
    return {k: v / 100 for k, v in internet_dict.items()}


def prep_eu_states():
    """Flag eu, eurozone, schengen member countries.

    Data pulled from europa.eu
    """
    return pd.read_csv(
        path.join(get_input_dir(), 'eu_countries.csv'),
        converters={'country': lambda x: countries.get(name=x).alpha_3.lower()}
    ).set_index('country')


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


def flag_complements(df):
    """Create dataframe of only complementary origin, destination pairs.

    We know that not all countries of origin are represented in these data,
    since LinkedIn only shows us the top 75 origin locations per desired
    destination, by number of users. Return dataframe of only complement pairs.

    NOTE: Should this be within query_date or across all query_dates?
    I think this depends, but for now make it within
    """
    id_cols = ['query_date', 'country_orig', 'country_dest']
    # use list of tuples [(date, orig, dest)] b/c quick to loop over &
    # easily make a dataframe from it again at the end
    data_pairs = df[id_cols].to_records(index=False).tolist()
    complements = [(date, dest, orig) for date, orig, dest in data_pairs]
    # TODO good place for a test?
    keep_pairs = list(set(data_pairs) & set(complements))
    return df.merge(
        pd.DataFrame.from_records(keep_pairs, columns=id_cols),
        how='left', indicator='comp'
    ).assign(comp=lambda x: x['comp'].map({'left_only': 0, 'both': 1}))


def get_net_migration(df, value_col='flow', add_cols=['query_date']):
    orig_cols = ['iso3_orig'] + add_cols
    dest_cols = ['iso3_dest'] + add_cols
    has_comp = (df['comp'] == 1)
    return df.assign(
        # immigrants - emigrants
        net_flow=lambda x:
        x[has_comp].groupby(dest_cols)[value_col].transform(sum) -
        x[has_comp].groupby(orig_cols)[value_col].transform(sum),
        # use 100 to compare w/ GWP
        net_rate_100=lambda x: (x['net_flow'] / x['users_orig']) * 100)


def add_metadata(df):
    """So meta.

    Wrapper for many smaller functions that prep metadata to be merged on.
    Split into parts (1) where two columns are created separately for origin
    and destination and (2) where one new column is created from the
    origin, destination pair
    """
    # (1) two new columns, separate for origin + destination
    area_map = prep_country_area()
    int_use = prep_internet_usage()
    for k, v in {'prop': None, 'area': area_map, 'internet': int_use}.items():
        for x in ['orig', 'dest']:
            if k != 'prop':
                df[f'{k}_{x}'] = df[f'iso3_{x}'].map(v)
            else:
                df[f'{k}_{x}'] = df[f'users_{x}'] / df[f'pop_{x}']
    eu = prep_eu_states()
    new_eu_cols = [f'{x}_{y}' for x in eu.columns for y in ['orig', 'dest']]
    df = df.merge(
        eu, how='left', right_index=True, left_on='iso3_orig'
    ).merge(
        eu, how='left', right_index=True, left_on='iso3_dest',
        suffixes=('_orig', '_dest')
    # fill unmerged rows w/ 0 for columns added from 'eu'
    ).fillna(dict(zip(new_eu_cols, [0] * len(new_eu_cols)))
    # fix sneaky floats created from previous NAs
    ).astype(dict(zip(new_eu_cols, [int] * len(new_eu_cols))))
    # (2) one new column, based on origin/destination pair
    kwargs = {
        'how': 'left', 'left_on': ['iso3_orig', 'iso3_dest'],
        'right_index': True
    }
    return (
        df.merge(prep_geo(), **kwargs).merge(prep_language(), **kwargs)
        .pipe(flag_complements)
        .pipe(get_net_migration)
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
    too_big = (
        (df['query_date'] == '2020-10-08') &
        (df['iso3_dest'] == 'caf') &
        (df['iso3_orig'].isin(['usa', 'ind', 'gbr', 'deu', 'esp',
                               'can', 'pol', 'nld']))
    )
    # few of these, drop b/c should not be possible
    same = (df['iso3_dest'] == df['iso3_orig'])
    return df[~(too_big | same)]


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
