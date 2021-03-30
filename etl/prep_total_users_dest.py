import pandas as pd
from utils.io import get_input_dir, _get_working_dir
from etl.prep_bilateral_flows import prep_eu_states


def get_total_users():
    """File with total LinkedIn users by country."""
    df = pd.read_csv(f'{get_input_dir()}/model_input.csv')
    keep_cols = [x for x in df.columns if '_dest' in x] + ['query_date']
    eu = prep_eu_states()
    eu_uk_iso3s = eu[eu['eu_uk'] == 1].index.values
    df = df[keep_cols].drop_duplicates()
    df['eu_uk'] = df['iso3_dest'].apply(lambda x: 1 if x in eu_uk_iso3s else 0)
    df['query_datetime'] = pd.to_datetime(df['query_date'])
    return df.sort_values(by='query_datetime')

df = pd.read_csv(
    f'{get_input_dir()}/LinkedInRecruiterBaseratesSimple_withTime_2021-03-30.csv')
df['query_date'] = df['query_time'].str[:-9]
assert (df['query_info'] == 'r4').values.all()
df = df.drop(['query_info', 'Unnamed: 0', 'query_time'], axis=1)
df = df.drop_duplicates()
df = df.rename(columns={'query_country': 'country_dest'})
df['query_datetime'] = pd.to_datetime(df['query_date'])
df = df.sort_values(by='query_datetime')

# merge on the 'total' from bilateral flows
key_cols = ['country_dest', 'query_datetime', 'query_date']
keys = pd.merge_asof(get_total_users()[key_cols], df[key_cols],
                     on='query_datetime', by='country_dest')

# to do !
# that merge didn't really work
# need to look at examples like this:
"""
country_dest query_datetime query_date_x query_date_y
137         Iraq     2020-07-25   2020-07-25   2020-07-24
498         Iraq     2020-10-20   2020-10-20   2020-07-24
"""

