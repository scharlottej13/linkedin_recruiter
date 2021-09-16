import argparse
from collections import defaultdict
from os import mkdir, path
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from configurator import Config
from utils.misc import custom_round

CONFIG = Config()


def line_plt(df, iso, avg_prop, avg_n, x, y, suffix=None, log_scale=False):
    """Create time series line plot.

    df: dataframe of bilateral flows
    iso: iso3 country code
    avg_prop: total linkedin users / country population,
        averaged across data collection dates
    avg_n: total linkedin users averaged across data collection dates
    x, y: either 'orig' or 'dest', designed to easily run for either direction
        ie. show for a single origin all destination countries or
        for a single destination show all origin countries
    log_scale: whether to log transform the y-axis (open to relocate / users)
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(
        'query_date',
        'prop',
        hue=f'country_{y}',
        style=f'country_{y}',
        marker='o',
        data=df,
        ax=ax
    )
    # make adjustments
    # did this so that a bunch of plots would all be on the same y-axis
    ax.set_ylim((0 , .00250))
    ax.set_xticklabels(
        df['query_date'].unique(), rotation=45, ha='right')
    ax.set_yticklabels([f'{x*100000:.0f}' for x in ax.get_yticks().tolist()])
    ax.set_xlabel('Date of Data Collection')
    ax.set_ylabel('Users per 100,000')
    if log_scale:
        suffix = 'log_scale'
        ax.set_ylabel('Proportion (log10)')
    # ok now format some text
    country = df[f'country_{x}'].values[0]
    if x == 'orig':
        legend = 'Destination Country'
        title = f'LinkedIn Users in {country} Open to Relocation'
    else:
        legend = 'Origin Country'
        title = f'LinkedIn Users Open to Relocating to {country}'
    ax.legend(
        bbox_to_anchor=(1.05, 1), loc=2,
        title=legend, frameon=False, ncol=1)
    # main title
    ax.text(
        x=0.5, y=1.1, s=title, transform=ax.transAxes,
        fontsize=12, weight='bold', ha='center', va='bottom'
    )
    # subtitle
    ax.text(
        x=0.5, y=1.03,
        s=f'on average {avg_prop:.1%} of people in {country} use LinkedIn (n={avg_n})',
        fontsize=10, alpha=0.75, ha='center', va='bottom',
        transform=ax.transAxes
    )
    fig.tight_layout()
    # plt.show()
    outdir = f"{CONFIG['directories.data']['viz']}/{iso}"
    if not path.exists(outdir):
        mkdir(outdir)
    plt.savefig(
        f"{outdir}/{iso}_{x}_time_series_{suffix}.png", dpi=300, bbox_inches="tight")
    plt.close()


def prep_data(iso, x, y):
    df = pd.read_csv(
        f"{CONFIG['directories.data']['processed']}/model_input.csv")
    # restrict to countries that show up at least a few times
    keep_isos = list(
        df.query(f"iso3_{x} == '{iso}'").groupby(
            f'iso3_{y}'
        )['flow'].count().iloc[lambda x: x.values > 5].index)
    bins_dict = defaultdict(lambda: 5)
    return df.query(f"iso3_{x} == '{iso}' & iso3_{y} in {keep_isos}").assign(
        # proportion of relocaters out of all users
        prop=df['flow'] / df[f'users_{x}'],
        cutoff=lambda x: pd.qcut(
            x['prop'], bins_dict[iso], labels=False
        )
    ).sort_values(by=['query_date', 'prop'], ascending=[True, False])


def get_top_countries(x, iso3_y, df, variance_df):
    top = variance_df.sort_values(
        by='flow_mean', ascending=False).iloc[:x][f'iso3_{iso3_y}'].values
    top_df = df[df[f'iso3_{iso3_y}'].isin(top)]
    # bit of a hack
    # because of an earlier restriction (that we like) sometimes < 10
    num_isos = x
    while len(top_df[f'iso3_{iso3_y}'].unique()) < x:
        num_isos += 1
        top = variance_df.sort_values(
            by='flow_mean', ascending=False
        ).iloc[:num_isos][f'iso3_{iso3_y}'].values
        top_df = df[df[f'iso3_{iso3_y}'].isin(top)]
    return top_df


def main(iso, dest):
    if not dest:
        iso3_x = 'orig'
        iso3_y = 'dest'
    else:
        iso3_x = 'dest'
        iso3_y = 'orig'
    # data that will be plotted
    df = prep_data(iso, iso3_x, iso3_y)
    # now pull in some other metrics
    variance_df = pd.read_csv(
        f"{CONFIG['directories.data']['processed']}/variance.csv"
    ).query(f"iso3_{iso3_x} == '{iso}'")
    # safe to take the first value b/c we only care about country_x
    # proportion of population using LinkedIn (averaged over time)
    prop = variance_df[f'prop_{iso3_x}_mean'].iloc[0]
    # number of LinkedIn users per country (averaged over time)
    n = custom_round(variance_df[f'users_{iso3_x}_mean'].iloc[0])
    # plot top countries
    # line_plt(get_top_countries(10, iso3_y, df, variance_df),
    #          iso, prop, n, iso3_x, iso3_y, suffix='top10')
    line_plt(get_top_countries(5, iso3_y, df, variance_df),
             iso, prop, n, iso3_x, iso3_y, suffix='top5')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('iso3', help='country code', type=str.lower)
    parser.add_argument(
        '-dest', '--destination', help='iso3 will be destination instead',
        action='store_true'
    )
    args = parser.parse_args()
    main(args.iso3, args.destination)
