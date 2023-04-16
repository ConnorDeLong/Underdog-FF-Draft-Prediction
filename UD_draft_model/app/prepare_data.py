from os.path import join
import pickle

import pandas as pd
import numpy as np
import streamlit as st
import getpass

import UD_draft_model.scrapers.scrape_site.scrape_league_data as scrape_site
import UD_draft_model.scrapers.scrape_site.pull_bearer_token as pb
import UD_draft_model.data_processing.prepare_drafts as prepare_drafts
import UD_draft_model.data_processing.add_features as add_features
from UD_draft_model.modeling.model_version import ModelVersion


def create_draft_board(df_entries: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Creates a df of all user/pick numbers given the entries of a snake draft.

    Parameters
    ----------
    df_entries : pd.DataFrame
        All entries in the draft.
        Note that the draft must be full
    num_rounds : int
        Number of rounds in the draft.

    Returns
    -------
    pd.DataFrame
        Draft board containing each pick number for every entry.
    """

    df_asc = df_entries.sort_values(by="pick_order")
    df_desc = df_entries.sort_values(by="pick_order", ascending=False)

    dfs = []
    for round in range(1, params["rounds"] + 1):
        if round % 2 == 0:
            df_round = df_desc.copy()
        else:
            df_round = df_asc.copy()

        df_round["round"] = round

        dfs.append(df_round)

    df = pd.concat(dfs).reset_index(drop=True)
    df["number"] = df.index + 1
    df.rename(columns={"id": "draft_entry_id"}, inplace=True)

    keep_vars = ["draft_id", "draft_entry_id", "user_id", "username", "round", "number"]

    df = df[keep_vars]

    df = prepare_drafts.add_next_pick_number(df, filter_nulls=False)
    df = add_user_next_pick_number(df, params["draft_entry_id"])

    return df


def add_user_next_pick_number(
    df_board: pd.DataFrame, draft_entry_id: str
) -> pd.DataFrame:
    """
    Adds the pick number of the next pick of interest for the user using
    the app rather than the user currently drafting. "Next pick of interest"
    refers to the pick number that follows the user's upcoming pick.

    next_pick_number is used to create features that indicate how each players'
    rank relates to the # of picks between the current pick and the
    next pick of the user currently drafting. Therefore, probability estimates
    will be from the perspective of this user which isn't relevant to the user
    actually utilizing the model. For example, if the user is drafting from pick 6
    and the draft is currently at the 10th pick, probability estimates for pick
    15 are useless. Instead, estimates for pick 30 would allow the user to
    start preparing for their next pick.

    IMPORTANT: Using this will result in feature and target distributions
    being different from training (e.g. max picks between will be 48 vs. 24)
    which could throw the predictions off. However, this should be insignificant
    once the draft is within a handful of picks from the user.

    Parameters
    ----------
    df_board : pd.DataFrame
        Draft board containing each pick number for every entry.
    draft_entry_id : str
        Draft entry ID to base the next pick number off of.

    Returns
    -------
    pd.DataFrame
        Draft board with the next pick number based off the draft_entry_id
        passed.
    """

    df_user = df_board.loc[df_board["draft_entry_id"] == draft_entry_id].copy()
    df_user.sort_values(by="number", inplace=True)

    df_user["next_pick_number_2"] = df_user["next_pick_number"].shift(-1)

    rename_vars = {
        "number": "user_number",
        "next_pick_number": "user_next_pick_number",
        "next_pick_number_2": "user_next_pick_number_2",
    }
    keep_vars = ["round", "number", "next_pick_number", "next_pick_number_2"]
    df_user = df_user[keep_vars].rename(columns=rename_vars)

    # User's next pick number needs to be named 'next_pick_number' for the
    # add_features function.
    df_all = df_board.rename(columns={"next_pick_number": "next_pick_number_og"})

    df = pd.merge(df_all, df_user, how="left", on="round")
    df["next_pick_number"] = np.where(
        df["number"] <= df["user_number"],
        df["user_next_pick_number"],
        df["user_next_pick_number_2"],
    )

    df.drop(columns=list(rename_vars.values()), inplace=True)

    return df


def update_board(df_board: pd.DataFrame, df_draft: pd.DataFrame) -> pd.DataFrame:
    """
    Updates the draft board with the selections made.

    Parameters
    ----------
    df_board : pd.DataFrame
        Draft board containing each pick number for every entry.
    df_draft : pd.DataFrame
        All draft selections that have been made so far.

    Returns
    -------
    pd.DataFrame
        Draft board that contains the player selection made at each pick.
    """

    df = pd.merge(
        df_board, df_draft, how="left", on=["draft_id", "draft_entry_id", "number"]
    )

    return df


def get_current_pick(df_board: pd.DataFrame) -> pd.DataFrame:
    """
    Filters the draft board down to the current pick.

    Parameters
    ----------
    df_board : pd.DataFrame
        Draft board that includes all current selections.

    Returns
    -------
    pd.DataFrame
        Filtered Draft board that only contains the next pick to select
        a player.
    """

    df = df_board.loc[df_board["appearance_id"].isnull()].iloc[0:1]

    return df


def get_avail_players(df_players: pd.DataFrame, df_draft: pd.DataFrame) -> pd.DataFrame:
    """
    Pulls the remaining available players to draft.

    Parameters
    ----------
    df_players : pd.DataFrame
        All players that could/can be selected in the draft.
    df_draft : pd.DataFrame
        All draft selections that have been made so far.

    Returns
    -------
    pd.DataFrame
        All players that have NOT been drafted.
    """

    df = (
        df_players.loc[~df_players["appearance_id"].isin(df_draft["appearance_id"])]
        # .iloc[:100]
    )

    return df


def add_avail_players(
    df_cur_pick: pd.DataFrame, df_avail_players: pd.DataFrame
) -> pd.DataFrame:
    """
    Joins the available players onto the current pick df that is required
    for the model features and prediction.

    Parameters
    ----------
    df_cur_pick : pd.DataFrame
        Filtered Draft board that only contains the next pick to select
        a player.
    df_avail_players : pd.DataFrame
        All players that have NOT been drafted.

    Returns
    -------
    pd.DataFrame
        All players that have NOT been drafted with current pick data.
    """

    left_vars = [
        "draft_id",
        "draft_entry_id",
        "user_id",
        "username",
        "round",
        "number",
        "next_pick_number",
    ]
    df = pd.merge(df_cur_pick[left_vars], df_avail_players, how="cross")
    df.reset_index(inplace=True, drop=True)

    return df


@st.cache_resource
def load_model(file_path: str) -> ModelVersion:
    """
    Loads the ModelVersion object containing the model to be used for creating
    predictions.

    Parameters
    ----------
    file_path : str
        Path to the ModelVersion object

    Returns
    -------
    ModelVersion
        ModelVersion object with model to be used.
    """
    dbfile = open(file_path, "rb")
    obj = pickle.load(dbfile)
    dbfile.close()

    print("model loaded")

    return obj


def create_predictions(df: pd.DataFrame, model: ModelVersion) -> np.ndarray:
    """
    Applies the model to the df to create new predictions.

    Parameters
    ----------
    df : pd.DataFrame
        df of all players to create a probability estimate for.
    model : ModelVersion
        ModelVersion obj that contains the model to use for predictions.

    Returns
    -------
    np.ndarray
        1D array containing the probability estimates.
    """

    df_features = df[model.metadata["features"]]

    y_pred_prob = model.model.predict_proba(df_features)
    y_pred_prob = y_pred_prob[:, 1]

    return y_pred_prob


def merge_prediction(df: pd.DataFrame, pred: np.array, out_col: str) -> pd.DataFrame:
    """
    Merges the model's predicions back onto the full df.

    Parameters
    ----------
    df : pd.DataFrame
        df of all available players to draft.
    pred : np.array
        1D array of probability estimates.
    out_col : str
        Name of the probability estiamte column.

    Returns
    -------
    pd.DataFrame
        df of all available players to draft with the probability estimate
        of being picked added.
    """

    df = df.copy()
    df.reset_index(inplace=True, drop=True)

    pred = pd.DataFrame(pred, columns=[out_col])

    df = pd.concat([df, pred], axis=1)
    df[out_col] = df[out_col].astype(float).round(2)

    return df


def final_players_df(
    df_players: pd.DataFrame, df_draft: pd.DataFrame, df_cur_pick: pd.DataFrame, model
) -> pd.DataFrame:
    """
    Selects the final columns to display

    Parameters
    ----------
    df : pd.DataFrame
        _description_

    Returns
    -------
    pd.DataFrame
        _description_
    """

    df_avail_players = get_avail_players(df_players, df_draft)
    df_w_players = add_avail_players(df_cur_pick, df_avail_players)

    df_w_features = add_features.add_features(df_w_players)

    probs = create_predictions(df_w_features, model)
    df_w_probs = merge_prediction(df_w_features, probs, "prob")

    df_w_probs["full_name"] = df_w_probs["first_name"] + " " + df_w_probs["last_name"]

    rename_cols = {
        "full_name": "Player",
        "position": "Position",
        "abbr": "Team",
        "adp": "ADP",
        "prob": "Next Pick Selected Probability",
    }

    df_w_probs = df_w_probs[list(rename_cols.keys())]
    df_w_probs = df_w_probs.rename(columns=rename_cols)

    return df_w_probs
