import pandas as pd

import UD_draft_model.data_processing.read_data as read_data
import UD_draft_model.data_processing.prepare_drafts as prepare_drafts
import UD_draft_model.data_processing.add_features as add_features


def create_model_data(folder_path: str, years: list, num_players: int) -> pd.DataFrame:
    """
    Creates modeling data from drafts completed in the years list at
    the Draft/Pick/Available Player level where num_players
    determines the number of available to be included for each pick.
    """

    df_ranks = read_data.read_ranks(folder_path, years)
    df_lookups = read_data.read_lookups(folder_path, years)
    df_drafts = read_data.read_drafts(folder_path, years)

    df = prepare_drafts.process_data(df_drafts, df_ranks, df_lookups, num_players)
    df = add_features.add_features(df)

    return df
