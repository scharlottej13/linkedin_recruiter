import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from os import path, mkdir
from matplotlib.patches import Rectangle
# from matplotlib.colors import LinearSegmentedColormap
from utils.io import get_input_dir, _get_working_dir
from scipy import stats
import statsmodels.stats.api as sms
# from math import e


def get_output_dir(custom_dir=None, sub_dir=None):
    if sub_dir:
        outdir = path.join(_get_working_dir(custom_dir), 'plots', sub_dir)
    else:
        outdir = path.join(_get_working_dir(custom_dir), 'plots')
    if not path.exists(outdir):
        mkdir(outdir)
    return outdir


def log_tform(df, log_cols):
    df[[f'log_{x}' for x in log_cols]] = df[[x for x in log_cols]].apply(np.log)
    return df


def ttest(df, grp_var):
    # TODO not quite right, need to account for repeated measures (dates)
    a = df[df[f'{grp_var}'] == 1]['flow'].values
    b = df[df[f'{grp_var}'] == 0]['flow'].values
    print(f'T test for {grp_var}')
    print(stats.ttest_ind(a, b, equal_var=False))
    cm = sms.CompareMeans(sms.DescrStatsW(a), sms.DescrStatsW(b))
    print(cm.tconfint_diff(usevar='unequal'))


def facet_hist(df, plt_vars, output_dir):
    df = df[plt_vars + ['query_date', 'eu_plus']].replace(
        {-np.inf: np.nan, np.inf: np.nan}
    ).sort_values(by='query_date')
    for plt_var in plt_vars:
        ax = sns.displot(
            df, x=plt_var, col='query_date', hue='eu_plus', kde=True,
            height=2, col_wrap=3, facet_kws={'dropna': True}
        )
        plt.savefig(f"{output_dir}/hist_{plt_var}.png", dpi=300)
        plt.close()


def pairplot(df, plt_vars, plt_name, output_dir):
    # TODO part of this is getting cut off? and the legend looks funky
    plt.figure(figsize=(10, 10))
    g = sns.pairplot(
        df.sort_values(by='query_date'), vars=plt_vars + ['flow'],
        hue='query_date', palette='crest', diag_kws=dict(fill=False),
        corner=True, dropna=True
    )
    plt.savefig(f"{output_dir}/{plt_name}_scatter.png", dpi=300)
    plt.close()


def corr_matrix(df, loc_str, suffix, output_dir, type='pearson'):
    if type == 'pearson':
        prefix = 'p'
        title_str = "Pearson's correlation"
        cols = [x for x in df.columns if 'median' in x] + ['flow_variation'] + \
            sorted(
                [x for x in df.columns if 'dist' in x or 'area' in x or
                 (('hdi' in x or 'gdp' in x) and 'bin' not in x)
                 or 'internet' in x]) + ['csl', 'cnl', 'prox2']
    elif type == 'spearman':
        prefix = 'sp'
        title_str = "Spearman's rank"
        cols = [x for x in df.columns if 'median' in x] + ['prox1']
    else:
        ValueError, f"Type must be spearman or pearson, but was: {type}"
    corr = df[cols].corr(type)
    plt.figure(figsize=(10, 10))
    ax = sns.heatmap(
        corr, mask=np.triu(corr), annot=True, fmt='.1g',
        vmin=-1, vmax=1, center=0, square=True,
        cmap=sns.diverging_palette(20, 220, n=200)
    )
    ax.set_xticklabels(cols, rotation=45, horizontalalignment='right')
    ax.set_title(f"{loc_str} {title_str} coefficients")
    ax.add_patch(Rectangle(
        (0, 1), 1, len(cols), fill=False, edgecolor='blue', lw=3)
    )
    plt.tight_layout()
    plt.savefig(f"{output_dir}/{prefix}_corr_matrix_{suffix}.png", dpi=300)
    plt.close()


def data_availability(outdir):
    def make_it_nice(df, pair_type, loc_level):
        return df[['query_date', 'flow']].assign(
            **{'Pair Type': pair_type, 'Locations': loc_level}
        ).rename(columns={'query_date': 'Date'})
    df_list = []
    recip_str_dict = {
        '': 'all', '_recip_pairs': 'reciprocal pairs (across dates)',
        '_by_date_recip_pairs': 'reciprocal pairs(by date)'
    }
    for suffix, str_title in recip_str_dict.items():
        for loc_level in ['EU+UK', 'Global']:
            if loc_level == 'EU+UK':
                df = pd.read_csv(f"{get_input_dir()}/model_input{suffix}.csv"
                    ).query('eu_plus == 1')
                df_list.append(make_it_nice(df, str_title, loc_level))
            else:
                df = pd.read_csv(f"{get_input_dir()}/model_input{suffix}.csv")
                df_list.append(make_it_nice(df, str_title, loc_level))
    pd.concat(df_list).pivot_table(
        index='Date', columns=['Locations', 'Pair Type'],
        values='flow', aggfunc='count'
    ).to_csv(f'{outdir}/pairs_table.csv')


def variation_heatmap(df, outdir):
    df = df.assign(
        flow_variation_pct=lambda x: x['flow_variation'] * 100
    )
    num_dates = df['flow_count'].iloc[0]
    heatmap_kws = {
        'square': True, 'linewidths': .5, 'annot': True,
        'fmt': '.1g', 'cbar_kws': {"shrink": .5},
        'cmap': sns.color_palette("viridis", as_cmap=True)
    }
    for metric in ['flow_variation_pct', 'flow_median']:
        if metric == 'flow_variation_pct':
            metric_str = 'Coefficient of Variance (%)'
        if metric == 'flow_median':
            metric_str = 'Median'
            heatmap_kws.update({'annot': None})
        recip_pairs = df[
            ['country_orig', 'country_dest', metric]
        ].rename(
            columns={'country_orig': 'Origin Country',
                    'country_dest': 'Destination Country'}
        ).pivot_table(metric, 'Origin Country', 'Destination Country')
        # create figure
        plt.figure(figsize=(10, 10))
        # make plot
        ax = sns.heatmap(recip_pairs, **heatmap_kws)
        # Let the horizontal axis labeling appear on top
        ax.xaxis.set_label_position('top')
        ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)
        ax.set_title(
            f'{metric_str} across {num_dates} collection dates', fontsize=15)
        # add '%' to colorbar for CV %
        if metric == 'flow_variation_pct':
            cb = ax.collections[0].colorbar
            cb.ax.set_yticklabels([f'{i}%' for i in cb.get_ticks()])
        # Rotate the tick labels and set alignment
        plt.setp(ax.get_xticklabels(), rotation=-30, ha="right",
                 rotation_mode="anchor")
        plt.tight_layout()
        plt.savefig(f"{outdir}/heatmap_{metric}.png", dpi=300)
        plt.close()


def get_top_countries(df, value, country_col='country_dest', n=15):
    """Return list of top n countries by some value, sorted by date."""
    return df[[value, country_col]].drop_duplicates().sort_values(
        by=value, ascending=False).head(n)[country_col].values


def plt_over_time(outdir):
    """Prep data for line plot over time."""
    for value_col in ['users_dest', 'goers']:
        df = pd.read_csv(f"{get_input_dir()}/goers.csv").dropna(
            subset=['users_dest']).sort_values(
                by=['date_key', value_col], ascending=[True, False])
        n = 15
        for loc in ['eu', 'top']:
            if loc == 'eu':
                data = df[df['eu_plus'] == 1]
                loc_str = 'EU + UK'
            if loc == 'top':
                data = df[
                    df['country_dest'].isin(get_top_countries(df, value_col, n=n))
                ]
                loc_str = f'top {n} countries'
                if value_col == 'goers':
                    loc_str = f'top {n} destinations'
            title_str = f'Number of LinkedIn users, by country ({loc_str})'
            if value_col == 'goers':
                title_str = f'Number of LinkedIn users open to relocating, by destination country ({loc_str})'
            make_line_plt(data, value_col, title_str, loc, outdir)


def make_line_plt(data, value, title_str, suffix, outdir):
    """Code for actual plot."""
    plt.figure(figsize=(10, 10))
    ax = sns.lineplot(
        data=data, x=data['date_key'], y=data[value],
        hue=data['country_dest'], style=data['country_dest']
    )
    ax.set_xticklabels(
        data['date_key'].unique(), rotation=45, ha='right')
    ax.set_yticklabels(
        ['{:,.0f}'.format(x) for x in ax.get_yticks().tolist()])
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    plt.xlabel('Date of Data Collection')
    plt.ylabel('Country')
    plt.title(title_str)
    plt.tight_layout()
    plt.savefig(f"{outdir}/lineplt_users_{suffix}.png", dpi=300)
    plt.close()


def main(save_hists=True, save_heatmaps=True, save_pairplots=False):
    # save this first, shows what data went into each plot
    data_availability(get_output_dir())
    # TODO feeling a plotting class kind of thing
    categ_cols = ['contig', 'comlang_ethno', 'colony', 'comcol',
                  'curcol', 'col45', 'col', 'smctry', 'prox1']
    cont_cols = [
        'flow', 'net_flow', 'net_rate_100', 'users_orig', 'users_dest',
        'pop_orig', 'gdp_orig', 'hdi_orig', 'pop_dest', 'gdp_dest', 'hdi_dest',
        'area_orig', 'area_dest', 'internet_orig', 'internet_dest',
        'dist_biggest_cities', 'dist_pop_weighted', 'dist_unweighted',
        'csl', 'cnl', 'prox2'
    ]
    log_cols = \
        [f'{x}_{y}' for y in ['dest', 'orig']
            for x in ['users', 'pop', 'gdp', 'area']] \
        + ['flow', 'prox2', 'cnl', 'csl'] + \
        [x for x in cont_cols if 'dist' in x]
    if save_heatmaps:
        df = pd.read_csv(f'{get_input_dir()}/variance.csv')
        outdir = get_output_dir(sub_dir='recip')
        for loc in ['EU+UK', 'Global']:
            if loc == 'EU+UK':
                data = df[df['eu_plus'] == 1]
                variation_heatmap(data, outdir)
            else:
                data = df.copy()
            corr_matrix(data, loc, loc.lower(), outdir)
            corr_matrix(data, loc, loc.lower(), outdir, type='spearman')
    for col in [None, 'recip', 'by_date_recip']:
        outdir = get_output_dir(sub_dir=col)
        if col is not None:
            df = pd.read_csv(f"{get_input_dir()}/model_input_{col}_pairs.csv")
            df = log_tform(df, log_cols + ['net_flow', 'net_rate_100'])
        else:
            df = pd.read_csv(f"{get_input_dir()}/model_input.csv")
            df = log_tform(df, log_cols)
        eu = df[df['eu_plus'] == 1]
        if save_hists:
            facet_hist(df, [x for x in df.columns if 'log' in x], outdir)
        for string, data in {'EU+UK': eu, 'Global': df}.items():
            if save_pairplots:
                # columns chosen manually by inspection of previous plots
                cols = ['gdp_dest', 'hdi_dest',
                        'internet_dest', 'prox1', 'prox2']
                pairplot(data, cols, string, outdir)
        # if col == 'recip':
        #     for x in categorical_cols:
        #         print(f'Global dataset:\n{ttest(df, x)}')
        #         print(f'EU dataset:\n{ttest(eu, x)}')
    # # TODO this line plot is not quite right
    # # plt_over_time(get_output_dir())


if __name__ == "__main__":
    main()
    
