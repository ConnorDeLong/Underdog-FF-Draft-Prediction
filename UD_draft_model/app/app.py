import streamlit as st
import pickle
from os.path import join
import datetime

import pandas as pd

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


def app(df: pd.DataFrame):
    st.title("My Dataframe App")
    # st.write(df)

    # left_column, middle_column, right_column = st.columns([1, 2, 1])
    # with left_column:
    #     st.write(df)
    # with middle_column:
    #     st.write(df)
    # with right_column:
    #     st.write("")

    # st.markdown(
    #     """
    # <style>
    # .dataframe {
    #     position: absolute;
    #     top: 300px;
    #     left: 50px;
    # }
    # </style>
    # """,
    #     unsafe_allow_html=True,
    # )
    # st.dataframe(df)

    st.dataframe(df, width=500).style.set_table_styles(
        [
            {
                "selector": "th",
                "props": [
                    ("text-align", "center"),
                    ("white-space", "pre-wrap"),
                    ("word-wrap", "break-word"),
                ],
            }
        ]
    )


def app2():
    def get_user_name():
        return "John"

    with st.echo():
        # Everything inside this block will be both printed to the screen
        # and executed.

        def get_punctuation():
            return "!!!"

        greeting = "Hi there, "
        value = get_user_name()
        punctuation = get_punctuation()

        st.write(greeting, value, punctuation)

    # And now we're back to _not_ printing to the screen
    foo = "bar"
    st.write("Done!")


def selection_page():
    st.title("Selection Page")
    st.write("Please select an item from the list below:")
    selection = st.selectbox("", ["Item 1", "Item 2", "Item 3"])
    if selection == "Item 1":
        item1_page()
    elif selection == "Item 2":
        item2_page()
    elif selection == "Item 3":
        item3_page()


# Define the pages for each item in the Streamlit app
def item1_page():
    st.title("Item 1 Page")
    st.write("This is Item 1 Page.")


def item2_page():
    st.title("Item 2 Page")
    st.write("This is Item 2 Page.")


def item3_page():
    st.title("Item 3 Page")
    st.write("This is Item 3 Page.")


# Run the Streamlit app
selection_page()


# app(df_w_probs)

# app2()
