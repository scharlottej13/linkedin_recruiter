import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from prep_model_data import get_input_dir


def log_tform(df, cols):
    for x in cols:
        df[f'log{x}'] = np.log(df[f'{x}'])
    return df


def corr_matrix(df, cols, loc_str, suffix):
    cols = sorted(cols)
    # put the dependent variable first
    cols.insert(0, cols.pop(cols.index('flow')))
    # col_label_dict = dict(zip([f'log{x}' for x in cols], cols))
    col_label_dict = dict(zip(cols, cols))
    # corr = df[col_label_dict.keys()].corr()
    corr = df[cols].corr('spearman')
    plt.figure(figsize=(10,10))
    ax = sns.heatmap(
        corr, mask=np.triu(corr), annot=True, fmt='.1g',
        vmin=-1, vmax=1, center=0,
        cmap=sns.diverging_palette(20, 220, n=200),
        square=True
    )
    ax.set_xticklabels(
        col_label_dict.values(),
        rotation=45,
        horizontalalignment='right'
    )
    ax.set_yticklabels(col_label_dict.values())
    ax.set_title(f"{loc_str} Spearman's rank coefficients")
    ax.add_patch(Rectangle((0, 1), 1, 17, fill=False, edgecolor='blue', lw=3))
    plt.tight_layout()
    plt.savefig(f"/Users/scharlottej13/Nextcloud/linkedin_recruiter/outputs/sp_corr_matrix_{suffix}.png", dpi=300)

if __name__ == "__main__":
    df = pd.read_csv(f"{get_input_dir()}/model_input.csv", low_memory=False)
    log_vars = ['flow', 'users_orig', 'users_dest',
                'pop_orig', 'gdp_orig', 'hdi_orig', 'pop_dest', 'gdp_dest', 'hdi_dest', 'area_orig', 'area_dest',
                'internet_orig', 'internet_dest', 'dist_biggest_cities',
                'dist_pop_weighted', 'dist_unweighted']
    df = log_tform(df, log_vars)
    square_df = df.loc[df['comp'] == 1]
    square_eu = df.loc[(df['eu_orig'] == 1) & (
        df['eu_dest'] == 1) & (df['comp'] == 1)]
    lang_vars = ['prox1', 'prox2']
    corr_matrix(df, log_vars + lang_vars, 'Global', 'full')
    corr_matrix(square_df, log_vars + lang_vars, 'Global', 'recip')
    corr_matrix(square_eu, log_vars + lang_vars, 'EU', 'eu_recip')
