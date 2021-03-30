import pandas as pd
from utils.io import get_input_dir, _get_working_dir
from prep_bilateral_flows import prep_eu_states


def get_total_users():
    """File with total LinkedIn users by country."""
    df = pd.read_csv(f'{get_input_dir()}/model_input.csv')
    keep_cols = [x for x in df.columns if '_dest' in x] + ['query_date']
    eu = prep_eu_states()
    eu_uk_iso3s = eu[eu['eu_uk'] == 1].index.values
    df = df[keep_cols].drop_duplicates()
    df['eu_uk'] = df['iso3_dest'].apply(lambda x: 1 if x in eu_uk_iso3s else 0)
    return df

df = pd.read_csv(
    f'{get_input_dir()}/LinkedInRecruiterBaseratesSimple_withTime_2021-03-30.csv')
df['query_date'] = df['query_time'].str[:-9]
assert (df['query_info'] == 'r4').values.all()
df = df.drop(['query_info', 'Unnamed: 0', 'query_time'], axis=1)
df = df.drop_duplicates()
df = df.rename(columns={'query_country': 'country_dest'})

# merge on the 'total' from bilateral flows, think this will be useful?
df = pd.merge(get_total_users(), df, on='query_date', by='country_dest')


