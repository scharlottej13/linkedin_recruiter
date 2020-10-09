# -*- coding: utf-8 -*-
"""
Created on Fri Oct  9 10:39:43 2020

@author: johnson
"""


import pandas as pd
mapper = pd.read_excel("U:\linkedin_recruiter\country_region_lookup.xlsx", sheet_name="look up")
df = pd.read_csv("N:\LinkedInDataMigrationProject\Data\RecruiterData\linkedinRecruiterFromIndicatedTo.csv")
my_dict = mapper.set_index('country')['world region'].to_dict()
df['region_from'] = df['country_from'].map(my_dict)
df['region_to'] = df['country_to'].map(my_dict)
# manual fun time mappings
missing_locs = set(
    list(df.loc[df['region_from'].isnull(), 'country_from']) + list(df.loc[df['region_to'].isnull(), 'country_to'])
)
location_country_dict = {
    'Brabantine City Row': 'Netherlands',
    'Charlotte Metro': 'United States'
    'Gold Coast': 'Australia'
    'Metro Cebu': 'Philippines',
    'Metro Manila': 'Philippines',
    }
location_region_dict = {
    'Anguilla': 'Central America (incl. Mexico and Carribean)',
    'Antigua and Barbuda': 'Central America (incl. Mexico and Carribean)',
    'Bermuda': 'Central America (incl. Mexico and Carribean)',
    'Brabantine City Row': 'Western Europe',
    'British Virgin Islands': 'Central America (incl. Mexico and Carribean)',
    'Cayman Islands': 'Central America (incl. Mexico and Carribean)',
    'Charlotte Metro': 'North America',
    'Congo (DRC)': 'Sub-Saharan Africa',
    "Côte d'Ivoire": 'Sub-Saharan Africa',
    'Dominica': 'Central America (incl. Mexico and Carribean)',
    'FYRO Macedonia': 'Eastern Europe',
    'French-Guadeloupe': 'Central America (incl. Mexico and Carribean)',
    'French-Martinique': 'Central America (incl. Mexico and Carribean)',
    'Gaza Strip': 'Western Asia',
    'Gold Coast': 'Oceania',
    'Hong Kong SAR': 'Central Asia (incl. Russia)',
    'Kosovo': 'Eastern Europe',
    'Metro Cebu': 'South-East Asia',
    'Metro Manila': 'South-East Asia',
    'Palestinian Authority': 'Western Asia',
    'Republic of the Congo': 'Sub-Saharan Africa',
    'Seychelles': 'Central America (incl. Mexico and Carribean)',
    'St Kitts and Nevis': 'Central America (incl. Mexico and Carribean)',
    'St Lucia': 'Central America (incl. Mexico and Carribean)',
    'St Vincent and the Grenadines': 'Central America (incl. Mexico and Carribean)',
    'Taiwan': 'Central Asia (incl. Russia)',
    'The Bahamas': 'Central America (incl. Mexico and Carribean)',
    'The Gambia': 'Sub-Saharan Africa',
    'Turks and Caicos Islands': 'Central America (incl. Mexico and Carribean)',
    'West Bank': 'Western Asia',
    'West Midlands': 'Northern Europe'
}

for flow in ['from', 'to']:
    df[f'region_{flow}'] = df[f'country_{flow}'].map(my_dict)
    df.loc[
        df[f'region_{flow}'].isnull(), f'region_{flow}'
    ] = df[f'country_{flow}'].map(manual_dict)
    assert not df[f'region_{flow}'].isnull().values.any()

# because R and I are currently not friends
df = df.rename(columns={
    'region_from': 'orig_reg', 'region_to': 'dest_reg', 'count': 'flow'})
df.groupby(['orig_reg', 'dest_reg'])['flow'].sum().to_csv("U:/linkedin_recruiter/region_flows_2020_10_09.csv")











