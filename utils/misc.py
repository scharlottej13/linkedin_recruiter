"""Miscellaneous"""
import pandas as pd

def no_duplicates(df, id_cols, value_col, verbose=False):
    check_cols = id_cols + [value_col]
    dups = df[df[id_cols].duplicated(keep=False)][check_cols]
    if len(dups) > 0:
        # try to fix duplicates
        # variance should be 0 if all values of value_col are the same
        var = dups.groupby(id_cols)[value_col].var()
        if (var == 0).values.all():
            return True
        else:
            if verbose:
                print(f"Flow values differ, check it!:\n {var[var != 0]}")
            return False
    else:
        return True


def test_no_duplicates():
    id_cols = ['a', 'b']
    value_col = 'c'
    df = pd.DataFrame(
        {'a': ['x', 'x', 'r', 'r'], 'b': ['y', 'y', 'p', 'p'],
         'c': [1, 1, 1, 2]}
    )
    # this should return False
    assert not no_duplicates(df, id_cols, value_col)
    df.at[3, 'c'] = 1
    # and this should return True
    assert no_duplicates(df, id_cols, value_col)
