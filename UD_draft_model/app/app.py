from os.path import join
import pickle

import pandas as pd
import numpy as np
import streamlit as st
from selenium.common.exceptions import WebDriverException

import UD_draft_model.app.prepare_data as prepare_data
from UD_draft_model.app.draft import Draft
from UD_draft_model.app.get_credentials import Credentials, get_headers
import UD_draft_model.scrapers.scrape_site.scrape_league_data as scrape_site
import UD_draft_model.scrapers.scrape_site.pull_bearer_token as pb
import UD_draft_model.data_processing.prepare_drafts as prepare_drafts
import UD_draft_model.data_processing.add_features as add_features
from UD_draft_model.modeling.model_version import ModelVersion

# REMOVE LATER
import UD_draft_model.credentials.credentials as _credentials

CHROMEDRIVER_PATH = "/usr/bin/chromedriver"
PATH = (
    "/home/cdelong/Python-Projects/UD-Draft-Model/"
    + "Repo-Work/UD-Draft-Model/UD_draft_model/app"
)

MODEL_PATH = "../modeling/models"
MODEL = "LogisticRegression_v01_v001"


url = "https://underdogfantasy.com/lobby"
chromedriver_path = "/usr/bin/chromedriver"
username = _credentials.username
password = _credentials.password
headers = get_headers(username, password, chromedriver_path, save_headers=True)
valid_credentials = True

# credentials = Credentials(CHROMEDRIVER_PATH, session_state=st.session_state)
# credentials.enter_ud_credentials()

# headers = credentials.headers
# valid_credentials = credentials.valid_credentials

if "current_pick_number" not in st.session_state:
    st.session_state["current_pick_number"] = -1

if "df_w_probs" not in st.session_state:
    st.session_state["df_w_probs"] = pd.DataFrame()


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


@st.cache_data
def get_draft_params(df_active: pd.DataFrame, draft_id: str) -> dict:
    """
    Creates a dict of parameters required to pull data for the draft_id passed.

    Parameters
    ----------
    df_active : pd.DataFrame
        All active drafts.
    draft_id : str
        ID of draft to create params for.

    Returns
    -------
    dict
        Required draft params.
    """

    df = df_active.loc[df_active["id"] == draft_id]

    draft_entry_id = df["draft_entry_id"].iloc[0]
    slate_id = df["slate_id"].iloc[0]
    scoring_type_id = df["scoring_type_id"].iloc[0]
    rounds = df["rounds"].iloc[0]
    draft_status = df["status"].iloc[0]

    params = {
        "draft_entry_id": draft_entry_id,
        "slate_id": slate_id,
        "scoring_type_id": scoring_type_id,
        "rounds": rounds,
        "draft_id": draft_id,
        "draft_status": draft_status,
    }

    return params


@st.cache_data
def get_active_drafts(headers: dict) -> pd.DataFrame:
    active_drafts = scrape_site.DraftsActive(headers)
    df_active = active_drafts.create_df_active_drafts()

    print("Active drafts pulled")

    return df_active


def refresh_drafts(headers: dict):
    return get_active_drafts(headers)


@st.cache_data
def get_players(headers: dict, params: dict) -> pd.DataFrame:
    # These should be initialized upon opening the app
    player_vars = [
        "appearance_id",
        "player_id",
        "position",
        "first_name",
        "last_name",
        "abbr",
        "team_name",
        "adp",
        "season_projected_points",
    ]
    refs = scrape_site.ReferenceData(
        headers, params["slate_id"], params["scoring_type_id"]
    )
    df_players = refs.create_df_players_master()

    print("Pulled players")

    return df_players


@st.cache_data
def get_draft_entries(headers: dict, params: dict) -> pd.DataFrame:
    draft_id = [params["draft_id"]]
    draft_detail = scrape_site.DraftsDetail(draft_id, headers)
    df_entries = draft_detail.create_df_draft_entries()

    return df_entries


def get_draft(headers: dict, params: dict) -> pd.DataFrame:
    draft_id = [params["draft_id"]]
    draft_detail = scrape_site.DraftsDetail(draft_id, headers)
    df_draft = draft_detail.create_df_drafts()

    return df_draft


def select_draft(draft_ids: list, headers: dict) -> str:

    with st.sidebar:
        draft_id = st.selectbox("Select draft", draft_ids, on_change=clear_cache)
        st.button("Refresh", on_click=refresh_drafts, args=[headers])

    if len(draft_ids) == 0:
        st.write("No active drafts to select from")

    return draft_id


def clear_cache() -> None:
    st.cache_data.clear()


model = load_model(join(MODEL_PATH, MODEL))


if valid_credentials:
    df_active = get_active_drafts(headers)

    if df_active is None:
        draft_ids = []
    else:
        draft_ids = tuple(df_active["id"])

    draft_id = select_draft(draft_ids, headers)

    if df_active is not None:
        params = get_draft_params(df_active, draft_id)

        draft = Draft(params, headers, model)

        # params["draft_status"] = "drafting"
        if params["draft_status"] == "drafting":
            draft.initialize_draft_attrs()
            draft.update_draft_attrs()
            draft.create_df_final_players()

            if draft.df_final_players is not None:
                st.dataframe(draft.df_final_players)
        else:
            st.write("Draft has not been filled")

st.button("Re-run")

"""
if valid_credentials:
    df_active = get_active_drafts(headers)

    if df_active is None:
        draft_ids = []
    else:
        draft_ids = tuple(df_active["id"])

    draft_id = select_draft(draft_ids, headers)

    if df_active is not None:
        params = get_draft_params(df_active, draft_id)

        # params["draft_status"] = "drafting"
        if params["draft_status"] == "drafting":
            df_players = get_players(headers, params)
            df_entries = get_draft_entries(headers, params)
            df_board = prepare_data.create_draft_board(df_entries, params)

            # IMPORTANT: this will result in an IndexError until the first pick
            # has been selected
            df_draft = get_draft(headers, params)
            df_board = prepare_data.update_board(df_board, df_draft)
            df_cur_pick = prepare_data.get_current_pick(df_board)

            current_pick_number = df_cur_pick["number"].iloc[0]

            if st.session_state["current_pick_number"] != current_pick_number:
                st.session_state["current_pick_number"] = current_pick_number

                df_w_probs = prepare_data.final_players_df(
                    df_players.copy(), df_draft.copy(), df_cur_pick.copy(), model
                )

                st.session_state["df_w_probs"] = df_w_probs

            if len(st.session_state["df_w_probs"]) > 0:
                st.dataframe(st.session_state["df_w_probs"])
        else:
            st.write("Draft has not been filled")

st.button("Re-run")

print(df_draft)
"""
