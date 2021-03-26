import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from os import path, mkdir
from matplotlib.patches import Rectangle
from matplotlib.colors import LinearSegmentedColormap
from prep_model_data import get_input_dir, _get_working_dir
from scipy import stats
import statsmodels.stats.api as sms


def get_output_dir(custom_dir=None, sub_dir=None):
    if sub_dir:
        outdir = path.join(_get_working_dir(custom_dir), 'plots', sub_dir)
    else:
        outdir = path.join(_get_working_dir(custom_dir), 'plots')
    if not path.exists(outdir):
        mkdir(outdir)
    return outdir


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
    ax = plt.gca()
    ax.text(.1, .6, f"N = {len(data)}", transform=ax.transAxes)


def violins(df, prefix, output_dir):
    df = df.sort_values(by='query_date')
    for metric in ['flow', 'net_flow', 'net_rate_100']:
        ax = sns.violinplot(x="query_date", y=metric, data=df)
        ax.set_xticklabels(df['query_date'].unique(), rotation=45)
        plt.tight_layout()
        plt.savefig(f"{output_dir}/{prefix}_violin_{metric}.png", dpi=300)
        plt.close()


def facet_hist(df, plt_vars, output_dir):
    hist_df = df.replace({-np.inf: np.nan, np.inf: np.nan}
        ).sort_values(by='query_date')
    for plt_var in plt_vars:
        g = sns.FacetGrid(
            hist_df[[plt_var, 'query_date', 'eu']].dropna(), col="query_date",
            height=2, col_wrap=3, hue='eu'
        )
        g.map(sns.histplot, f"{plt_var}")
        g.set_titles(col_template="{col_name}")
        # g.map_dataframe(annotate)
        g.tight_layout()
        plt.savefig(f"{output_dir}/hist_{plt_var}.png", dpi=300)
        plt.close()


def pairplot(df, plt_vars, plt_name, output_dir):
    # TODO part of this is getting cut off? and the legend looks funky
    plt.figure(figsize=(10, 10))
    g = sns.pairplot(
        df.sort_values(by='query_date'), vars=plt_vars + ['flow'], hue='query_date',
        palette='crest', diag_kws=dict(fill=False), corner=True, dropna=True
    )
    plt.savefig(f"{output_dir}/{plt_name}_scatter.png", dpi=300)
    plt.close()


def corr_matrix(df, plt_vars, loc_str, suffix, output_dir, type='pearson'):
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
    plt.savefig(f"{output_dir}/{prefix}_corr_matrix_{suffix}.png", dpi=300)
    plt.close()


def data_availability(df, outdir):
    """Save heatmap showing for which countries we have reciprocal pairs."""
    assert df['recip'].isin([0,1]).values.all()
    # prep data
    recip_pairs = df[
        ['country_orig', 'country_dest', 'recip']
    ].drop_duplicates().rename(
        columns={'country_orig': 'Origin Country',
                 'country_dest': 'Destination Country'}
    ).pivot_table(
        values='recip', index='Origin Country',
        columns='Destination Country', fill_value=0)
    # create figure
    plt.figure(figsize=(10,10))
    # change colors to be binary, not continuous
    colors = ["lightgray", "salmon"]
    cmap = LinearSegmentedColormap.from_list('Custom', colors, len(colors))
    # make plot
    ax = sns.heatmap(recip_pairs, square=True, cmap=cmap, linewidths=.5,
                     cbar_kws={"shrink": .5})
    # Let the horizontal axes labeling appear on top.
    ax.xaxis.set_label_position('top') 
    ax.tick_params(top=True, bottom=False,
                   labeltop=True, labelbottom=False)
    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(), rotation=-30, ha="right",
             rotation_mode="anchor")
    # set colorbar labels
    colorbar = ax.collections[0].colorbar
    colorbar.set_ticks([0.25,0.75])
    colorbar.set_ticklabels(['excluded', 'included'])
    plt.tight_layout()
    plt.savefig(f"{outdir}/heatmap_recip_pairs.png", dpi=300)
    plt.close()


def main(save_hists=False, save_heatmaps=False, save_pairplots=False, save_violins=True):
    for col in ['recip', 'by_date_recip']:
        outdir = get_output_dir(sub_dir=col)
        df = pd.read_csv(f"{get_input_dir()}/model_input_{col}_pairs.csv", low_memory=False)
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
        eu = df[df['eu'] == 1]
        if save_hists:
            # histograms of each variable, with facets for collection dates
            facet_hist(df, log_cols + categorical_cols, outdir)
        for string, data in {'EU': eu, 'Global': df}.items():
            if save_violins:
                violins(data, string, outdir)
            if save_heatmaps:
                corr_matrix(data, cont_cols, string, string.lower(), outdir)
                # add prox1-- this variable is sort of categorical?
                corr_matrix(
                    data, cont_cols + ['prox1'], string, string.lower(), outdir,
                    type='spearman')
            if save_pairplots:
                # columns chosen manually by inspection of previous plots
                if string == 'EU':
                    cols = ['cnl', 'gdp_dest', 'hdi_dest', 'internet_dest', 'prox1',
                            'users_orig', 'users_dest', 'pop_orig', 'pop_dest']
                else:
                    cols = ['users_dest', 'users_orig', 'gdp_dest', 'gdp_orig',
                            'hdi_dest', 'hdi_orig', 'internet_orig', 'internet_dest']
                pairplot(data, cols, string, outdir)

        for col in categorical_cols:
            print('Global dataset')
            ttest(df, col)
            print('EU dataset')
            ttest(eu, col)

    # save another thing
    data_availability(
        pd.read_csv(f"{get_input_dir()}/model_input.csv",
                    low_memory=False).query("eu_uk == 1"),
        get_output_dir())


if __name__ == "__main__":
    main()
    
