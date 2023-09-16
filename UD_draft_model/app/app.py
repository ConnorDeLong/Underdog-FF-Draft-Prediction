# Does not properly re-load when the first pick is made. Need to refresh
# browser or select new draft.

from os.path import join
import pickle

import pandas as pd
import numpy as np
import streamlit as st
from streamlit.delta_generator import DeltaGenerator
import plotly.graph_objects as go

from UD_draft_model.app.draft import Draft, TeamSummary
from UD_draft_model.app.get_credentials import Credentials, get_headers
import UD_draft_model.scrapers.scrape_site.scrape_league_data as scrape_site
from UD_draft_model.modeling.model_version import ModelVersion

# REMOVE LATER
import UD_draft_model.credentials.credentials as _credentials


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
    clear_cache()
    return get_active_drafts(headers)


def select_draft(draft_ids: list, headers: dict) -> str:
    with st.sidebar:
        draft_id = st.selectbox("Select draft", draft_ids, on_change=clear_cache)
        st.button("Refresh", on_click=refresh_drafts, args=[headers])

    if len(draft_ids) == 0:
        st.write("No active drafts to select from")

    return draft_id


def clear_cache() -> None:
    st.cache_data.clear()


def initialize_draft(headers: dict, valid_credentials: bool) -> tuple:
    """
    Ensures that credentials have passed, a selected draft is active,
    and it is currently in the draft process.

    Parameters
    ----------
    valid_credentials : bool
        Determines whether or not the user passed valid credentials
        required to scrape a draft.

    Returns
    -------
    tuple
        First element is true if credentials are passed and there's an
        active draft. Second element is an instance of a Draft obejct
        whose primary attributes are updated to reflect the draft in
        progress.
    """
    if not valid_credentials:
        return False, None

    df_active = get_active_drafts(headers)

    if df_active is None:
        return False, None

    draft_ids = tuple(df_active["id"])
    draft_id = select_draft(draft_ids, headers)
    params = get_draft_params(df_active, draft_id)
    draft = Draft(params, headers, model, session_state=st.session_state)

    # Check if we're currently drafting and initialize and update draft attributes
    if params["draft_status"] == "drafting":
        draft.initialize_draft_attrs()
        print("draft initialized")
        draft.update_draft_attrs()
        print("draft attrs updated")
        draft.create_df_final_players()
        print("players df created")
        return True, draft

    return False, draft


def filter_avail_players(cols: list, draft: Draft) -> pd.DataFrame:
    """
    Creates drop-downs in the app and filters the df accordingly.
    """
    teams = list(draft.df_players["abbr"].drop_duplicates().sort_values())
    teams.insert(0, "All Teams")
    teams = tuple(teams)

    df = draft.df_final_players

    # Create the drop-downs.
    pos_selected = cols[0].selectbox(
        "Position Filter",
        ("All Positions", "QB", "WR", "RB", "TE"),
    )
    stack_selected = cols[1].selectbox("Stack Filter", ("Any Player", "Stack Players"))
    team_selected = cols[2].selectbox("Teams", teams)

    # Set defaults.
    pos_filter = df.index >= 0
    stack_filter = df.index >= 0
    team_filter = df.index >= 0

    # Filter on selected values.
    if pos_selected != "All Positions":
        pos_filter = df["Position"] == pos_selected
    if stack_selected != "Any Player":
        stack_filter = df["All Pos"] > 0
    if team_selected != "All Teams":
        team_filter = df["Team"] == team_selected

    df = df.loc[(pos_filter & stack_filter & team_filter)]

    return df


def display_current_next_pick(df_cur_pick: pd.DataFrame, column) -> None:
    """ """
    current_drafter = draft.df_cur_pick["username"].iloc[0]
    current_pick = draft.df_cur_pick["current_round_pick"].iloc[0]
    user_next_pick = draft.df_cur_pick["actual_next_round_pick"].iloc[0]

    column.markdown(
        f"""
        <div style="display: flex; flex-direction: column; align-items: center; width: 200px;">
            <p style="margin: 0;"><strong>{current_drafter}<strong/></p>
            <div style="display: flex; justify-content: space-between; align-items: center; width: 200px;">
                <div style="text-align: center;">
                    <p style="text-decoration: underline; margin-bottom: 1px;">Current Pick</p>
                    <p style="font-size: 1em; margin: 0;">{current_pick}</p>
                </div>
                <div style="text-align: center;">
                    <p style="text-decoration: underline; margin-bottom: 1px;">User Next Pick</p>
                    <p style="font-size: 1em; margin: 0;">{user_next_pick}</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _display_picks_by_pos(
    column: DeltaGenerator, position: str, num_picks: int, color: str
) -> str:
    top_md = f"""
        <div
            style='text-align: center; color: {color}; font-weight: bold'
        >{position}
        </div>
    """

    bottom_md = f"""
        <div
            style='text-align: center'
        >{num_picks}
        </div>
    """

    column.markdown(top_md, unsafe_allow_html=True)
    column.markdown(bottom_md, unsafe_allow_html=True)

    return None


def display_all_picks_by_pos(cols: list, df_pos: pd.DataFrame):
    """
    Displays the number of players drafted by position.
    """
    num_qb = int(df_pos.loc[df_pos["position"] == "QB"]["num_players"])
    num_rb = int(df_pos.loc[df_pos["position"] == "RB"]["num_players"])
    num_wr = int(df_pos.loc[df_pos["position"] == "WR"]["num_players"])
    num_te = int(df_pos.loc[df_pos["position"] == "TE"]["num_players"])

    _display_picks_by_pos(cols[0], "QB", num_qb, "rgb(150, 71, 184)")
    _display_picks_by_pos(cols[1], "RB", num_rb, "rgb(21, 153, 126)")
    _display_picks_by_pos(cols[2], "WR", num_wr, "rgb(230, 126, 34)")
    _display_picks_by_pos(cols[3], "TE", num_te, "rgb(41, 128, 185)")


def create_team_pos_chart(df_team_pos: pd.DataFrame):
    """
    Creates a bar chart showing the number of players drafted
    by Team/Position.
    """
    df = df_team_pos.copy()
    df["team"] = df["abbr"]

    # Calculate the total number of players drafted (sum of the four columns)
    df["Total"] = df[["QB", "RB", "WR", "TE"]].sum(axis=1)

    df.sort_values(by="Total", inplace=True)

    # Define the categories and their corresponding colors for the stacked bars
    categories = {
        "QB": "rgb(150, 71, 184)",
        "RB": "rgb(21, 153, 126)",
        "WR": "rgb(230, 126, 34)",
        "TE": "rgb(41, 128, 185)",
    }

    # Create a stacked horizontal bar chart using Plotly
    fig = go.Figure()

    for category, color in categories.items():
        fig.add_trace(
            go.Bar(
                name=category,
                y=df["team"],
                x=df[category],
                orientation="h",
                marker=dict(color=color),
                showlegend=False,
                text=df[category],
                textposition="inside",
                insidetextanchor="middle",
            )
        )

    # Set the chart title and axis labels
    fig.update_layout(
        title="",
        xaxis_title="",
        yaxis_title="",
        margin=dict(t=0, b=0, l=0, r=0),
        xaxis=dict(tickmode="linear", tick0=0, dtick=1),
        yaxis_tickfont=dict(color="black"),
        xaxis_tickfont=dict(color="black"),
    )

    # Stack the bars on top of each other
    fig.update_layout(barmode="stack")

    return fig


def display_team_pos_chart(col, draft: Draft) -> None:
    df_team_pos = draft.team_summary.df_team_pos
    df_team_pos = df_team_pos.loc[
        df_team_pos["abbr"].isin(
            df_team_pos.loc[df_team_pos["All Positions"] > 0]["abbr"]
        )
    ]
    if len(df_team_pos) > 0:
        fig = create_team_pos_chart(df_team_pos)
        col.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    st.set_page_config(layout="wide")

    CHROMEDRIVER_PATH = "/usr/bin/chromedriver"
    MODEL_PATH = "../modeling/models"
    MODEL = "LogisticRegression_v01_v001"

    model = load_model(join(MODEL_PATH, MODEL))

    st.markdown(
        "<h1 style='text-align: center;'>Underdog Fantasy Football Draft Tool</h1>",
        unsafe_allow_html=True,
    )

    # username = _credentials.username
    # password = _credentials.password
    # headers = get_headers(username, password, CHROMEDRIVER_PATH, save_headers=True)
    # valid_credentials = True

    credentials = Credentials(CHROMEDRIVER_PATH, session_state=st.session_state)
    credentials.enter_ud_credentials()
    headers = credentials.headers
    valid_credentials = credentials.valid_credentials

    # Columns to store the df of remaining players and a summary of drafted players.
    c1, c2 = st.columns([3.5, 1])

    # Container and columns for filtering remaining players df.
    c1_0 = c1.container()
    c1_0_0, c1_0_1, c1_0_2, c1_0_3 = c1_0.columns(4)

    # Container and columns for the summary.
    c2_0 = c2.container()
    c2_0_lens = [1.5, 1, 1, 1, 1, 1]
    c2_0_0, c2_0_1, c2_0_2, c2_0_3, c2_0_4, c2_0_5 = c2_0.columns(c2_0_lens)

    # Update app as the draft progresses.
    try:
        draft_initialized, draft = initialize_draft(headers, valid_credentials)
        print(draft_initialized)

        if not draft_initialized or draft.df_final_players is None:
            raise Exception("Draft not initialized or players dataframe is None")

        df = filter_avail_players([c1_0_0, c1_0_1, c1_0_2], draft)
        display_current_next_pick(draft.df_cur_pick, c1_0_3)
        c1.dataframe(df)

        cols = [c2_0_1, c2_0_2, c2_0_3, c2_0_4, c2_0_5]
        display_all_picks_by_pos(cols, draft.team_summary.df_pos)

        display_team_pos_chart(c2, draft)

    except Exception as e:
        # For better debugging, you can also log or print the exception message.
        print(str(e))
        c1.write("Draft has not been filled")

    c1.button("Refresh player board")
