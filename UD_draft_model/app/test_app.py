import streamlit as st
from streamlit.delta_generator import DeltaGenerator
from UD_draft_model.app.save_session_state import SaveSessionState

# tab1, tab2 = st.tabs(["t1", "t2"])

# with tab1:
#     st.write("tab 1")

# with tab2:
#     st.write("tab 2")

# exp = st.expander("open to see more content")
# exp.write("this is more content")


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


var = "test this"

c1, c2 = st.columns(2)

st.write(type(c1))

c1.write("this is the left column")

with c2:
    container = st.container()

    with container:
        c2_0, c2_c1, c2_c2, c2_c3, c2_c4, c2_999 = st.columns([4, 1, 1, 1, 1, 4])

        display_picks_by_pos(c2_c1, "QB", 1, "rgb(150, 71, 184)")
        display_picks_by_pos(c2_c2, "RB", 1, "green")
        display_picks_by_pos(c2_c3, "WR", 1, "orange")
        display_picks_by_pos(c2_c4, "TE", 1, "blue")
