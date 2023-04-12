from os.path import join
import pickle

import pandas as pd
import numpy as np
import streamlit as st
from selenium.common.exceptions import WebDriverException

import UD_draft_model.scrapers.scrape_site.scrape_league_data as scrape_site
import UD_draft_model.scrapers.scrape_site.pull_bearer_token as pb
import UD_draft_model.data_processing.prepare_drafts as prepare_drafts
import UD_draft_model.data_processing.add_features as add_features
from UD_draft_model.modeling.model_version import ModelVersion

# REMOVE LATER
import UD_draft_model.credentials as credentials

CHROMEDRIVER_PATH = "/usr/bin/chromedriver"
PATH = (
    "/home/cdelong/Python-Projects/UD-Draft-Model/"
    + "Repo-Work/UD-Draft-Model/UD_draft_model/app"
)
print(PATH)
dbfile = open(join(PATH, "df_w_probs"), "rb")
df_w_probs = pickle.load(dbfile)
dbfile.close()

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


def get_headers(
    username: str, password: str, chromedriver_path: str, save_headers: bool = False
) -> dict:
    """
    Pulls the bearer token and user-agent required to make api requests.

    Parameters
    ----------
    username : str
        UD username/email.
    password : str
        UD password.
    chromedriver_path : str
        File path to chromedriver.
    save_headers : bool, optional
        Saves headers to UD_draft_model/scrapers/scrape_site/bearer_token.
        Default is False

    Returns
    -------
    dict
        Required headers.
    """

    headers = pb.read_headers()

    if username not in headers:
        valid_token = False
    else:
        headers = headers[username]
        valid_token = pb.test_headers(headers)

    if valid_token == False:
        url = "https://underdogfantasy.com/lobby"
        headers = pb.pull_required_headers(url, chromedriver_path, username, password)

        if save_headers:
            pb.save_headers(username, headers)

    return headers


def enter_ud_credentials(chromdriver_path: str = CHROMEDRIVER_PATH) -> bool:
    """
    Creates a login form that requires the user to enter their UD
    credentials in order to obtain the necessary API request headers.

    Note that these headers are stored in session state.

    Parameters
    ----------
    chromdriver_path : str, optional
        File path to chromedriver.

    Returns
    -------
    bool
        Indicates if valid credentials were entered.
    """

    valid_credentials = False
    placeholder = st.empty()

    with placeholder.form("Enter"):
        st.markdown("Underdog Credentials")

        email = st.text_input("Email", placeholder="Enter Email")
        password = st.text_input(
            "Password", placeholder="Enter Password", type="password"
        )

        login_button = st.form_submit_button("Enter")

        if login_button:
            try:
                headers = get_headers(email, password, chromdriver_path)
                valid_credentials = True
                st.session_state["headers"] = headers
                placeholder.empty()
            except KeyError:
                pass
            except UnboundLocalError:
                st.write("Invalid Credentials - Please try again")
            except WebDriverException:
                st.write("Unable to check credentials")

    return valid_credentials


# if "valid_credentials" not in st.session_state:
#     st.session_state["valid_credentials"] = False

# if st.session_state["valid_credentials"] == False:
#     st.session_state["valid_credentials"] = enter_ud_credentials()

# if st.session_state["valid_credentials"]:
#     st.dataframe(df_w_probs)

#     st.button("Re-run")

url = "https://underdogfantasy.com/lobby"
chromedriver_path = "/usr/bin/chromedriver"
username = credentials.username
password = credentials.password

headers = get_headers(username, password, chromedriver_path, save_headers=True)


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

    draft_entry_id = df["draft_entry_id"]
    slate_id = df["slate_id"]
    scoring_type_id = df["scoring_type_id"]
    rounds = df["rounds"]

    params = {
        "draft_entry_id": draft_entry_id,
        "slate_id": slate_id,
        "scoring_type_id": scoring_type_id,
        "rounds": rounds,
        "draft_id": draft_id,
    }

    return params


def get_active_drafts(headers: dict) -> pd.DataFrame:
    active_drafts = scrape_site.DraftsActive(headers)
    df_active = active_drafts.create_df_active_drafts()

    return df_active


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

    return df_players


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


df_active = get_active_drafts(headers)
draft_ids = tuple(df_active["id"])

with st.sidebar:
    draft_id = st.selectbox("Select draft", draft_ids)
    st.write(draft_id)
    st.cache_data.clear()

params = get_draft_params(df_active, draft_id)

df_players = get_players(headers, params)
df_entries = get_draft_entries(headers, params)
df_draft = get_draft(headers, params)

st.dataframe(df_draft)


# st.dataframe(df_w_probs)


# print(st.session_state["valid_credentials"])

st.button("Re-run")

# if "key" not in st.session_state:
#     st.session_state["key"] = "value"
#     print("check")

# st.button("Re-run")


# st.dataframe(df_w_probs)


# app(df_w_probs)

# app2()
