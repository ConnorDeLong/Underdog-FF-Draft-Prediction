import pandas as pd
import numpy as np
from os import listdir
from os import path
from typing import Union


def compile_ranks(folder_path: str) -> pd.DataFrame:
    """ Compiles all csvs in the folder path into one df. """

    files = listdir(folder_path)

    dfs = []
    for file in files:
        if file[:15] == 'df_player_ranks':
            full_path = path.join(folder_path, file)

            df = pd.read_csv(full_path)

            dfs.append(df)

    df = pd.concat(dfs)

    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year

    df['player_key'] = df['player'] \
                    + ' - ' + df['date'].astype('str') \
                    + ' - ' + df['adp'].astype('str')   

    # Required to differentiate from derived rank
    df.rename(columns={'rank': 'rank_actual'}, inplace=True)

    return df


def read_drafts(folder_path: str, years: list) -> pd.DataFrame:

    dfs = []
    for year in years:
        df_drafts = pd.read_csv(path.join(folder_path, f'{year}/df_drafts.csv'))
        df_info = pd.read_csv(path.join(folder_path, f'{year}/df_league_info.csv'))

        df_info = df_info[['id', 'source', 'title']]

        rename_vars = {'id': 'draft_id', 'source': 'draft_source', 'title': 'draft_title'}
        df_info.rename(columns=rename_vars, inplace=True)

        df = pd.merge(df_drafts, df_info, how='left', on='draft_id')
        dfs.append(df)

    df = pd.concat(dfs)
    df['full_name'] = df['first_name'] + ' ' + df['last_name']

    drop_vars = ['id', 'pick_slot_id', 'points', 'projection_points'
                , 'swapped', 'player_id', 'first_name', 'last_name']
    df.drop(columns=drop_vars, inplace=True)

    # Noticed a draft being duplicated.
    df.drop_duplicates(inplace=True)

    return df


def read_ranks(folder_path: str, years: list) -> pd.DataFrame:
    """  Reads in all Ranks data. """

    dfs = []
    for year in years:
        df = compile_ranks(path.join(DATA_FOLDER, f'{year}/player_ranks'))
        dfs.append(df)
    
    df = pd.concat(dfs)

    # type field only available if a custom ranks file is created.
    try:
        df['type'] = df['type'].fillna('actual')
    except:
        df['type'] = 'actual'

    return df


def read_lookups(folder_path: str, years: list) -> pd.DataFrame:
    """ Reads in all Lookups files. """
    dfs = []
    for year in years:
        df = pd.read_csv(path.join(DATA_FOLDER, f'{year}/lookups.csv'))
        dfs.append(df)
    
    df = pd.concat(dfs)

    return df


def update_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """ Updates columns to more appropriate dyptes. """
    
    # Replace null adps and update to float.
    df['projection_adp'] = np.where(df['projection_adp'] == '-', 216, df['projection_adp'])
    df['projection_adp'] = df['projection_adp'].astype('float')

    # Update created_at to datetime to use as possible filter.
    df['created_at'] = pd.to_datetime(df['created_at'], infer_datetime_format=True)

    return df


def drafts_w_player_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filters out drafts which do not have player attributes (team, position, etc.)
    as these will likely serve as features for the model.
    """

    df = df.copy()

    null_drafts = df.loc[df['full_name'].isnull()]

    null_drafts = null_drafts.drop_duplicates(subset='draft_id')['draft_id'].to_frame()
    null_drafts['ind_null_name_draft'] = 1

    df = pd.merge(df, null_drafts, on='draft_id', how='left')
    df = df.loc[df['ind_null_name_draft'].isnull()]

    df.drop(columns='ind_null_name_draft', inplace=True)

    return df


def _add_draft_dt(df: pd.DataFrame) -> pd.DataFrame:
    """ 
    Adds the datetime, date, and year of the draft.
    Note that created_at is datetime of each pick.
    """
    
    df_drafts = df[['draft_id', 'created_at']].copy()
    df_drafts.sort_values(by=['draft_id', 'created_at'], inplace=True)

    df_drafts.drop_duplicates(subset='draft_id', keep='first', inplace=True)
    df_drafts.rename(columns={'created_at': 'draft_datetime'}, inplace=True)

    df_drafts['draft_date'] = df_drafts['draft_datetime'].dt.normalize()
    df_drafts['draft_year'] = df_drafts['draft_datetime'].dt.year

    df = pd.merge(df, df_drafts, on='draft_id', how='left')

    return df


def add_draft_attrs(df: pd.DataFrame) -> pd.DataFrame:
    """ Adds draft level attributes. """

    # Adds number of teams by draft.
    by_vars = ['draft_id', 'draft_entry_id']
    draft_teams = df[by_vars].drop_duplicates(subset=by_vars)

    num_teams = draft_teams.groupby('draft_id').size().to_frame('num_teams')

    df = pd.merge(df, num_teams, on='draft_id', how='left')

    # Adds round and pick of the round by draft.
    df['round'] = ((df['number'] - 1) / df['num_teams']).astype('int') + 1
    df['round_pick'] = df['number'] - ((df['round'] - 1) * df['num_teams'])

    # Add datetime, date, and year of draft and year.
    df = _add_draft_dt(df)

    return df


def add_draft_rank_type(df: pd.DataFrame) -> pd.DataFrame:
    """
    This adds a rank_type column to the df which is required to determine
    if the date in df needs to be adjusted to map to the rankings used
    for the draft (see add_ranks_lookups function).

    IMPORTANT: The logic for this will need updated if more custom
    ranks are ever added.

    NO LONGER NEEDED - Custom ranks also need to be offset by one
    to prevent a player/day from having multiple adps.
    """

    df['ranks_type'] = np.where(df['draft_year'] == 2021, 'custom', 'actual')

    return df


def add_lookup_vals(df_base: pd.DataFrame, df_lookups: pd.DataFrame, lookup_type: str
                    , join_col_name: str, final_col_name: str) -> pd.DataFrame:
    """ 
    Adds the ranks_val from the df_lookups dataset to df_base based off the lookup_type
    and updates its name to the final_col_name.
    Point of this is for the player attributes in the drafts data to align with those
    in the ranks data.
    IMPORTANT: If other years ever end up being added, they must be all be found on
    the df passed to df_lookups. Otherwise, only the last year's values will be shown.
    """

    df_base = df_base.copy()
    df_lookups = df_lookups.loc[df_lookups['lookup_type'] == lookup_type].copy()

    df = pd.merge(df_base, df_lookups, how='left'
                , left_on=['draft_year', join_col_name]
                , right_on=['draft_year', 'drafts_val'])

    df.drop(columns=['lookup_type', 'drafts_val'], inplace=True)
    df.rename(columns={'ranks_val': final_col_name}, inplace=True)

    return df


def _add_rank_draft_date(df: pd.DataFrame, hour_thresh: int=5) -> pd.DataFrame:
    """
    Add a date col which aligns with the rankings that were used for the draft
    and accounts for early morning drafts which use rankings from the prior day.
    """

    date_change_filter = (df['draft_datetime'].dt.hour <= hour_thresh)
    df['ranks_draft_date'] = np.where(date_change_filter
                                    , df['draft_date'] - pd.Timedelta(days=1)
                                    , df['draft_date'])

    return df


def add_ranks_lookups(df: pd.DataFrame, df_lookups: pd.DataFrame) -> pd.DataFrame:
    """ 
    Adds the lookups required to map to the ranks df.
    IMPORATANT: Passed df must contain draft_year.
    """

    df = add_lookup_vals(df, df_lookups, 'player', 'full_name', 'drafted_player')
    df = add_lookup_vals(df, df_lookups, 'team', 'team_name', 'drafted_team')
    df = add_lookup_vals(df, df_lookups, 'position', 'position', 'drafted_position')

    df.drop(columns=['full_name', 'team_name', 'position'], inplace=True)

    # Draft date appears to be offset by a day relative to the ranks
    # for early morning drafts (or at least those with that timestamp).
    df = _add_rank_draft_date(df, hour_thresh=5)

    # Ranks data will be stacked with derived ranks from drafts w/o ranks data.
    # This will allow those drafts to link back to the stacked ranks data.
    df['drafted_player_key'] = df['drafted_player'] \
                    + ' - ' + df['ranks_draft_date'].astype('str') \
                    + ' - ' + df['projection_adp'].astype('str') 

    return df


def _add_rank_actual(df_drafts: pd.DataFrame, df_ranks: pd.DataFrame) -> pd.DataFrame:
    """ 
    Adds the actual rank of each player for every draft.
    This is to determine how often actual rank differs from derived.
    """
    
    df_base = df_drafts.copy()
    df_ranks = df_ranks.copy()

    keep_vars = ['player', 'date', 'adp', 'rank_actual']
    df_ranks = df_ranks[keep_vars]

    rename_vars = {'player': 'drafted_player'
                    , 'adp': 'projection_adp'
                    , 'date': 'ranks_draft_date'}
    df_ranks.rename(columns=rename_vars, inplace=True)

    df = pd.merge(df_base, df_ranks, how='left'
                , on=['drafted_player', 'projection_adp', 'ranks_draft_date'])

    return df


def _add_rank_derived(df: pd.DataFrame, by_var: str=None) -> pd.DataFrame:
    """ 
    Adds derived rank for each draft/player based off adp.
    Note that even early round derived ranks won't align
    with actual due to multiple players having the same ADP.
    """

    if by_var is None:
        by_var = 'draft_id'

    df = df.copy()
    df.sort_values(by=[by_var, 'projection_adp', 'number'], inplace=True)

    df['rank_derived'] = 1
    df['rank_derived'] = df.groupby(by_var)['rank_derived'].cumsum()

    # df.sort_values(by=[by_var, 'number'], inplace=True)

    return df


def add_ranks(df_drafts: pd.DataFrame, df_ranks: pd.DataFrame) -> pd.DataFrame:
    """ Adds all rank versions to df_drafts. """
    
    df = _add_rank_actual(df_drafts, df_ranks)
    df = _add_rank_derived(df)

    return df


def add_model_vars(df: pd.DataFrame) -> pd.DataFrame:
    """ Adds additional variables to test in the model. """

    df['actual_proj_adp_diff'] = df['projection_adp'] - df['number']
    df['rank_pick_diff'] = df['rank_actual'] - df['number']

    return df