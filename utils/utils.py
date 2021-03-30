"""The dreaded utils misc. file."""

#TODO it'd be nice to have a helper function for interactive data exploration
# that dropped the reciprocal pairs when you don't need to see them
# eg seeing A -> B and B -> A not necessary


def _get_working_dir(custom_dir):
    pc = "N:/johnson/linkedin_recruiter"
    mac = "/Users/scharlottej13/Nextcloud/linkedin_recruiter"
    check_dirs = [pc, mac]
    if custom_dir:
        check_dirs.insert(0, custom_dir)
    for check_dir in check_dirs:
        if path.exists(check_dir):
            return check_dir
    # if this line is exectued, no path was returned
    assert any([path.exists(x) for x in check_dirs]), \
        f"Working directory not found, checked:\n {check_dirs}"


def get_input_dir(custom_dir=None):
    # TODO read in filepaths from config, then set in init
    # don't love how this f'n is called all the time
    return path.join(_get_working_dir(custom_dir), 'inputs')


def save_output(df, filename):
    """Auto archive output saving."""
    today = datetime.now().date()
    active_dir = get_input_dir()
    archive_dir = path.join(active_dir, '_archive')
    if not path.exists(archive_dir):
        mkdir(archive_dir)
    df.to_csv(path.join(active_dir, f'{filename}.csv'), index=False)
    df.to_csv(path.join(archive_dir, f'{filename}_{today}.csv'), index=False)


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
