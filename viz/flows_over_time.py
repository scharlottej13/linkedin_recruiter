import argparse
from collections import defaultdict
from os import mkdir, path
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from configurator import Config

CONFIG = Config()


def check_cutoffs(df, y):
    # check to make sure that countries
    # don't appear twice across different plots
    for idx in range(1, df.cutoff.max()):
        overlap = \
            set(df.query(f'cutoff == {idx - 1}')[f'country_{y}']) \
            & set(df.query(f'cutoff == {idx}')[f'country_{y}'])
        if len(overlap) != 0:
            # this could be better & pick an index based on where more
            # points are already
            df.loc[df[f'country_{y}'].isin(overlap), 'cutoff'] = idx - 1
    return df


def lineplt_broken_y_axis(df, y):
    """Same lineplot, but with broken axis.
    https://matplotlib.org/3.1.0/gallery/subplots_axes_and_figures/broken_axis.html
    """
    f, (ax, ax2) = plt.subplots(2, 1, sharex=True, figsize=(10, 5))
    # plot the same data on both axes
    lineplot_kwargs = {
        'x': 'query_date', 'y': 'prop', 'hue': f'country_{y}',
        'style': f'country_{y}', 'marker': 'o', 'data': df, 'ax': ax}
    sns.lineplot(**lineplot_kwargs)
    lineplot_kwargs.update({'ax': ax2})
    sns.lineplot(**lineplot_kwargs)

    # zoom-in / limit the view to different portions of the data
    ax.set_ylim(0.0016, 0.0019)  # outliers only
    ax2.set_ylim(0, .0009)  # most of the data

    # hide the spines between ax and ax2
    ax.spines['bottom'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax.xaxis.tick_top()
    ax.tick_params(labeltop=False)  # don't put tick labels at the top
    ax2.xaxis.tick_bottom()

    # This looks pretty good, and was fairly painless, but you can get that
    # cut-out diagonal lines look with just a bit more work. The important
    # thing to know here is that in axes coordinates, which are always
    # between 0-1, spine endpoints are at these locations (0,0), (0,1),
    # (1,0), and (1,1).  Thus, we just need to put the diagonals in the
    # appropriate corners of each of our axes, and so long as we use the
    # right transform and disable clipping.

    d = .015  # how big to make the diagonal lines in axes coordinates
    # arguments to pass to plot, just so we don't keep repeating them
    kwargs = dict(transform=ax.transAxes, color='k', clip_on=False)
    ax.plot((-d, +d), (-d, +d), **kwargs)        # top-left diagonal
    ax.plot((1 - d, 1 + d), (-d, +d), **kwargs)  # top-right diagonal

    kwargs.update(transform=ax2.transAxes)  # switch to the bottom axes
    ax2.plot((-d, +d), (1 - d, 1 + d), **kwargs)  # bottom-left diagonal
    ax2.plot((1 - d, 1 + d), (1 - d, 1 + d), **kwargs)  # bottom-right diagonal

    # What's cool about this is that now if we vary the distance between
    # ax and ax2 via f.subplots_adjust(hspace=...) or plt.subplot_tool(),
    # the diagonal lines will move accordingly, and stay right at the tips
    # of the spines they are 'breaking'

    plt.show()


def line_plt(df, iso, avg_prop, avg_n, x, y, split=None, log_scale=False):
    """Create time series line plot.

    df: dataframe of bilateral flows
    iso: iso3 country code
    avg_prop: total linkedin users / country population,
        averaged across data collection dates
    avg_n: total linkedin users averaged across data collection dates
    x, y: either 'orig' or 'dest', designed to easily run for either direction
        ie. show for a single origin all destination countries or
        for a single destination show all origin countries
    split: if a value is passed, then the plot is formatted a bit differently
        to account for the fact that not all corresponding countries are shown
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
    ax.set_xticklabels(df['query_date'].unique(),
                       rotation=45, horizontalalignment='right')
    ax.set_xlabel('Date of Data Collection')
    ax.set_ylabel('Percent of all users')
    if not split:
        suffix = 'time_series_all'
        ncol = 2
        ax.set_yticklabels([f'{x:.2%}' for x in ax.get_yticks().tolist()])
    else:
        suffix = f'time_series_split_{split}'
        ncol = 1
        ax.set_yticklabels([f'{x:.3%}' for x in ax.get_yticks().tolist()])
    if log_scale:
        suffix = 'time_series_log_scale'
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
        title=legend, frameon=False, ncol=ncol)
    # main title
    ax.text(
        x=0.5, y=1.1, s=title, transform=ax.transAxes,
        fontsize=12, weight='bold', ha='center', va='bottom'
    )
    # subtitle
    ax.text(
        x=0.5, y=1.03,
        s=f'on average {avg_prop:.1%} of people in {country} use LinkedIn (n={avg_n:,.0f})',
        fontsize=10, alpha=0.75, ha='center', va='bottom',
        transform=ax.transAxes
    )
    fig.tight_layout()
    # plt.show()
    outdir = f"{CONFIG['directories.data']['viz']}/{iso}"
    if not path.exists(outdir):
        mkdir(outdir)
    plt.savefig(
        f"{outdir}/{iso}_{x}_{suffix}.png", dpi=300, bbox_inches="tight")
    plt.close()


def prep_data(iso, x, y):
    df = pd.read_csv(
        f"{CONFIG['directories.data']['processed']}/model_input.csv")
    # restrict to countries that show up at least a few times
    keep_isos = list(
        df.query(f"iso3_{x} == '{iso}'").groupby(
            f'iso3_{y}'
        )['flow'].count().iloc[lambda x: x.values > 3].index)
    bins_dict = defaultdict(lambda: 5)
    return df.query(f"iso3_{x} == '{iso}' & iso3_{y} in {keep_isos}").assign(
        # proportion of relocaters out of all users
        prop=df['flow'] / df[f'users_{x}'],
        cutoff=lambda x: pd.qcut(
            x['prop'], bins_dict[iso], labels=False
        )
    ).sort_values(by=['query_date', 'prop'], ascending=[True, False])


def main(iso, dest):
    if not dest:
        x = 'orig'
        y = 'dest'
    else:
        x = 'dest'
        y = 'orig'
    # data that will be plotted
    df = prep_data(iso, x, y)
    # now pull in some other metrics
    variance_df = pd.read_csv(
        f"{CONFIG['directories.data']['processed']}/variance.csv"
    ).query(f"iso3_{x} == '{iso}'")
    # safe to take the first value b/c we only care about country_x
    # proportion of population using LinkedIn (averaged over time)
    prop = variance_df[f'prop_{x}_mean'].iloc[0]
    # number of LinkedIn users per country (averaged over time)
    n = variance_df[f'users_{x}_mean'].iloc[0]
    # plot top 10 countries
    top_10 = variance_df.sort_values(
        by='flow_mean', ascending=False).iloc[:11][f'iso3_{y}'].values
    # line_plt(
    #     df[df[f'iso3_{y}'].isin(top_10)], iso, prop, n,
    #     x, y, split='top10'
    # )
    lineplt_broken_y_axis(df[df[f'iso3_{y}'].isin(top_10)], y)
    # plot all countries, split across figures
    # df = check_cutoffs(df, y)
    # for idx in range(max(df['cutoff']), 0, -1):
    #     line_plt(df[df['cutoff'] == idx], iso, prop, n, x, y, split=idx + 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('iso3', help='country code', type=str.lower)
    parser.add_argument(
        '-dest', '--destination', help='iso3 will be destination instead',
        action='store_true'
    )
    args = parser.parse_args()
    main(args.iso3, args.destination)
