import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from os import path
from matplotlib.patches import Rectangle
from prep_model_data import get_input_dir, _get_working_dir
from scipy import stats
import statsmodels.stats.api as sms


def get_output_dir(custom_dir=None):
    return path.join(_get_working_dir(custom_dir), 'plots')


def get_log_cols(continuous_cols):
    # looked at all the variables, then picked the skewed distributions
    log_vars = ['users', 'pop', 'gdp', 'area']
    return [
        f'{x}_{y}' for y in ['dest', 'orig']
        for x in log_vars
    # just use count of flow for now
    ] + ['flow', 'csl', 'cnl', 'prox2'] + [x for x in continuous_cols if 'dist' in x]


def log_tform(df, log_cols):
    df[log_cols] = df[log_cols].apply(np.log)
    return df


def ttest(df, grp_var, date='2020-10-08'):
    # TODO include other dates of data collection
    a = df[(df[f'{grp_var}'] == 1) & (df['query_date'] == date)]['flow'].values
    b = df[(df[f'{grp_var}'] == 0) & (df['query_date'] == date)]['flow'].values
    print(f'T test for {grp_var}')
    print(stats.ttest_ind(a, b, equal_var=False))
    cm = sms.CompareMeans(sms.DescrStatsW(a), sms.DescrStatsW(b))
    print(cm.tconfint_diff(usevar='unequal'))


def annotate(data, **kws):
    n = len(data)
    ax = plt.gca()
    ax.text(.1, .6, f"N = {n}", transform=ax.transAxes)


def pairplot(df, plt_vars, plt_name):
    # TODO part of this is getting cut off? and the legend looks funky
    plt.figure(figsize=(10, 10))
    g = sns.pairplot(
        df.sort_values(by='query_date'), vars=plt_vars + ['flow'], hue='query_date',
        palette='crest', diag_kws=dict(fill=False), corner=True, dropna=True
    )
    plt.savefig(f"{get_output_dir()}/{plt_name}.png", dpi=300)
    plt.close()


def facet_hist(df, plt_vars):
    hist_df = df.replace({-np.inf: np.nan, np.inf: np.nan}
        ).sort_values(by='query_date')
    for plt_var in plt_vars:
        g = sns.FacetGrid(
            hist_df[[plt_var, 'query_date']].dropna(), col="query_date",
            height=2, col_wrap=3
        )
        g.map(sns.histplot, f"{plt_var}")
        g.set_titles(col_template="{col_name}")
        g.map_dataframe(annotate)
        g.tight_layout()
        plt.savefig(f"{get_output_dir()}/hist_{plt_var}.png", dpi=300)
        plt.close()


def corr_matrix(df, plt_vars, loc_str, suffix, type='pearson'):
    # put the dependent variable first
    cols = sorted(plt_vars)
    cols.insert(0, cols.pop(cols.index('flow')))
    if type == 'pearson':
        prefix = 'p'
        title_str = "Pearson's correlation"
    elif type == 'spearman':
        prefix = 'sp'
        title_str = "Spearman's rank"
    else:
        ValueError, f"Type must be spearman or pearson, but was: {type}"
    corr = df[cols].corr(type)
    plt.figure(figsize=(10,10))
    ax = sns.heatmap(
        corr, mask=np.triu(corr), annot=True, fmt='.1g',
        vmin=-1, vmax=1, center=0, square=True,
        cmap=sns.diverging_palette(20, 220, n=200)
    )
    ax.set_xticklabels(cols, rotation=45, horizontalalignment='right')
    ax.set_title(f"{loc_str} {title_str} coefficients")
    ax.add_patch(Rectangle((0, 1), 1, len(plt_vars), fill=False, edgecolor='blue', lw=3))
    plt.tight_layout()
    plt.savefig(f"{get_output_dir()}/{prefix}_corr_matrix_{suffix}.png", dpi=300)
    plt.close()


def main(save_hists=False, save_heatmaps=False, save_pairplots=False):
    df = pd.read_csv(f"{get_input_dir()}/model_input.csv", low_memory=False)
    categorical_cols = ['contig', 'comlang_ethno', 'colony', 'comcol',
                        'curcol', 'col45', 'col', 'smctry']
    cont_cols = [
        'flow', 'net_flow', 'net_rate_100', 'users_orig', 'users_dest',
        'pop_orig', 'gdp_orig', 'hdi_orig', 'pop_dest', 'gdp_dest', 'hdi_dest',
        'area_orig', 'area_dest', 'internet_orig', 'internet_dest',
        'dist_biggest_cities', 'dist_pop_weighted', 'dist_unweighted',
        'csl', 'cnl', 'prox2'
    ]
    log_cols = get_log_cols(cont_cols)
    df = log_tform(df, log_cols)
    square_df = df.loc[df['comp'] == 1]
    eu = square_df.loc[(df['eu_orig'] == 1) & (df['eu_dest'] == 1)]
    if save_hists:
        # histograms of each variable, with facets for collection dates
        facet_hist(square_df, log_cols + categorical_cols)
    if save_heatmaps:
        corr_matrix(df, cont_cols, 'Global', 'global')
        corr_matrix(square_df, cont_cols, 'Global', 'global_recip')
        corr_matrix(eu, cont_cols, 'EU', 'eu_recip')
        # add prox1-- this variable is sort of categorical?
        corr_matrix(square_df, cont_cols + ['prox1'], 'Global', 'global_recip', type='spearman')
        corr_matrix(eu, cont_cols + ['prox1'], 'EU', 'eu_recip', type='spearman')
    
    if save_pairplots:
        pairplot(
            eu,
            ['cnl', 'gdp_dest', 'hdi_dest', 'internet_dest', 'prox1',
            'users_orig', 'users_dest', 'pop_orig', 'pop_dest'], 'eu_scatter')
        pairplot(
            square_df,
            ['gdp_dest', 'gdp_orig', 'hdi_dest', 'hdi_orig',
            'internet_orig', 'internet_dest', 'users_dest', 'users_orig'],
            'global_scatter'
        )

    for col in categorical_cols:
        print('Global dataset')
        ttest(square_df, col)
        print('EU dataset')
        ttest(eu, col)


if __name__ == "__main__":
    main()
    
