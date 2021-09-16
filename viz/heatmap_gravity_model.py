import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from itertools import permutations
from configurator import Config
from datetime import datetime
import argparse
from pycountry import countries
from utils.misc import get_location_hierarchy
from etl.prep_bilateral_flows import cyp_hack

CONFIG = Config()


def percent_error(resid, fitted):
    return (resid / fitted) * 100


def get_best_model():
    model_dir = f"{CONFIG['directories.data']['model']}"
    best = pd.read_csv(f"{model_dir}/model_versions.csv").query("best == 1")
    assert len(best) == 1
    best_row = best.iloc[0]
    return pd.read_csv(
        f"{model_dir}/{best_row['description']}-{best_row['version_id']}.csv")


def aggregate_locations(df, loc_level='subregion'):
    """Aggregate model results to a given location level.
    
    The model is run in log space, so residuals should be
    calculated in log space, however, it doesn't make sense to sum log-
    transformed values. Therefore, sum to the region then
    log-transform and recalculate residuals.
    """
    # read in mapping from iso3 to region, subregion, midregion
    loc_df = get_location_hierarchy()[[loc_level]]
    df = df.merge(
        loc_df, how='left', left_on='iso3_orig', right_index=True
    ).merge(
        loc_df, how='left', left_on='iso3_dest', right_index=True,
        suffixes=('_orig', '_dest')
    ).pipe(cyp_hack).assign(
        antilog_preds=np.power(10, df['.fitted'])
    ).groupby(
        [f'{loc_level}_orig', f'{loc_level}_dest'], as_index=False
    )[['antilog_preds', 'flow_median', 'users_dest_median']].sum().rename(
        columns={'antilog_preds': '.fitted',
                 'subregion_orig': 'region_orig',
                 'subregion_dest': 'region_dest'})
    df['.resid'] = df['flow_median'] - df['.fitted']
    return df


def prep_heatmap_data(df, value, loc_level='country'):
    if loc_level == 'country':
        for x in ['orig', 'dest']:
            df[f'{loc_level}_{x}'] = df[f'iso3_{x}'].apply(
                lambda x: countries.get(alpha_3=x.upper()).name
            )
    col_label_dict = {
        f'{loc_level}_orig': f'Current {loc_level.capitalize()}',
        f'{loc_level}_dest': f'Prospective Destination {loc_level.capitalize()}'
    }
    id_cols = list(col_label_dict.keys())
    labels = list(col_label_dict.values())
    if loc_level == 'country':
        pvt = pd.DataFrame(
            permutations(df[f'{loc_level}_dest'].unique(), 2), columns=id_cols
        ).merge(df[id_cols + [value]], how='left').fillna(0).rename(
            columns=col_label_dict).pivot_table(
                value, labels[0], labels[1]
            )
    else:
        pvt = df[id_cols + [value]].rename(columns=col_label_dict).pivot_table(
            value, labels[0], labels[1])
    order = df.sort_values(by='users_dest_median', ascending=False)[
        f'{loc_level}_dest'].drop_duplicates().values
    return pvt.reindex(order, axis=0).reindex(order, axis=1)


def heatmap(df, value, aggregate):
    assert 'quant' in value, "This will only work for categorical plots"
    ticks = list(set(df[value]))
    heatmap_kws = {
        'square': True, 'linewidths': .5, 'cbar_kws': {"shrink": .5},
        'cmap': sns.color_palette("coolwarm", len(ticks)),
    }
    if aggregate:
        pairs = prep_heatmap_data(df, value, loc_level='region')
        fig_size = (9, 6)
    else:
        pairs = prep_heatmap_data(df, value)
        fig_size = (12, 10)
    # create figure
    fig, ax = plt.subplots(figsize=fig_size)
    ax = sns.heatmap(pairs, mask=(pairs == 0), **heatmap_kws)
    # hack for making the colorbar show categories
    colorbar = ax.collections[0].colorbar
    colorbar.set_ticks(ticks)
    tick_labels = [
        'much lower than expected', 'lower than expected',
        'about as expected', 'higher than expected',
        'much higher than expected'
    ]
    assert len(tick_labels) == len(ticks), \
        "now you messed up, number of tick labels != number of ticks"
    colorbar.set_ticklabels(tick_labels)
    # Let the horizontal axis labeling appear on top
    ax.xaxis.set_label_position('top')
    ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)
    title_suffix = 'Percentage Error' if 'pct_error' in value else 'Residuals'
    ax.set_title(f'Quintiles of {title_suffix}', fontsize=15)
    # Rotate the tick labels and set alignment
    plt.setp(ax.get_xticklabels(), rotation=-30, ha="right",
             rotation_mode="anchor")
    fig.tight_layout()
    out_dir = CONFIG['directories.data']['viz']
    agg_str = '_aggregate' if aggregate else ''
    plt.savefig(
        f'{out_dir}/eu_heatmap_{value}{agg_str}.pdf')
    plt.savefig(
        f'{out_dir}/_archive/\
        eu_heatmap_{value}{agg_str}_{datetime.now().date()}.pdf')
    plt.close()


def main(value, aggregate):
    df = get_best_model()
    if aggregate:
        df = aggregate_locations(df)
    df['pct_error'] = percent_error(df['.resid'], df['.fitted'])
    df[[f'{x}_quant' for x in ['resids', 'pct_error']]] = \
        df[['.resid', 'pct_error']].apply(
            lambda x: pd.qcut(x, 5, labels=list(range(1, 6))).astype(int))
    heatmap(df, f'{value}_quant', aggregate)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('value', choices=['pct_error', 'resids'])
    parser.add_argument(
        '-aggregate', help='whether to aggregate to higher location level',
        action='store_true'
    )
    args = parser.parse_args()
    main(args.value, args.aggregate)
