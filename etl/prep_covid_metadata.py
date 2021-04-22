"""
Academic citation:
Thomas Hale, Noam Angrist, Rafael Goldszmidt, Beatriz Kira, Anna Petherick,
Toby Phillips, Samuel Webster, Emily Cameron-Blake, Laura Hallas, Saptarshi Majumdar,
and Helen Tatlow. (2021). “A global panel database of pandemic policies
(Oxford COVID-19 Government Response Tracker).” Nature Human Behaviour.
https://doi.org/10.1038/s41562-021-01079-8
"""

import pandas as pd
url = "https://github.com/OxCGRT/covid-policy-tracker/blob/master/data/OxCGRT_latest.csv?raw=true"
df = pd.read_csv(url)
