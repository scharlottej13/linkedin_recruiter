import pandas as pd
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


def get_best_model():
    model_dir = f"{CONFIG['directories.data']['model']}"
    best = pd.read_csv(f"{model_dir}/model_versions.csv").query("best == 1")
    assert len(best) == 1
    best_row = best.iloc[0]
    return pd.read_csv(
        f"{model_dir}/{best_row['description']}-{best_row['version_id']}.csv")


def prep_heatmap_data(df, value, sort, aggregate=False):
    # first grab country names from iso3s
    for x in ['orig', 'dest']:
        df[f'country_{x}'] = df[f'iso3_{x}'].apply(
            lambda x: countries.get(alpha_3=x.upper()).name
        )
    if aggregate:
        # need the regions we're aggregating to
        loc_df = get_location_hierarchy()
        df = df.merge(
            loc_df, how='left', left_on='iso3_orig', right_index=True).merge(
            loc_df, how='left', left_on='iso3_dest', right_index=True,
            suffixes=('_orig', '_dest')).pipe(cyp_hack).groupby(
                ['subregion_dest', 'subregion_orig'])
    col_label_dict = {'country_orig': 'Current Country',
                      'country_dest': 'Prospective Destination Country'}
    id_cols = list(col_label_dict.keys())
    pvt = pd.DataFrame(
        permutations(df['country_dest'].unique(), 2), columns=id_cols
    ).merge(df[id_cols + [value]], how='left').fillna(0).rename(
        columns=col_label_dict).pivot_table(
            value, 'Current Country', 'Prospective Destination Country'
        )
    if sort:
        order = df.sort_values(by='users_dest_median', ascending=False)[
            'country_dest'].drop_duplicates().values
        return pvt.reindex(order, axis=0).reindex(order, axis=1)
    else:
        return pvt


def heatmap(df, value, sort=False):
    assert 'quant' in value, "This will only work for categorical plots"
    ticks = list(set(df[value]))
    heatmap_kws = {
        'square': True, 'linewidths': .5, 'cbar_kws': {"shrink": .5},
        'cmap': sns.color_palette("coolwarm", len(ticks)),
    }
    recip_pairs = prep_heatmap_data(df, value, sort)
    # create figure
    plt.figure(figsize=(12, 10))
    # make plot
    ax = sns.heatmap(recip_pairs, mask=(recip_pairs == 0), **heatmap_kws)
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
    plt.tight_layout()
    sort_str = '_sorted' if sort else ''
    out_dir = CONFIG['directories.data']['viz']
    plt.savefig(
        f'{out_dir}/eu_heatmap_{value}{sort_str}.pdf')
    plt.savefig(
        f'{out_dir}/_archive/\
        eu_heatmap_{value}{sort_str}_{datetime.now().date()}.pdf')
    plt.close()


def main(value, sort):
    df = get_best_model()
    df['pct_error'] = (df['.resid'] / df['.fitted']) * 100
    df[[f'{x}_quant' for x in ['resids', 'pct_error']]] = \
        df[['.resid', 'pct_error']].apply(
            lambda x: pd.qcut(x, 5, labels=list(range(1, 6))).astype(int))
    heatmap(df, f'{value}_quant', sort)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('value', choices=['pct_error', 'resids'])
    parser.add_argument(
        '-sort', help='whether to sort columns, rows by number of users',
        action='store_true'
    )
    args = parser.parse_args()
    main(args.value, args.sort)
