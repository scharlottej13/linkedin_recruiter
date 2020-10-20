# -*- coding: utf-8 -*-
"""
Created on Fri Oct  9 10:39:43 2020

@author: johnson
"""

import pandas as pd
import os
import datetime

data_path = os.path.abspath(
    "N:\Theile\LinkedIn\LinkedInRecruiter_dffromtobase_merged_gdp.csv")
output_dir = os.path.abspath("N:\johnson\linkedin_recruiter\outputs")
input_dir = os.path.abspath("N:\johnson\linkedin_recruiter\inputs")

df = pd.read_csv(data_path)
df = df.rename(
    columns={'countrycode_x': 'iso3_from', 'countrycode_y': 'iso3_to'})
loc_mapper = pd.read_csv(
    os.path.join(input_dir, 'UNSD-methodology.csv'), encoding='latin1'
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

# the paper from Abel & Cohen has a *slightly* different location aggregation
midreg_dict = pd.read_csv(
    os.path.join(input_dir, 'abel_regions.csv')
).set_index('Sub-region Name')['Mid-region Name'].to_dict()
df['midreg_from'] = df['subregion_from'].map(midreg_dict)
df['midreg_to'] = df['subregion_to'].map(midreg_dict)
df.to_excel(os.path.join(output_dir, "merged_with_region.xlsx"))

# because R and I are currently not friends
df = df.rename(columns={
    'region_from': 'orig_reg', 'region_to': 'dest_reg',
    'number_people_who_indicated': 'flow', 'subregion_from': 'orig_subreg',
    'subregion_to': 'dest_subreg'})
today = datetime.datetime.now().date()
df.query('query_time_round == "2020-07-25 02:00:00"').groupby(
    ['orig_reg', 'dest_reg'])['flow'].sum().to_csv(
        os.path.join(output_dir, f'july_region_flows_{today}.csv'))
df.query('query_time_round == "2020-07-25 02:00:00"').groupby(
    ['orig_subreg', 'dest_subreg'])['flow'].sum().to_csv(
        os.path.join(output_dir, f'july_subregion_flows_{today}.csv'))
df.query('query_time_round == "2020-07-25 02:00:00"').groupby(
    ['orig_midreg', 'dest_midreg'])['flow'].sum().to_csv(
        os.path.join(output_dir, f'july_midregion_flows_{today}.csv'))
























