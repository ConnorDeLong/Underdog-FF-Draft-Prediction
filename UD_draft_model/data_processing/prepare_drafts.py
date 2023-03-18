import pandas as pd
import numpy as np


def update_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """ 
    Updates draft data columns to more appropriate dyptes. 

    Parameters
    ----------
    df
        Raw draft data.

    Returns
    -------
    DataFrame
        Draft/Pick level draft data.
    """
    
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

    Parameters
    ----------
    df
        Draft data processed through update_dtypes.

    Returns
    -------
    DataFrame
        Draft/Pick level draft data.
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
    Filters out drafts which do not have player attributes (team, position, etc.)
    as these will likely serve as features for the model.

    Parameters
    ----------
    df
        Draft data processed through update_dtypes.

    Returns
    -------
    DataFrame
        Draft/Pick level draft data.
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
    """ 
    Adds draft level attributes to the df.

    Parameters
    ----------
    df
        Draft data processed through update_dtypes.

    Returns
    -------
    DataFrame
        Draft/Pick level draft data.
    """

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

    Note
    ----
    IMPORTANT: The logic for this will need updated if more custom
    ranks are ever added.

    NO LONGER NEEDED - Custom ranks also need to be offset by one
    to prevent a player/day from having multiple adps.

    Parameters
    ----------
    df
        Draft data processed through add_draft_attrs.

    Returns
    -------
    DataFrame
        Draft/Pick level draft data.
    """

    df['ranks_type'] = np.where(df['draft_year'] == 2021, 'custom', 'actual')

    return df


def _add_lookup_vals(df_base: pd.DataFrame, df_lookups: pd.DataFrame, lookup_type: str
                    , join_col_name: str, final_col_name: str) -> pd.DataFrame:
    """ 
    Adds the ranks_val from the df_lookups dataset to df_base based off the lookup_type
    and updates its name to the final_col_name.
    Point of this is for the player attributes in the drafts data to align with those
    in the ranks data.

    Note
    ----
    IMPORTANT: If other years ever end up being added, they must be all be found on
    the df passed to df_lookups. Otherwise, only the last year's values will be shown.

    Parameters
    ----------
    df_base
        Draft data processed through add_draft_attrs.
    df_lookups
        Lookups data pulled from read_lookups.
    lookup_type
        Value from lookup_type field in df_lookups which indicates what will be mapped
        between the draft and rankings data.
        This can be "player", "team", or "position.
    join_col_name
        Name of the field from df_base that will be mapped to the rankings data.
    final_col_name
        Name of the column created.

    Returns
    -------
    DataFrame
        Draft/Pick level draft data.
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
    Adds a date col which aligns with the rankings that were used for the draft
    and accounts for early morning drafts which use rankings from the prior day.

    Parameters
    ----------
    df
        Draft data processed through add_draft_attrs.
    hour_thresh
        Last hour of the day that the date will be shifted
        back by a day.

    Returns
    -------
    DataFrame
        Draft/Pick level draft data.
    """

    date_change_filter = (df['draft_datetime'].dt.hour <= hour_thresh)
    df['ranks_draft_date'] = np.where(date_change_filter
                                    , df['draft_date'] - pd.Timedelta(days=1)
                                    , df['draft_date'])

    return df


def add_ranks_lookups(df: pd.DataFrame, df_lookups: pd.DataFrame) -> pd.DataFrame:
    """ 
    Adds the lookups required to map to the ranks df.

    Note
    ----
    Passed df must contain draft_year.

    Parameters
    ----------
    df
        Draft data processed through add_draft_attrs.
    df_lookups
        Lookups data pulled from read_lookups.

    Returns
    -------
    DataFrame
        Draft/Pick level draft data.
    """

    df = _add_lookup_vals(df, df_lookups, 'player', 'full_name', 'drafted_player')
    df = _add_lookup_vals(df, df_lookups, 'team', 'team_name', 'drafted_team')
    df = _add_lookup_vals(df, df_lookups, 'position', 'position', 'drafted_position')

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


def _expand_draft(df_draft: pd.DataFrame, df_ranks: pd.DataFrame,
                num_players: int) -> pd.DataFrame:
    """ 
    Expands the draft data so that each pick is represented by the top 
    number of num_picks players left on the board and creates the data 
    level that is necessary for modeling.

    Parameters
    ----------
    df_draft
        Draft data for ONE draft processed through add_ranks_lookups.
    df_lookups
        Rankings data pulled from read_ranks.
    num_players
        Number of the top available players that will be expanded
        for each pick (e.g. if num_players = 40, then the row count
        will increase by a factor of 40).

    Returns
    -------
    DataFrame
        Draft/Pick/Available Player level draft data.
    """

    # Lagged value used to build list of players already selected for each pick.
    keep_vars = ['draft_id', 'ranks_draft_date', 'number', 'drafted_player_key']
    df = df_draft[keep_vars].sort_values(by='number')
    df['drafted_player_key_l1'] = df['drafted_player_key'].shift(1)

    # Required to pull the ranks used for the draft.
    draft_date = df['ranks_draft_date'].iloc[0].strftime('%Y-%m-%d')

    keep_vars = ['player_key', 'rank_actual', 'team', 'pos', 'adp']
    rename_vars = {'rank_actual': 'avail_rank_actual', 'team': 'avail_team'
                    , 'pos': 'avail_position', 'adp': 'avail_projection_adp'}    
    _df_ranks = df_ranks.loc[df_ranks['date'] == draft_date][keep_vars]
    _df_ranks.rename(columns=rename_vars, inplace=True)

    # Loops through each individual player selection.
    zipped_cols = zip(df['draft_id'], df['drafted_player_key'], df['drafted_player_key_l1'])
    selections = []
    dfs = []
    for draft, player, player_l1 in zipped_cols:
        selections.append(player_l1)

        top_x_players = _df_ranks.loc[~_df_ranks['player_key'].isin(selections)].iloc[:num_players]
        top_x_players.rename(columns={'player_key': 'avail_player_key'}, inplace=True)
        
        # Expands player selection row by the top num_picks available players.
        _df = pd.DataFrame([[draft, player]], columns=['draft_id', 'drafted_player_key'])
        _df = pd.merge(_df, top_x_players, how='cross')

        dfs.append(_df)

    keep_vars = ['drafted_player_key', 'avail_player_key', 'avail_rank_actual'
                , 'avail_team', 'avail_position', 'avail_projection_adp']
    df_expanded = pd.concat(dfs)[keep_vars]

    df_draft = pd.merge(df_expanded, df_draft, on='drafted_player_key', how='left')

    return df_draft


def expand_all_drafts(df: pd.DataFrame, df_ranks: pd.DataFrame
                    , num_players: int) -> pd.DataFrame:
    """ 
    Expands each individual draft to the selected player/available player
    level with final df at the draft/selected player/available player level.

    Parameters
    ----------
    df_draft
        Draft data for ALL drafts processed through add_ranks_lookups.
    df_lookups
        Rankings data pulled from read_ranks.
    num_players
        Number of the top available players that will be expanded
        for each pick (e.g. if num_players = 40, then the row count
        will increase by a factor of 40).

    Returns
    -------
    DataFrame
        Draft/Pick/Available Player level draft data.
    """

    drafts = []
    draft_ids = list(df['draft_id'].drop_duplicates())
    for draft_id in draft_ids:
        df_draft = df.loc[df['draft_id'] == draft_id].copy()
        df_draft = _expand_draft(df_draft, df_ranks, num_players)

        drafts.append(df_draft)

    df_all_drafts = pd.concat(drafts)

    return df_all_drafts


def add_avail_player_number(df_expanded: pd.DataFrame) -> pd.DataFrame:
    """ 
    Adds the pick each available player was actually drafted at.
    This will be used to determine if the player was available
    in the next round for the user.

    Parameters
    ----------
    df_expanded
        Draft data for ALL drafts processed through expand_all_drafts.

    Returns
    -------
    DataFrame
        Draft/Pick/Available Player level draft data.
    """

    keep_vars = ['draft_id', 'drafted_player_key', 'number']
    df_drafted_players = df_expanded[keep_vars].drop_duplicates()

    rename_vars = {'number': 'avail_number', 'drafted_player_key': 'avail_player_key'}
    df_drafted_players.rename(columns=rename_vars, inplace=True)

    df = pd.merge(df_expanded, df_drafted_players
                    , on=['draft_id', 'avail_player_key']
                    , how='left')

    # Undrafted players need value to prevent being flagged as ever being picked.
    df['avail_number'] = df['avail_number'].fillna(9999)

    return df


def add_next_pick_number(
    df_expanded: pd.DataFrame, out_col: str='next_pick_number', filter_nulls: bool=True
) -> pd.DataFrame:
    """ 
    Adds the pick number of the next time the user will draft.
    Used to determine if the player was available in the next round.

    Note
    ----
    Picks at the turn use the pick following the next since the user
    will also be drafting back to back.

    Each user's last pick will be NULL, so these are filtered out.
    The second to last pick of the user drafting last will also removed
    since this is a turn pick.

    Parameters
    ----------
    df_expanded
        Draft data for ALL drafts processed through expand_all_drafts.

    Returns
    -------
    DataFrame
        Draft/Pick/Available Player level draft data.
    """

    df = df_expanded[['draft_id', 'draft_entry_id', 'number']].drop_duplicates()
    df.sort_values(by=['draft_id', 'draft_entry_id', 'number'], inplace=True)

    df['number_rl1'] = df['number'].shift(-1)
    df['number_rl2'] = df['number'].shift(-2)

    # Accounts for picks at the turn.
    df[out_col] = np.where(df['number_rl1'] - df['number'] == 1
                                    , df['number_rl2']
                                    , df['number_rl1'])

    # Fills picks pulled from other users/drafts with null values.
    df[out_col] = np.where(df[out_col] - df['number'] < 0
                                    , np.nan
                                    , df[out_col])

    df = pd.merge(df_expanded, df[['draft_id', 'number', out_col]]
                    , on=['draft_id', 'number'], how='left')

    if filter_nulls:
        df = df.loc[df[out_col].notna()]

    return df


def add_picked_indicator(df_expanded: pd.DataFrame) -> pd.DataFrame:
    """ 
    Adds a flag indicating if the available player was available in 
    the next round.

    This will serve as the response variable for the model.

    Parameters
    ----------
    df_expanded
        Draft data for ALL drafts processed through expand_all_drafts.

    Returns
    -------
    DataFrame
        Draft/Pick/Available Player level draft data.
    """

    df = add_avail_player_number(df_expanded)
    df = add_next_pick_number(df)

    df['ind_avail'] = np.where(df['avail_number'] >= df['next_pick_number'], 1, 0)
    df['ind_picked'] = np.where(df['ind_avail'] == 1, 0, 1)

    return df


def process_data(df_drafts: pd.DataFrame, df_ranks: pd.DataFrame
                , df_lookups: pd.DataFrame, num_players: int) -> pd.DataFrame:
    """ 
    Processes a (mostly) featureless dataset at the 
    Draft/Pick/Available Player level for modeling.

    Note
    ----
    Filters out the follwing: a\n
    - Drafts without player attributes a\n
    - Last pick of the draft for each user

    Drafts which use derived ranks will need further filtering to 
    account for later rounds lacking an adequate representation
    of rankings.

    Parameters
    ----------
    df_drafts
        Raw Draft/Pick level draft data.
    df_ranks
        Raw Day/Player level rankings data.
    df_lookups
        Raw Year/Lookup Type/Lookup Value lookups data. 
    num_players
        Number of the top available players that will be expanded
        for each pick (e.g. if num_players = 40, then the row count
        will increase by a factor of 40).

    Returns
    -------
    DataFrame
        Draft/Pick/Available Player level draft data.
    """
    
    df_updated_types = update_dtypes(df_drafts)
    df_complete_players = drafts_w_player_data(df_updated_types)
    df_draft_attrs = add_draft_attrs(df_complete_players)
    df_w_rank_type = add_draft_rank_type(df_draft_attrs)
    df_w_rank_lookups = add_ranks_lookups(df_w_rank_type, df_lookups)
    df_expanded = expand_all_drafts(df_w_rank_lookups, df_ranks, num_players)
    df_final = add_picked_indicator(df_expanded)

    return df_final


if __name__ == '__main__':
    import read_data

    DATA_FOLDER = '/home/cdelong/Python-Projects/UD-Draft-Model/Repo-Work/UD-Draft-Model/data'
    RANKS_FOLDER = '/home/cdelong/Python-Projects/UD-Draft-Model/Repo-Work/UD-Draft-Model\
    /data/2022/player_ranks'

    df_ranks = read_data.read_ranks(DATA_FOLDER, [2021, 2022])
    df_lookups = read_data.read_lookups(DATA_FOLDER, [2021, 2022])
    df_drafts = read_data.read_drafts(DATA_FOLDER, [2021, 2022])

    df = process_data(df_drafts, df_ranks, df_lookups, 40)

    print(len(df))

    # print(DATA_FOLDER)
