import pandas as pd
from os import listdir
from os import path


def _compile_ranks(folder_path: str) -> pd.DataFrame:
    """ 
    Compiles all daily rankings csvs into one df.

    Parameters
    ----------
    folder_path
        Full path to the folder.

    Returns
    -------
    DataFrame
        Day/Player level data from every day in the
        folder path.
    """

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
    """ 
    Compiles each year of draft data into one df.

    Parameters
    ----------
    folder_path
        Full path to the main data folder.
    years
        The years of draft data to pull in.
        Note that each year is a folder within the folder_path.

    Returns
    -------
    DataFrame
        Draft/Pick level draft data from every day in the
        folder path.
    """

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
    """ 
    Compiles each year of rankings data into one df.

    Note
    ----
    Some years will contain *actual* rankings (i.e. the true ranking
    of each player on a particular day) while others will used derived
    rankings (i.e. determined by the adp of each player from a draft for 
    a day).

    Parameters
    ----------
    folder_path
        Full path to the main data folder.
    years
        The years of draft data to pull in.
        Note that each year is a folder within the folder_path.

    Returns
    -------
    DataFrame
        Day/Player level rankings data from every day in the
        folder path.
    """

    dfs = []
    for year in years:
        df = _compile_ranks(path.join(folder_path, f'{year}/player_ranks'))
        dfs.append(df)
    
    df = pd.concat(dfs)

    # type field only available if a custom ranks file is created.
    try:
        df['type'] = df['type'].fillna('actual')
    except:
        df['type'] = 'actual'

    return df


def read_lookups(folder_path: str, years: list) -> pd.DataFrame:
    """ 
    Compiles each year of lookups data into one df.
    This is necessary to map each unique player from the 
    draft data to the rankings data.

    Parameters
    ----------
    folder_path
        Full path to the main data folder.
    years
        The years of draft data to pull in.
        Note that each year is a folder within the folder_path.

    Returns
    -------
    DataFrame
        Year/Lookup Type level data from year.
    """

    dfs = []
    for year in years:
        df = pd.read_csv(path.join(folder_path, f'{year}/lookups.csv'))
        dfs.append(df)
    
    df = pd.concat(dfs)

    return df