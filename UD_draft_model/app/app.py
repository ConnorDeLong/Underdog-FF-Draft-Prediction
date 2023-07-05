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


def display_picks_by_pos(
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


def display_all_picks_by_pos(df_pos: pd.DataFrame):

    num_qb = int(df_pos.loc[df_pos["position"] == "QB"]["num_players"])
    num_rb = int(df_pos.loc[df_pos["position"] == "RB"]["num_players"])
    num_wr = int(df_pos.loc[df_pos["position"] == "WR"]["num_players"])
    num_te = int(df_pos.loc[df_pos["position"] == "TE"]["num_players"])

    display_picks_by_pos(c2_c1, "QB", num_qb, "rgb(150, 71, 184)")
    display_picks_by_pos(c2_c2, "RB", num_rb, "rgb(21, 153, 126)")
    display_picks_by_pos(c2_c3, "WR", num_wr, "rgb(230, 126, 34)")
    display_picks_by_pos(c2_c4, "TE", num_te, "rgb(41, 128, 185)")


def create_team_pos_chart(df_team_pos: pd.DataFrame):
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

    # fig.add_trace(go.Scatter(
    #     y=df['team'],
    #     x=df["Total"],
    #     text=df["Total"],
    #     mode='text',
    #     textposition='middle right',
    #     showlegend=False
    # ))

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


def set_page_container_style(
    max_width: int = 1100,
    max_width_100_percent: bool = False,
    padding_top: int = 1,
    padding_right: int = 10,
    padding_left: int = 1,
    padding_bottom: int = 10,
    color: str = "white",
    background_color: str = "black",
):
    if max_width_100_percent:
        max_width_str = f"max-width: 100%;"
    else:
        max_width_str = f"max-width: {max_width}px;"
    st.markdown(
        f"""
            <style>
                .reportview-container .sidebar-content {{
                    padding-top: {padding_top}rem;
                }}
                .reportview-container .main .block-container {{
                    {max_width_str}
                    padding-top: {padding_top}rem;
                    padding-right: {padding_right}rem;
                    padding-left: {padding_left}rem;
                    padding-bottom: {padding_bottom}rem;
                }}
                .reportview-container .main {{
                    color: {color};
                    background-color: {background_color};
                }}
            </style>
            """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    st.set_page_config(layout="wide")

    CHROMEDRIVER_PATH = "/usr/bin/chromedriver"
    MODEL_PATH = "../modeling/models"
    MODEL = "LogisticRegression_v01_v001"

    model = load_model(join(MODEL_PATH, MODEL))

    username = _credentials.username
    password = _credentials.password
    headers = get_headers(username, password, CHROMEDRIVER_PATH, save_headers=True)
    valid_credentials = True

    # credentials = Credentials(CHROMEDRIVER_PATH, session_state=st.session_state)
    # credentials.enter_ud_credentials()

    # headers = credentials.headers
    # valid_credentials = credentials.valid_credentials
    st.markdown(
        "<h1 style='text-align: center;'>Underdog Fantasy Football Draft Tool</h1>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([3.5, 1])

    if valid_credentials:
        df_active = get_active_drafts(headers)

        if df_active is None:
            draft_ids = []
        else:
            draft_ids = tuple(df_active["id"])

        draft_id = select_draft(draft_ids, headers)

        if df_active is not None:
            params = get_draft_params(df_active, draft_id)
            draft = Draft(params, headers, model, session_state=st.session_state)

            if params["draft_status"] == "drafting":
                draft.initialize_draft_attrs()
                draft.update_draft_attrs()
                draft.create_df_final_players()

                if draft.df_final_players is not None:
                    with c1:
                        container = st.container()

                        with container:
                            c1_0, c1_1 = st.columns(2)
                            pos_selected = c1_0.selectbox(
                                "Position Filter",
                                ("All Positions", "QB", "WR", "RB", "TE"),
                            )
                            stack_selected = c1_1.selectbox(
                                "Stack Filter", ("Any Player", "Stack Players")
                            )

                        df = draft.df_final_players

                        if pos_selected == "All Positions":
                            pos_filter = df.index >= 0
                        else:
                            pos_filter = df["Position"] == pos_selected
                        if stack_selected == "Any Player":
                            stack_filter = df.index >= 0
                        else:
                            stack_filter = df["All Positions"] > 0

                        df = df.loc[(pos_filter & stack_filter)]

                        st.dataframe(df)
                        st.dataframe(draft.df_cur_pick)

                    with c2:
                        container = st.container()

                        df_team_pos = draft.team_summary.df_team_pos
                        df_team_pos = df_team_pos.loc[
                            df_team_pos["abbr"].isin(
                                df_team_pos.loc[df_team_pos["All Positions"] > 0][
                                    "abbr"
                                ]
                            )
                        ]

                        with container:
                            c2_0, c2_c1, c2_c2, c2_c3, c2_c4, c2_999 = st.columns(
                                [1, 1, 1, 1, 1, 1]
                            )
                            display_all_picks_by_pos(draft.team_summary.df_pos)

                        if len(df_team_pos) > 0:
                            fig = create_team_pos_chart(df_team_pos)
                            st.plotly_chart(fig, use_container_width=True)
            else:
                with c1:
                    st.write("Draft has not been filled")

        with c1:
            st.button("Refresh player board")

    # from streamlit_autorefresh import st_autorefresh
    # count = st_autorefresh(interval=1000, limit=100, key="fizzbuzzcounter")
