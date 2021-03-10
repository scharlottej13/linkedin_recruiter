"""Prep dyadic LinkedIn Recruiter data for all countries."""

import datetime
from collections import defaultdict
from os import listdir, path, pipe, mkdir

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


def _get_iso3(x):
    """Helper function to get iso3 from iso2."""
    iso3 = None
    country_info = countries.get(alpha_2=x)
    if country_info:
        iso3 = country_info.alpha_3
    elif historic_countries.get(alpha_2=x):
        iso3 = historic_countries.get(alpha_2=x).alpha_3
    # Kosovo is not UN official
    elif x == 'XK':
        iso3 = 'XKX'
    else:
        print(f"Could not find iso3 for {x}")
    return iso3.lower()


def check_geo(cepii, maciej):
    """Check some assumptions."""
    assert set(cepii['iso_o']) == set(cepii['iso_d'])
    assert set(maciej['origin2']) == set(maciej['dest2'])
    diffs = set(cepii['iso_o']) - set(maciej['origin2'])
    diffs2 = set(maciej['origin2']) - set(cepii['iso_o'])
    assert len(diffs) < len(diffs2)


def prep_geo():
    """Prep data on relevant geographic variables.

    CEPII
    dist: Geodesic distances from lat/long of most populous cities
    distcap: geodesic distance between capital cities
    distw: population weighted distance, theta = 1
    distwces: population weighted distance, theta = -1
    contig: share a border
    comcol, colony, col45, curcol: colonial relationships

    Maciej
    dist_pop_weighted: average bilateral population-weighted distance
    dist_biggest_cities: average bilateral population-weighted distance
    ^ most similar distwces TODO double check w/ Maciej how these differ
    dist_unweighted: average bilateral distance TODO capital cities?
    """
    cepii =  pd.read_excel(
        path.join(get_input_dir(), 'CEPII_distance/dist_cepii.xls'),
        converters=dict(zip(['iso_o', 'iso_d'], [lambda x: str.lower(x)]*2)))
    maciej = pd.read_csv(
        path.join(get_input_dir(), 'maciej_distance/DISTANCE.csv'),
        keep_default_na=False,
        # NA iso2 in origin/dest columns is not a null value, but Namibia
        na_values=dict(zip(['variable', 'src_ref_db', 'values'], ['NA']))
    # drop cepii calculated values
    ).query("src_ref_db == 'maps{R}&geosphere{R}'").pivot(
        # reshape from long to wide on distance variable
        index=['origin2', 'dest2'], columns='variable', values='values'
    # fix micronesia, and united kingdom, checked geo_distances.csv
    ).reset_index().replace({'MIC': 'FM', 'UK': 'GB'})
    # create dictionary of {iso2: iso3}, faster than looping through whole df?
    iso2s = maciej['origin2'].unique()
    iso2_3 = dict(zip(iso2s, [_get_iso3(x) for x in iso2s]))
    # map iso2 to iso3
    maciej[['origin2', 'dest2']] = maciej[['origin2', 'dest2']].apply(
        lambda x: x.map(iso2_3))
    # some checks
    check_geo(cepii,  maciej)
    # merge two 'databases' together
    geo_df = maciej.set_index(['origin2', 'dest2']).merge(
        cepii, how='outer', left_index=True, right_on=['iso_o', 'iso_d'])
    # fill null distances TODO calculate from latlong w/ Maciej's method
    return geo_df.fillna(
        {'dist_pop_weighted': geo_df['distwces'],
         'dist_biggest_cities': geo_df['distwces'],
         'dist_unweighted': geo_df['dist']}
    ).drop(['comlang_off', 'dist', 'distcap', 'distw', 'distwces'], axis=1
    ).set_index(['iso_o', 'iso_d'])


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
        # 2018 is most recent year with complete data by country
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


def get_percent_change(df, diff_col='query_date'):
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
    # TODO check w/ Tom, I think these collection dates can be combined
    combine_dates = {'2021-01-15': '2021-01-12', '2021-02-11': '2021-02-23'}
    return df[~(too_big | same)].replace(combine_dates)


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


def fill_missing_borders(df):
    """Use country-borders to fill missing 'neighbor' values in CEPII."""
    url = "https://raw.githubusercontent.com/geodatasource/"\
          "country-borders/master/GEODATASOURCE-COUNTRY-BORDERS.CSV"
    # contains all reciprocal pairs of countries *except* if a country
    # has no land borders, then country_border_code is Null
    borders = pd.read_csv(
        url, na_values=[''], keep_default_na=False,
        usecols=['country_code', 'country_border_code'],
        converters=dict(zip(
            ['country_code', 'country_border_code'], [lambda x: _get_iso3(x)]*2
        ))
    ).rename(columns={'country_code': 'iso3_orig', 'country_border_code': 'iso3_dest'})
    borderless = borders.loc[borders['iso3_dest'].isnull(), 'iso3_orig'].unique()
    df = df.merge(borders, how='left', indicator='neighbor')
    df.loc[
        (df['contig'].isnull() & df['neighbor'] == 'both'), 'contig'
    ] = 1
    df.loc[(
        df['contig'].isnull() &
        (df['iso3_orig'].isin(borderless) | df['iso3_dest'].isin(borderless))
    ), 'contig'] = 0
    return df.drop('neighbor', axis=1)


def data_validation(
        df, id_cols=['country_orig', 'country_dest', 'query_date'],
        value_col='flow'
    ):
    """Checks and possible fixes before saving."""
    # TODO check for null values and try to fill them in
    # df = fill_missing_borders(df)
    test_no_duplicates()
    if no_duplicates(df, id_cols, value_col, verbose=True):
        df = df.drop_duplicates(subset=id_cols, ignore_index=True)
    assert df[value_col].dtype == int
    return df
    

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
    

def collapse(df, var, id_cols=None, value_col='flow'):
    if id_cols is None:
        id_cols = [f'orig_{var}', f'dest_{var}', 'query_date']
    return df.groupby(id_cols)[value_col].sum().reset_index()


def main(update_chord_diagram=False):
    df = (
        pd.read_csv(path.join(get_input_dir(), get_latest_data()))
          .pipe(standardize_col_names)
    )
    # see changes across data collection dates
    save_output(get_percent_change(df), 'rolling_pct_change')

    (df.pipe(merge_region_subregion)
       .pipe(drop_bad_rows)
       .pipe(add_metadata)
       .pipe(bin_continuous_vars, ['hdi', 'gdp'])
       .pipe(data_validation)
       .pipe(save_output, 'model_input'))

    # collapse by HDI, GDP, and "midregion"
    if update_chord_diagram:
        for grp_var in ['hdi', 'gdp', 'midreg']:
            save_output(collapse(df, grp_var), f'{grp_var}_chord_diagram')


if __name__ == "__main__":
    main()
