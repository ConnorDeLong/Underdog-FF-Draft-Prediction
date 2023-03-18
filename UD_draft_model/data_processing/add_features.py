import pandas as pd
import numpy as np


def add_current_rank(df: pd.DataFrame) -> pd.DataFrame:
    """ 
    Adds derived rank for each draft/player based off adp.
    Note that even early round derived ranks won't align
    with actual due to multiple players having the same ADP.
    """

    by_vars = ['draft_id', 'number']
    df['avail_cur_rank_actual'] = 1
    df['avail_cur_rank_actual'] = df.groupby(by_vars)['avail_cur_rank_actual'].cumsum()

    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a handful of basic features that capture each players ranking
    relative to the next pick.
    """

    df = add_current_rank(df)

    df['picks_btwn'] = df['next_pick_number'] - df['number']
    df['diff_cur_rank_picks_btwn'] = df['avail_cur_rank_actual'] -\
        df['picks_btwn']

    ind_rank_btwn = np.where(df['diff_cur_rank_picks_btwn'] <= 0, 1, 0)
    df['ind_rank_btwn'] = ind_rank_btwn

    return df