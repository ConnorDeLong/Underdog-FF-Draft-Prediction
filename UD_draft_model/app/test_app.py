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

        display_picks_by_pos(c2_c1, "QB", 1, "violet")
        display_picks_by_pos(c2_c2, "RB", 1, "green")
        display_picks_by_pos(c2_c3, "WR", 1, "orange")
        display_picks_by_pos(c2_c4, "TE", 1, "blue")


class Counter(SaveSessionState):
    def __init__(self, session_state=None):
        super().__init__(session_state=session_state)

        self.initialize_session_state("count", 0)
        self.initialize_session_state("title", "Calculator")
        self.col1, self.col2 = st.columns(2)

    def add(self):
        st.session_state.Counter_count += 1

    def add_actual(self):
        self.count += 1
        # print(type(self.count))

    def subtract(self):
        st.session_state.Counter_count -= 1

    def tester(self):
        if "tester" not in st.session_state:
            st.session_state.Counter_tester = "Tester"
        else:
            st.session_state.Counter_tester = "Already tested"
        with self.col2:
            st.write(f"Hello from the {st.session_state.Counter_tester}!")

    def window(self):

        with self.col1:
            st.button("Increment", on_click=self.add)
            st.button("Add Object Val", on_click=self.add_actual)
            st.button("Subtract", on_click=self.subtract)
            st.write(f"Count = {st.session_state.Counter_count}")
            st.write(self.count)
        with self.col2:
            st.button("test me", on_click=self.tester)


# class Counter:
#     def __init__(self):
#         if "count" not in st.session_state:
#             st.session_state.count = 0
#         # st.session_state.count = 0
#         if "title" not in st.session_state:
#             st.session_state.title = "Calculator"
#         self.col1, self.col2 = st.columns(2)

#         self.count = st.session_state.count

#     def add(self):
#         st.session_state.count += 1

#     def add_actual(self):
#         self.count += 1
#         self.check = st.session_state
#         print(print(type(st.session_state)))
#         # print(type(self.count))

#     def subtract(self):
#         st.session_state.count -= 1

#     def tester(self):
#         if "tester" not in st.session_state:
#             st.session_state.tester = "Tester"
#         else:
#             st.session_state.tester = "Already tested"
#         with self.col2:
#             st.write(f"Hello from the {st.session_state.tester}!")

#     def window(self):

#         with self.col1:
#             st.button("Increment", on_click=self.add)
#             st.button("Add Object Val", on_click=self.add_actual)
#             st.button("Subtract", on_click=self.subtract)
#             st.write(f"Count = {st.session_state.count}")
#             st.write(self.count)
#         with self.col2:
#             st.button("test me", on_click=self.tester)


if __name__ == "__main__":
    ct = Counter(session_state=st.session_state)
    ct.window()
