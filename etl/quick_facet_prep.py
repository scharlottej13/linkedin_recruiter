import pandas as pd
from etl.prep_bilateral_flows import fix_query_date

df = pd.read_csv(
    "/Users/scharlottej13/Nextcloud/linkedin_recruiter/raw-data/recruiter_all_categories/2021-06-03_all_facets.csv"
)
df = df.assign(query_date=df['time'].str[:-9])
df = fix_query_date(df).groupby(
    ['facet', 'country_to', 'value', 'query_date']
)['count'].sum().reset_index().groupby(
    ['facet', 'country_to', 'value']
)['count'].median().reset_index()
df['by_facet_prop'] = df['count'] / df.groupby(['facet', 'country_to'])['count'].transform(sum)

df.to_csv("/Users/scharlottej13/Nextcloud/linkedin_recruiter/processed-data/quick_facets.csv", index=False)

