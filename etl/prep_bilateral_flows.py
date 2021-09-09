"""Prep dyadic LinkedIn Recruiter data for all countries."""

from collections import defaultdict, namedtuple
from os import listdir, path, pipe
import argparse
import json

import numpy as np
import pandas as pd
from scipy.stats import variation as cv
from pycountry import countries

from utils.io import save_output
from utils.misc import (no_duplicates, test_no_duplicates,
                        iso2_to_iso3, name_to_iso3, get_location_hierarchy)
from configurator import Config

CONFIG = Config()


def read_data(date):
    filename = f'{date}_LinkedInRecruiter_dffromtobase_merged_wr6.csv'
    df = pd.read_csv(
        path.join(f"{CONFIG['directories.data']['raw']}", filename),
        usecols=[
            'country_from', 'country_to', 'number_people_who_indicated',
            'query_time_round', 'query_info', 'linkedinusers_from',
            'linkedinusers_to']
    )
    replace_dict = {
        '_from': '_orig', '_to': '_dest', 'linkedin': '',
        'number_people_who_indicated': 'flow'
    }
    df.columns = df.columns.to_series().replace(replace_dict, regex=True)
    return (df.assign(query_date=df['query_time_round'].str[:-9])
              .drop(['query_time_round'], axis=1, errors='ignore'))


def fix_iso3(df, verbose=True):
    """Create iso3 columns from location names.

    Also drop rows that aren't countries and fix duplicates.
    """
    suffixes = ['orig', 'dest']
    country_names = list(
        set(df['country_orig']).union(set(df['country_dest'])))
    iso3_dict = dict(zip(
        country_names, [name_to_iso3(x, verbose) for x in country_names]))
    for x in suffixes:
        df[f'iso3_{x}'] = df[f'country_{x}'].map(iso3_dict)
    # handle null iso3s
    null_iso3 = (df['iso3_dest'].isnull() | df['iso3_orig'].isnull())
    df[null_iso3].drop_duplicates().to_csv(path.join(
        CONFIG['directories.data']['processed'], 'dropped_locations.csv'
    ), index=False)
    df = df[~null_iso3]
    # handle duplicate country names which have the same iso3
    # e.g. FYRO Macedonia and North Macedonia
    for x in suffixes:
        df[f'country_{x}'] = df[f'iso3_{x}'].apply(
            lambda x: countries.get(alpha_3=x.upper()).name
        )
    return df.drop_duplicates(
        subset=['iso3_dest', 'iso3_orig', 'query_date'])


def reshape_long_wide(df, wide_col='query_info',
                      value_cols=['users_orig', 'users_dest', 'flow'],
                      hack=True):
    """Reshape wide_col from long to wide.

    query_info column takes two values: 'r4' and 'r6_remote'
    r4 is those open to relocating,
    r6 is open to relocating AND open to remote work
    """
    if hack:
        # CHANGE THIS LATER - Tom is investigating
        # basically for now, we only trust r4
        return df[df['query_info'] == 'r4'].drop('query_info', axis=1)
        # return df[~(df['query_date'].str.startswith('2021-03-2'))].drop(
        #     [wide_col], axis=1)
    else:
        idx_cols = list(
            set([x for x in df.columns]) - set(value_cols + [wide_col])
        )
        df = df.pivot_table(index=idx_cols, columns=wide_col,
                            values=value_cols).reset_index()
        df.columns = ['_'.join(x) if '' not in x else ''.join(x)
                      for x in df.columns]
        df.columns = df.columns.to_series().replace({'_r[46]': ''}, regex=True)
        return df


def prep_population():
    """Prep file with popluation.

    Downloaded from UN Poplution Division, population in 1000s
    """
    def _helper_func(x):
        try:
            return countries.get(numeric=str(x).zfill(3)).alpha_3.lower()
        except AttributeError:
            return ''
    return pd.read_excel(
        path.join(
            f"{CONFIG['directories.data']['raw']}",
            'WPP2019_POP_F01_1_TOTAL_POPULATION_BOTH_SEXES.xlsx'),
        engine='openpyxl', header=16,
        converters={'Country code': lambda x: _helper_func(x),
                    '2020': lambda x: x * 1000}
    ).query(
        "Type == 'Country/Area'"
    ).set_index('Country code')['2020'].to_dict()


def prep_country_area():
    """Clean up file with country areas.

    Downloaded from Food and Agriculture Organization
    http://www.fao.org/faostat/en/#data/RL
    """
    return pd.read_csv(
        path.join(
            f"{CONFIG['directories.data']['raw']}",
            'FAO/FAOSTAT_data_2-1-2021.csv')
    ).dropna(subset=['Value']).assign(
        value=lambda x: x['Value'] * 10,
        iso3=lambda x: x['Area Code'].str.lower()
    ).set_index('iso3')['value'].to_dict()


def prep_gdp():
    """Clean up file with GDP."""
    df = pd.read_csv(
        path.join(
            f"{CONFIG['directories.data']['raw']}",
            'API_NY/API_NY.GDP.MKTP.CD_DS2_en_csv_v2_2001204.csv'
        ), header=2, converters={'Country Code': lambda x: str.lower(x)}).drop(
            ['Indicator Name', 'Indicator Code', 'Unnamed: 65'], axis=1
        ).melt(id_vars=['Country Name', 'Country Code'],
               var_name='year', value_name='gdp')
    # get most recent year with not-null GDP values
    df['max_year'] = df.loc[
        df['gdp'].notnull()
    ].groupby('Country Code')['year'].transform(max)
    return df.query('year ==  max_year').set_index(
        'Country Code')['gdp'].to_dict()


def prep_hdi():
    """Clean up file with HDI."""
    raise NotImplementedError


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
    contig: share a land border
    comcol: share common colonizer post 1945
    colony: have ever had a colonial link
    col45: share common colonizer pre 1945
    curcol: currently in a colonial relationship

    Maciej
    dist_pop_weighted: population-weighted average distance between
    biggest cities
    dist_biggest_cities: average distance between biggest cities
    ^ most similar to distwces
    dist_unweighted: average distance between (?) (not population weighted)
    """
    cepii = pd.read_excel(
        path.join(
            f"{CONFIG['directories.data']['raw']}",
            'CEPII_distance/dist_cepii.xls'),
        converters=dict(zip(['iso_o', 'iso_d'], [lambda x: str.lower(x)]*2))
    ).replace({'rom': 'rou'})
    maciej = pd.read_csv(
        path.join(
            f"{CONFIG['directories.data']['raw']}",
            'maciej_distance/DISTANCE.csv'),
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
    iso2_3 = dict(zip(iso2s, [iso2_to_iso3(x) for x in iso2s]))
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

    col: common official language (0 or 1); 19 languages considered
    csl: p(two random people understand a common language); >= cnl
    cnl: p(two random people share a native language)
    lp: lexical closeness of native langauges; set to 0 when cnl is 1 or 0
    also set to 0 if there is no dominant native language (e.g. India)
    lp1: tree based. 4 possibilities, 2 languages belonging to:
        0: separate family trees
        0.25: different branches of same tree (English and French),
        0.50: the same branch (English and German),
        0.75: the same sub-branch (German and Dutch)
    lp2: lexical similarity of 200 words, continuous scale 0-100
    normalized lp1, lp2 so coefficients are comparable to eachother and COL
    prox1 and prox2 are unadjusted versions of lp1 and lp2?
    """
    df = pd.read_stata(
        path.join(
            f"{CONFIG['directories.data']['raw']}",
            'CEPII_language/CEPII_language.dta'))
    # belgium & luxembourg are one row, split into 2
    blx_dict = {'Belgium': 'BEL', 'Luxembourg': 'LUX'}
    blx = df.loc[(df['iso_o'] == 'BLX') | (df['iso_d'] == 'BLX')].assign(
        country_o=df['country_o'].str.split(' and '),
        country_d=df['country_d'].str.split(' and ')
    ).explode('country_o').explode('country_d')
    blx['iso_o'] = blx['country_o'].map(blx_dict).fillna(blx['iso_o'])
    blx['iso_d'] = blx['country_d'].map(blx_dict).fillna(blx['iso_d'])
    # and, of course, append 2 rows for bel <-> lux corridor
    x = pd.DataFrame(dict(zip(
        ['iso_o', 'iso_d', 'col', 'csl', 'cnl', 'prox1',
         'lp1', 'prox2', 'lp2'],
        [['BEL', 'LUX']] + [['LUX', 'BEL']] + [[1, 1]]*3 + [[0, 0]]*4
    )))
    return pd.concat([df, blx, x]).assign(
        iso_o=lambda x: x['iso_o'].str.lower(),
        iso_d=lambda x: x['iso_d'].str.lower()
    ).set_index(['iso_o', 'iso_d']).drop(
        columns=['country_o', 'country_d', 'cle', 'cl'])


def prep_internet_usage():
    """Prep file for internet usage (as proportion of population).

    Downloaded from World Bank - International Telecommunication Union (ITU)
    World Telecommunication/ICT Indicators Database
    """
    internet_dict = pd.read_csv(
        path.join(
            f"{CONFIG['directories.data']['raw']}",
            'API_IT/API_IT.NET.USER.ZS_DS2_en_csv_v2_1928189.csv'),
        # 2018 is most recent year with complete data by country
        header=2, usecols=['Country Code', '2018'],
        converters={'Country Code': lambda x: str.lower(x)}
    ).dropna(subset=['2018']).set_index('Country Code')['2018'].to_dict()
    # filling in missing values for internet usage, I just googled them
    internet_dict.update({'tca': 81.0, 'imn': 71.0})
    return {k: v / 100 for k, v in internet_dict.items()}


def prep_eu_states():
    """Flag eu, eurozone, schengen member countries.

    Data pulled from europa.eu
    """
    return pd.read_csv(
        path.join(f"{CONFIG['directories.data']['raw']}", 'eu_countries.csv'),
        converters={'country': lambda x: countries.get(name=x).alpha_3.lower()}
    ).set_index('country')


def merge_region_subregion(df):
    """Add columns for country groups using UNSD or Abel/Cohen methods."""
    loc_df = get_location_hierarchy()
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


def sensitivity_reciprocal_pairs(df, across=True):
    """Assess if removing any collection dates increases pairs."""
    baseline = len(_get_reciprocal_pairs(df, across))
    for date in df.query_date.unique():
        recip_df = _get_reciprocal_pairs(
            df.query(f'query_date != "{date}"'), across
        )
        if len(recip_df) > baseline:
            print(f'Dropping {date} increased number of pairs by:\n\
                  {len(recip_df) - baseline}')


def _get_reciprocal_pairs(df, across=False, drop_dates=None):
    # TODO I think this could be faster/better
    # https://realpython.com/numpy-array-programming/
    id_cols = ['iso3_orig', 'iso3_dest', 'query_date']
    Countrypair = namedtuple('Countrypair', ['orig', 'dest'])
    if across & (drop_dates is not None):
        df = df[~(df['query_date'].isin(drop_dates))]
    df_pairs = df[id_cols].set_index('query_date').apply(
        Countrypair._make, 1).groupby(level=0).agg(
            lambda x: list(x.values)).to_dict()
    recips = {k: [(x.dest, x.orig) for x in v] for k, v in df_pairs.items()}
    date_pairs = {
        date: list(set(df_pairs[date]) & set(recips[date]))
        for date in df_pairs.keys()
    }
    if across:
        keep_pairs = list(set.intersection(*map(set, date_pairs.values())))
        # for hack later, instead of dropping date it should be 'expanded'
        id_cols.remove('query_date')
    else:
        keep_pairs = []
        for date, pairs in date_pairs.items():
            for pair in pairs:
                keep_pairs.append(tuple([pair[0], pair[1], date]))
    return pd.DataFrame.from_records(keep_pairs, columns=id_cols).assign(
        recip=1)


def flag_reciprocals(df, sensitivity=False, across=False):
    """Only keep reciprocal pairs by origin, destination country.

    We know that not all countries of origin are represented in these data,
    since LinkedIn only shows us the top 75 origin locations per desired
    destination, by number of users. Returns dataframe with only
    reciprocal pairs within date of collection
    or across all dates.

    Note-- this used to save a file for by date reciprocals too, but
    I don't have a need for a file like that right now, so stopped
    saving it. Create by setting across=False.
    """
    if sensitivity:
        sensitivity_reciprocal_pairs(df)
    # drop some dates to increase the number of pairs
    # this is an interative process
    drop_dates = ['2021-02-08', '2021-03-22']
    recip_df = _get_reciprocal_pairs(
        df, across, drop_dates=drop_dates)
    df = df.merge(recip_df, how='left')
    # just a lil hack
    # the recip_df for across=True doesn't use query_date as a merge_col
    # so need to fill that in w/ recip = 0
    # a better fix would be to change this in the if block for
    # _get_reciprocal_pairs (see note there)
    df['recip'] = df['recip'].fillna(0)
    df.loc[df['query_date'].isin(drop_dates), 'recip'] = 0
    return df


def get_net_migration(df, value_col='flow', add_cols=['query_date']):
    if 'recip' in df.columns:
        add_cols += ['recip']
    orig_cols = ['iso3_orig'] + add_cols
    dest_cols = ['iso3_dest'] + add_cols
    return df.assign(
        # immigrants - emigrants
        net_flow=lambda x:
        x.groupby(dest_cols)[value_col].transform(sum) -
        x.groupby(orig_cols)[value_col].transform(sum),
        # use 100 to compare w/ Gallup World Poll
        net_rate_100=lambda x: (x['net_flow'] / x['users_orig']) * 100)


def get_rank(df):
    """Add a column with the ranking of flow within each destination."""
    flow_grp = df.groupby(['query_date', 'iso3_dest'])['flow']
    return df.assign(
        rank=flow_grp.rank(ascending=False, method='first'),
        rank_norm=flow_grp.rank(ascending=False, method='first', pct=True)
    )


def get_pct_change(df, diff_col='query_date'):
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
    )


def get_variation(
    df, add_cols=None, by_cols=['country_orig', 'country_dest'],
    across_col='query_date',
    value_cols=['flow', 'net_flow', 'net_rate_100', 'users_orig',
                'users_dest', 'rank', 'rank_norm']
):
    id_cols = ['country_orig', 'country_dest']
    if len(set(by_cols) - set(id_cols)) == 0:
        assert not df[by_cols + [across_col]].duplicated().values.any()
    else:
        df = df.groupby(by_cols + [across_col])[value_cols].sum().reset_index()
    v_df = df.groupby(by_cols)[value_cols].agg(
        ['std', 'mean', 'median', 'count', cv]
    ).reset_index()
    v_df.columns = ['_'.join(x) if '' not in x
                    else ''.join(x) for x in v_df.columns]
    if add_cols:
        add_cols = list(set(add_cols) - set(value_cols))
        return v_df.merge(df[by_cols + add_cols].drop_duplicates())
    else:
        return v_df


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


def add_metadata(df):
    """So meta.

    Wrapper for many smaller functions that prep metadata to be merged on.
    Split into parts (1) where two columns are created separately for origin
    and destination and (2) where one new column is created from the
    origin, destination pair
    """
    orig_cols = df.columns
    # (1) two new columns, separate for origin + destination
    gdp_map = prep_gdp()
    area_map = prep_country_area()
    int_use = prep_internet_usage()
    pop_map = prep_population()
    for k, v in {'area': area_map, 'internet': int_use, 'gdp': gdp_map, 'pop': pop_map, 'prop': ''}.items():
        for x in ['orig', 'dest']:
            if k == 'prop':
                df[f'{k}_{x}'] = df[f'users_{x}'] / df[f'pop_{x}']
            else:
                df[f'{k}_{x}'] = df[f'iso3_{x}'].map(v)
    # (2) one new column, based on origin/destination pair
    # columns flagging EU, Schengen, EEA membership
    eu = prep_eu_states()
    for col in eu.columns:
        iso3_codes = eu[eu[col] == 1].index.values
        df[col] = df.apply(
            lambda x: 1 if (x['iso3_orig'] in iso3_codes) &
            (x['iso3_dest'] in iso3_codes) else 0,
            axis=1)
    # columns for distance, language proximity
    kwargs = {
        'how': 'left', 'left_on': ['iso3_orig', 'iso3_dest'],
        'right_index': True
    }
    df = df.merge(prep_geo(), **kwargs).merge(prep_language(), **kwargs)
    return df, list(set(df.columns) - set(orig_cols)) + \
        [f'{x}_{y}' for x in ['region', 'subregion', 'midregion']
         for y in ['orig', 'dest']]


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
            ['country_code', 'country_border_code'], [
                lambda x: iso2_to_iso3(x)]*2
        ))
    ).rename(columns={
        'country_code': 'iso3_orig', 'country_border_code': 'iso3_dest'})
    borderless = borders.loc[borders['iso3_dest'].isnull(),
                             'iso3_orig'].unique()
    df = df.merge(borders, how='left', indicator='neighbor')
    df.loc[
        (df['contig'].isnull()) & (df['neighbor'] == 'both'), 'contig'
    ] = 1
    df.loc[
        (df['contig'].isnull()) &
        (df['iso3_orig'].isin(borderless) | df['iso3_dest'].isin(borderless)),
        'contig'] = 0
    # TODO see if it's possible to fill in more missing values
    return df.drop('neighbor', axis=1)


def fix_query_date(df, cutoff=np.timedelta64(10, 'D')):
    """Adjust date of data collection for timeout errors."""
    dates = sorted([np.datetime64(x) for x in df['query_date'].unique()])
    combine_dates = {
        str(dates[n + 1]): str(dates[n])
        for n in range(0, len(dates) - 1) if dates[n+1] - dates[n] < cutoff}
    df = df.replace(combine_dates)
    # while we're here... let's add another column
    new_dates = sorted([np.datetime64(x) for x in df['query_date'].unique()])
    midpoint = np.datetime64(new_dates[round(len(new_dates) / 2)])
    df['date_centered'] = df['query_date'].apply(
        lambda x: (np.datetime64(x) - midpoint).astype(int))
    return df


def data_validation(
    df, id_cols=['country_orig', 'country_dest', 'query_date'],
    value_col='flow'
):
    """Checks and fixes before saving."""
    # TODO check for all null values and try to fill them in
    df = fill_missing_borders(df)
    df = fix_query_date(df)
    # TODO add function for checking numeric vs. categorical variables
    test_no_duplicates()
    if no_duplicates(df, id_cols, value_col, verbose=True):
        df = df.drop_duplicates(subset=id_cols, ignore_index=True)
    assert df[value_col].dtype == int
    return df


def main(date, update_chord_diagram):
    df = read_data(date).pipe(reshape_long_wide).pipe(fix_iso3)
    id_cols = ['iso3_dest', 'iso3_orig']
    assert not df[id_cols + ['query_date']].duplicated().values.any(), \
        df[df[id_cols + ['query_date']].duplicated(keep=False)]
    # see changes across data collection dates
    df.pipe(get_pct_change).pipe(save_output, 'pct_change')

    df, meta_cols = (df.pipe(merge_region_subregion).pipe(add_metadata))
    df = (df.pipe(bin_continuous_vars, ['gdp'])
            .pipe(data_validation)
            .pipe(drop_bad_rows)
            .pipe(get_rank)
            .pipe(flag_reciprocals, False, True)
            .pipe(get_net_migration))

    save_output(df, 'model_input')
    df.query('recip == 1').pipe(get_variation, meta_cols).pipe(
        save_output, 'variance_recip_pairs')
    df.drop('recip', axis=1).pipe(get_variation, meta_cols).pipe(
        save_output, 'variance')
    if update_chord_diagram:
        for grp_var in ['bin_gdp', 'midregion', 'subregion']:
            by_cols = [f'{grp_var}_orig', f'{grp_var}_dest']
            value_col = ['flow']
            (df.pipe(get_variation, by_cols=by_cols, value_cols=value_col)
               .pipe(save_output, f'chord_diagram_{grp_var}'))
            (df.query('recip == 1')
               .pipe(get_variation, by_cols=by_cols, value_cols=value_col)
               .pipe(save_output, f'chord_diagram_{grp_var}_recip'))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # sure, you could say 'look for those files that are sort of like this'
    # but I think requiring a date argument is better for avoiding
    # bugs related to incorrect versioning
    parser.add_argument(
        'date', help='date of data collection YYYY-MM-DD', type=str)
    parser.add_argument(
        '-update_chord_diagram',
        help='whether to update input data for the chord diagram',
        action='store_true'
    )
    args = parser.parse_args()
    main(**vars(args))
