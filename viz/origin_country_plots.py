from os import path, mkdir
from utils.io import get_input_dir, _get_working_dir
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import sys


def get_output_dir(custom_dir=None, sub_dir=None):
    #TODO this is bad, I copied it from another file oops
    if sub_dir:
        outdir = path.join(_get_working_dir(custom_dir), 'plots', sub_dir)
    else:
        outdir = path.join(_get_working_dir(custom_dir), 'plots')
    if not path.exists(outdir):
        mkdir(outdir)
    return outdir


def get_avg_prop(df):
    return df.drop_duplicates(
        ['query_date', 'country_orig']
    )['prop_orig'].mean()


def get_avg_n(df):
    return df.drop_duplicates(
        ['query_date', 'country_orig']
    )['users_orig'].mean()


def check_cutoffs(df):
    # check to make sure that countries
    # don't appear twice across different plots
    for idx in range(1, df.cutoff.max()):
        overlap = \
            set(df.query(f'cutoff == {idx - 1}')['country_dest']) \
            & set(df.query(f'cutoff == {idx}')['country_dest'])
        if len(overlap) != 0:
            # this could be better & pick an index based on where more
            # points are already
           df.loc[df['country_dest'].isin(overlap), 'cutoff'] = idx - 1
    return df


def line_plt(df, iso, avg_prop, avg_n, split=None):
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(
        'query_date',
        'prop',
        hue='country_dest',
        style='country_dest',
        marker='o',
        data=df,
        ax=ax
    )
    # make adjustments
    ax.set_xticklabels(df['query_date'].unique(),
                       rotation=45, horizontalalignment='right')
    ax.set_xlabel('Date of Data Collection')
    ax.set_ylabel('Percent Open to Relocation')
    if not split:
        suffix = 'time_series'
        ncol = 2
        ax.set_yticklabels([f'{x:.2%}' for x in ax.get_yticks().tolist()])
    elif split == 'log':
        suffix = 'time_series_log_scale'
        ncol = 2
        ax.set_ylabel('Proportion (log10)')
        ax.set_yticklabels([f'{x:.2}' for x in ax.get_yticks().tolist()])
    else:
        suffix = f'time_series_split_{split}'
        ncol = 1
        ax.set_yticklabels([f'{x:.3%}' for x in ax.get_yticks().tolist()])
    ax.legend(bbox_to_anchor=(1.05, 1), loc=2,
              title='Destination Country', frameon=False, ncol=ncol)
    country = df.country_orig.values[0]
    # main title
    ax.text(
        x=0.5, y=1.1, s=f'LinkedIn Users in {country} Open to Relocation',
        fontsize=12, weight='bold', ha='center', va='bottom',
        transform=ax.transAxes
    )
    # subtitle
    ax.text(
        x=0.5, y=1.03,
        s=f'on average {avg_prop:.1%} of people in {country} use LinkedIn (n={avg_n:,.0f})',
        fontsize=10, alpha=0.75, ha='center', va='bottom', transform=ax.transAxes
    )
    fig.tight_layout()
    # plt.show()
    plt.savefig(f'{get_output_dir(sub_dir=iso)}/{iso}_{suffix}.png', dpi=300)
    plt.close()


if __name__ == "__main__":
    iso = sys.argv[1]
    df = pd.read_csv(f"{get_input_dir()}/model_input.csv")
    keep_isos = list(
        df.query(f"iso3_orig == '{iso}'").groupby(
            'iso3_dest'
        )['flow'].count().iloc[lambda x: x.values == 14].index
    )
    iso_bins_dict = {
        'pol': [0, .0001, .000217, .0006, .001, 1],
        'ita': [0, .00002, .00004, .0014, 1],
        'deu': [0, .00003, .00004, .00008, .0015, 1]
    }
    df = df.query(f"iso3_orig == '{iso}' & iso3_dest in {keep_isos}").assign(
        prop=df['flow'] / df['users_orig'],
        cutoff=lambda x: pd.cut(
            x['prop'], iso_bins_dict[iso], labels=False, right=False)
    ).sort_values(by=['query_date', 'prop'], ascending=[True, False])
    prop = get_avg_prop(df)
    n = get_avg_n(df)
    line_plt(df, iso, prop, n)
    logdf = df.copy()
    logdf['prop'] = np.log10(logdf['prop'])
    line_plt(logdf, iso, prop, n, split='log')
    df = check_cutoffs(df)
    num_cols = len(df.cutoff.unique())
    for idx in range(0, num_cols):
        line_plt(df[df['cutoff'] == idx], iso, prop, n, split=idx + 1)

