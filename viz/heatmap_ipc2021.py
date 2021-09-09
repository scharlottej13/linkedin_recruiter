import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from itertools import permutations
from configurator import Config
from datetime import datetime
import argparse

CONFIG = Config()


def prep_heatmap_data(df, value, sort):
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
        f'{out_dir}/plots/_archive/\
        eu_heatmap_{value}{sort_str}_{datetime.now().date()}.pdf')
    plt.close()


def main(value, sort):
    model_name = "cohen_eu_dist_biggest_cities_plus"
    df = pd.read_csv(
        f"{CONFIG['directories.data']['model']}/{model_name}.csv")
    df['pct_error'] = ((df['flow_median'] - df['preds']) / df['preds']) * 100
    df[[f'{x}_quant' for x in ['resids', 'pct_error']]] = \
        df[['resids', 'pct_error']].apply(
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
