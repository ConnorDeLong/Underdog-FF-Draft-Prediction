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


def add_round_dummies(df: pd.DataFrame) -> pd.DataFrame:
    for round in range(1, 18):
        df[f"ind_round_v1_{round}"] = np.where(df["round"] ==  round, 1, 0)

    round_ranges_v1 = [
        [1, 3],
        [4, 6],
        [7, 9],
        [10, 12],
        [13, 15],
        [16, 18]
    ]

    for rng in round_ranges_v1:
        lower = rng[0]
        upper = rng[1]

        df[f"ind_round_v2_{lower}_{upper}"] = np.where(
            (df["round"] >= lower) & (df["round"] <= upper), 1, 0
        )

    return df


def add_round_interactions(df: pd.DataFrame) -> pd.DataFrame:
    round_cols = [col for col in list(df.columns) if col.startswith("ind_round_v1")]

    base_cols = {
        "diff_cur_rank_picks_btwn": "diff_picks",
        "ind_rank_btwn": "ind_rank_btwn"
    }
    for key, val in base_cols.items():
        for col in round_cols:
            df[f"{val}_{col}"] = df[key] * df[col]

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

    df = add_round_dummies(df.copy())
    df = add_round_interactions(df.copy())

    return df