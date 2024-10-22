import numpy as np
import pandas as pd
import xlsxwriter
from os import pipe
from utils.io import save_output
from etl.prep_bilateral_flows import prep_eu_states
from configurator import Config

CONFIG = Config()


def prep_total_users():
    """File with total LinkedIn users by country."""
    df = pd.read_csv(
        f"{CONFIG['directories.data']['processed']}/model_input.csv")
    keep_cols = [x for x in df.columns if '_dest' in x] + ['query_date']
    eu = prep_eu_states()
    eu_isos = eu[eu['eu_plus'] == 1].index.values
    df['eu_plus'] = df['iso3_dest'].apply(lambda x: 1 if x in eu_isos else 0)
    return df[keep_cols + ['eu_plus']].drop_duplicates().assign(
        query_datetime=pd.to_datetime(df['query_date'])
    ).sort_values(by='query_datetime')


def fix_dups(df, id_cols=['query_date', 'country_dest'], value_col='goers'):
    """Fix duplicates from same day, different time."""
    groups = df[df.duplicated(id_cols, keep=False)].groupby(id_cols)[value_col]
    for key, group in groups:
        values_arr = group.values
        assert np.allclose(values_arr[:, None], values_arr, rtol=0.01),\
            f"duplicates for {key} had very different values: {group}"
    return df.drop_duplicates(id_cols)


def drop_bad_rows(df):
    # there are some -1 values, drop these
    return df[(df['goers'] > 0) &
        ~((
            (df['query_date'] == '2020-10-08') &
            (df['country_dest'] == 'Central African Republic')
        ) | (df['country_dest'] == 'Cyprus UN Neutral Zone'))
    ]


def prep_goers():
    """Prep those who want to go ("potential immmigrants") to a country."""
    df = pd.read_csv(
        f"{CONFIG['directories.data']['raw']}/LinkedInRecruiterBaseratesSimple_withTime_2021 - 03 - 30.csv"
    ).assign(query_date=lambda x: x['query_time'].str[:-9]).rename(
        columns={'query_country': 'country_dest', 'total': 'goers'})
    assert (df['query_info'] == 'r4').values.all()
    return df.drop(['query_info', 'Unnamed: 0', 'query_time'], axis=1
    ).drop_duplicates().pipe(drop_bad_rows).pipe(fix_dups).assign(
        query_datetime=pd.to_datetime(df['query_date'])
    ).sort_values(by='query_datetime')


def merge_goers_total(goers_df, users_df):
    """Merge two dataframes to compare values & also grab metadata.
    
    goers_df: DataFrame of people who are open to relocating to a different
    country ("potential immigrants"), by country and date of data collection
    users_df: DataFrame of total number of linkedin users for a given country,
    by date of data collection, and a number of metadata columns.
    """
    keep_cols = ['country_dest', 'query_datetime', 'query_date']
    # doing this in two steps b/c 'merge_asof' only works as a left join
    keys = pd.merge_asof(
        users_df[keep_cols], goers_df[keep_cols], on='query_datetime',
        by='country_dest', direction='nearest'
        )[['query_date_y', 'query_date_x']].drop_duplicates().set_index(
            'query_date_y')['query_date_x'].to_dict()
    # and now for the real merge
    goers_df['date_key'] = goers_df['query_date'].map(keys)
    users_df['date_key'] = users_df['query_date'].copy()
    return goers_df.merge(
        users_df, left_on=['date_key', 'country_dest'],
        right_on=['date_key', 'country_dest'], how='left'
    ).drop(['query_date_x', 'query_date_y', 'query_datetime_x',
            'query_datetime_y'], axis=1).assign(
                ratio=lambda x: x['goers'] / x['users_dest'])


def get_rank_over_time(df, value, metric_name):
    """return rank of destination countries."""
    return (
        df.assign(
            rank=df.groupby('date_key')[f'{value}'].rank(
                ascending=False, method='first', na_option='bottom'))
          .pivot(index='rank', columns='date_key',
                 values=['country_dest', f'{value}'])
          .sort_index(axis=1, level=[1, 0])
          .rename(columns={f'{value}': f'{metric_name}'})
        )


def main():
    goers_df = prep_goers()
    users_df = prep_total_users()
    df = merge_goers_total(goers_df, users_df)
    save_output(df, 'goers')
    writer = pd.ExcelWriter(
        f"{CONFIG['directories.data']['processed']}/destination_ranks.xlsx",
        engine='xlsxwriter'
    )
    get_rank_over_time(df, 'goers', 'number').to_excel(
        writer, sheet_name='num')
    get_rank_over_time(df, 'ratio', 'proportion').to_excel(
        writer, sheet_name='prop')
    get_rank_over_time(df.query("eu_plus == 1"), 'goers', 'number').to_excel(
        writer, sheet_name='eu_num')
    get_rank_over_time(
        df.query("eu_plus == 1"), 'ratio', 'proportion').to_excel(
        writer, sheet_name='eu_prop')
    writer.save()


if __name__ == "__main__":
    main()
