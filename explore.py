# -*- coding: utf-8 -*-
"""
Created on Fri Oct  9 10:39:43 2020

@author: johnson
"""

import pandas as pd
import os

data_path = os.path.abspath(
    "N:\Theile\LinkedIn\LinkedInRecruiter_dffromtobase_merged_gdp.csv")
outputs_dir = os.path.abspath("N:\johnson\linkedin_recruiter\outputs")
inputs_dir = os.path.abspath("N:\johnson\linkedin_recruiter\inputs")

df = pd.read_csv(data_path)
df = df.rename(
    columns={'countrycode_x': 'iso3_from', 'countrycode_y': 'iso3_to'})
loc_mapper = pd.read_csv(
    os.path.join(inputs_dir, 'UNSD-methodology.csv'), encoding='latin1'
)
loc_mapper['ISO-alpha3 Code'] = loc_mapper['ISO-alpha3 Code'].str.lower()
# add TWN, not recognized by UN as separate from China
loc_mapper = loc_mapper.append(
    pd.DataFrame(
        {'Region Name': ['Asia'], 'Sub-region Name': ['Eastern Asia'],
         'ISO-alpha3 Code': ['twn']}), ignore_index=True)
iso3_subregion = loc_mapper.set_index(
    'ISO-alpha3 Code')['Sub-region Name'].to_dict()
iso3_region = loc_mapper.set_index('ISO-alpha3 Code')['Region Name'].to_dict()

for flow in ['from', 'to']:
    df[f'region_{flow}'] = df[f'iso3_{flow}'].map(iso3_region)
    df[f'subregion_{flow}'] = df[f'iso3_{flow}'].map(iso3_subregion)
    for loc_lvl in ['region', 'subregion']:
        assert not df[f'{loc_lvl}_{flow}'].isnull().values.any(), \
               df.loc[df[f'{loc_lvl}_{flow}'].isnull(), f'iso3_{flow}'].unique()

# because R and I are currently not friends
df = df.rename(columns={
    'region_from': 'orig_reg', 'region_to': 'dest_reg', 'count': 'flow'})
df.groupby(['orig_reg', 'dest_reg'])['flow'].sum().to_csv("U:/linkedin_recruiter/region_flows_2020_10_09.csv")







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



