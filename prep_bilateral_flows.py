"""Prep dyadic LinkedIn Recruiter data for all countries."""

from datetime import datetime
from collections import defaultdict, namedtuple
from os import listdir, path, pipe, mkdir

import numpy as np
import pandas as pd
from scipy.stats import variation as cv, sem
from pycountry import countries, historic_countries

from utils import (_get_working_dir, get_input_dir, save_output,
no_duplicates, test_no_duplicates)


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
        '_to': '_dest', 'linkedin': '', 'countrycode': 'iso3',
        'number_people_who_indicated': 'flow', 'max': ''}
    df.columns = df.columns.to_series().replace(replace_dict, regex=True)
    drop = ['Unnamed: 0', 'query_time_round', 'normalized1', 'normalized2']
    return (df.assign(query_date=df['query_time_round'].str[:-9])
              .drop(drop, axis=1, errors='ignore'))


def reshape_long_wide(df, wide_col='query_info',
                      value_cols=['users_orig', 'users_dest', 'flow'],
                      hack=True):
    """Reshape wide_col from long to wide."""
    if hack:
        # CHANGE THIS LATER - Tom is investigating
        return df[~(df['query_date'].str.startswith('2021-03-2'))].drop(
            [wide_col], axis=1)
    else:
        idx_cols = list(
            set([x for x in df.columns]) - set(value_cols + [wide_col])
        )
        df = df.pivot_table(index=idx_cols, columns=wide_col,
                    values=value_cols).reset_index()
        df.columns = ['_'.join(x) if '' not in x else ''.join(x)
                    for x in df.columns]
        # query_info column takes two values: 'r4' and 'r6_remote'
        # r4 is those open to relocating, r6 is AND open to remote work
        df.columns = df.columns.to_series().replace({'_r[46]': ''}, regex=True)
        return df


def prep_country_area():
    """Clean up file with country areas.

    Downloaded from Food and Agriculture Organization
    http://www.fao.org/faostat/en/#data/RL
    """
    return pd.read_csv(
        path.join(get_input_dir(), 'FAO/FAOSTAT_data_2-1-2021.csv')
    ).dropna(subset=['Value']).assign(
        value=lambda x: x['Value'] * 10,
        iso3=lambda x: x['Area Code'].str.lower()
    ).set_index('iso3')['value'].to_dict()


def _get_iso3(x):
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
    return pd.read_stata(
        path.join(get_input_dir(), 'CEPII_language/CEPII_language.dta'),
        columns=['iso_o', 'iso_d', 'col', 'csl', 'cnl', 'prox1', 'prox2']
    ).assign(iso_o=lambda x: x['iso_o'].str.lower(),
             iso_d=lambda x: x['iso_d'].str.lower()
    ).set_index(['iso_o', 'iso_d'])


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



def _get_reciprocal_pairs(df, across=False):
    id_cols = ['iso3_orig', 'iso3_dest', 'query_date']
    Countrypair = namedtuple('Countrypair', ['orig', 'dest'])
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
        id_cols.remove('query_date')
    else:
        keep_pairs = []
        for date, pairs in date_pairs.items():
            for pair in pairs:
                keep_pairs.append(tuple([pair[0], pair[1], date]))
    return pd.DataFrame.from_records(keep_pairs, columns=id_cols)


def flag_reciprocals(df, sensitivity=False):
    """Add columns flagging reciprocal origin, destination pairs.

    We know that not all countries of origin are represented in these data,
    since LinkedIn only shows us the top 75 origin locations per desired
    destination, by number of users. Return dataframe with added columns
    flagging reciprocal pairs within date of collection (by_date_recip)
    and across all dates (recip).
    """
    if sensitivity:
        sensitivity_reciprocal_pairs(df)
    across_date_df = _get_reciprocal_pairs(df, across=True)
    by_date_df = _get_reciprocal_pairs(df)
    merge_map={'left_only': 0, 'both': 1}
    return df.merge(
        across_date_df, how='left', indicator='recip'
        ).merge(by_date_df, how='left', indicator='by_date_recip'
        ).assign(recip=lambda x: x['recip'].map(merge_map),
                 by_date_recip=lambda x: x['by_date_recip'].map(merge_map))


def get_net_migration(df, value_col='flow', add_cols=['query_date']):
    orig_cols = ['iso3_orig'] + add_cols
    dest_cols = ['iso3_dest'] + add_cols
    return df.assign(
        # immigrants - emigrants
        net_flow=lambda x:
        x.groupby(dest_cols)[value_col].transform(sum) -
        x.groupby(orig_cols)[value_col].transform(sum),
        # use 100 to compare w/ GWP
        net_rate_100=lambda x: (x['net_flow'] / x['users_orig']) * 100)


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
    df, by_cols=['country_orig', 'country_dest'],
    across_col='query_date', value_cols=['flow', 'net_rate_100']
):
    assert not df[by_cols + [across_col]].duplicated().values.any()
    def rsem(x):
        return sem(x) / np.mean(x)
    v_df = df.groupby(by_cols)[value_cols].agg(
        ['std', 'mean', 'median', 'count', cv, sem, rsem]
    ).reset_index()
    v_df.columns = ['_'.join(x) if '' not in x else ''.join(x)
                    for x in v_df.columns]
    add_cols = ['eu_uk', 'subregion_orig', 'subregion_dest']
    return v_df.merge(df[by_cols + add_cols].drop_duplicates())


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
    # dropping feb 8th, march 10th increases the number of pairs
    low_pairs = (df['query_date'].isin(['2021-02-08', '2021-03-10']))
    return df[~(too_big | same | low_pairs)]


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
    return df.merge(prep_geo(), **kwargs).merge(prep_language(), **kwargs)


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
        (df['contig'].isnull()) & (df['neighbor'] == 'both'), 'contig'
    ] = 1
    df.loc[
        (df['contig'].isnull()) &
        (df['iso3_orig'].isin(borderless) | df['iso3_dest'].isin(borderless)),
    'contig'] = 0
    # TODO see if it's possible to fill in more missing values
    return df.drop('neighbor', axis=1)


def fix_query_date(df, cutoff=np.timedelta64(10, 'D')):
    """Adjust date of collection for timeout errors."""
    date_fmt = '%Y-%m-%d'
    dates = sorted(
        [datetime.strptime(x, date_fmt) for x in df['query_date'].unique()]
    )
    combine_dates = {
        dates[n+1].strftime(date_fmt): dates[n].strftime(date_fmt)
        for n in range(0, len(dates) - 1) if dates[n+1] - dates[n] < cutoff}
    return df.replace(combine_dates)


def data_validation(
        df, id_cols=['country_orig', 'country_dest', 'query_date'],
        value_col='flow'
    ):
    """Checks and fixes before saving."""
    # TODO check for null values and try to fill them in
    df = fill_missing_borders(df)
    df = fix_query_date(df)
    # TODO add function for checking numeric vs. categorical variables
    # make sure country areas are reasonable
    biggest_area = 17098250
    assert (df[['area_dest', 'area_orig']] <= biggest_area).values.all()
    test_no_duplicates()
    if no_duplicates(df, id_cols, value_col, verbose=True):
        df = df.drop_duplicates(subset=id_cols, ignore_index=True)
    assert df[value_col].dtype == int
    return df
    

def collapse(df, var, id_cols=None, value_col='flow'):
    if id_cols is None:
        id_cols = [x for x in df.columns if
                   (var in x) & ('bin' in x)] + ['query_date']
    return df.groupby(id_cols)[value_col].sum().reset_index()


def main(update_chord_diagram=True):
    df = (
        pd.read_csv(path.join(get_input_dir(), get_latest_data()))
          .pipe(standardize_col_names)
          .pipe(reshape_long_wide)
    )
    # see changes across data collection dates
    (df.pipe(get_pct_change)
       .pipe(save_output, 'pct_change'))

    df = (df.pipe(merge_region_subregion)
            .pipe(add_metadata)
            .pipe(bin_continuous_vars, ['hdi', 'gdp'])
            .pipe(data_validation)
            .pipe(drop_bad_rows)
            # this has to happen last!
            .pipe(flag_reciprocals, True))

    # save separate outputs
    save_output(df, 'model_input')
    for col in ['recip', 'by_date_recip']:
        (df[df[col] == 1].pipe(get_net_migration)
                         .pipe(save_output, f'model_input_{col}_pairs'))
        if col == 'recip':
            # variation only
            (df[df[col] == 1].pipe(get_net_migration)
                             .pipe(get_variation)
                             .pipe(save_output, f'variation'))

    if update_chord_diagram:
        for grp_var in ['hdi', 'gdp', 'midreg', 'subregion']:
            save_output(
                collapse(df[df['recip'] == 1], grp_var),
                f'{grp_var}_chord_diagram'
            )


if __name__ == "__main__":
    main()