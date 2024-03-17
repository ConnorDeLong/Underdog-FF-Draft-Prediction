import streamlit as st
import pandas as pd
import numpy as np

from UD_draft_model.app.save_session_state import SaveSessionState
import UD_draft_model.data_processing.prepare_drafts as prepare_drafts
import UD_draft_model.scrapers.scrape_site.scrape_league_data as scrape_site
from UD_draft_model.modeling.model_version import ModelVersion
import UD_draft_model.data_processing.add_features as add_features


class TeamSummary(SaveSessionState):
    def __init__(
        self,
        df_draft: pd.DataFrame,
        df_players: pd.DataFrame,
        draft_entry_id: str,
        session_state=None,
    ):
        super().__init__(session_state=session_state)

        self.initialize_session_state("df_draft", df_draft)
        self.initialize_session_state("df_players", df_players)
        self.initialize_session_state("draft_entry_id", draft_entry_id)
        self.initialize_session_state("df_pos_bye_week", None)
        self.initialize_session_state("df_team_pos", None)
        self.initialize_session_state("df_pos", None)

        self.df_draft = df_draft
        self.df_players = df_players
        self.draft_entry_id = draft_entry_id

    def pos_bye_week_shell(self) -> pd.DataFrame:
        """
        Creates a position/bye week level dataframe of all possible position/bye week
        combinations.
        """

        df = self.df_players[["position", "bye_week"]].dropna().drop_duplicates()

        return df

    def team_pos_shell(self) -> pd.DataFrame:
        """
        Creates a team/position level dataframe of all possible team/position
        combinations.
        """

        df_team_pos = self.df_players[["position", "abbr"]].dropna().drop_duplicates()
        df_team = df_team_pos[["abbr"]].drop_duplicates()
        df_team["position"] = "All Positions"

        df_team_pos = pd.concat([df_team_pos, df_team])

        return df_team_pos

    def pos_bye_week_agg(self) -> pd.DataFrame:
        """
        Creates a position/bye week level dataframe of all possible position/bye week
        combinations and includes the number of players drafted for each combo.
        """

        df_entry_draft = self.df_draft.loc[
            self.df_draft["draft_entry_id"] == self.draft_entry_id
        ]

        # df_draft doesn't contain any player attributes on it.
        player_vars = ["appearance_id", "position", "bye_week", "abbr"]
        df_entry_draft = pd.merge(
            df_entry_draft, self.df_players[player_vars], how="left", on="appearance_id"
        )

        df_entry_agg = (
            df_entry_draft.groupby(["position", "bye_week"])
            .size()
            .to_frame("num_players")
            .reset_index()
        )

        # Need a position/bye_week shell to capture all possible combinations
        df_pos_weeks = self.pos_bye_week_shell()
        df_pos_weeks = pd.merge(
            df_pos_weeks, df_entry_agg, how="left", on=["position", "bye_week"]
        )
        df_pos_weeks["num_players"] = df_pos_weeks["num_players"].fillna(0)

        return df_pos_weeks

    def team_pos_agg(self) -> pd.DataFrame:
        df_entry_draft = self.df_draft.loc[
            self.df_draft["draft_entry_id"] == self.draft_entry_id
        ]

        # df_draft doesn't contain any player attributes on it.
        player_vars = ["appearance_id", "position", "bye_week", "abbr"]
        df_entry_draft = pd.merge(
            df_entry_draft, self.df_players[player_vars], how="left", on="appearance_id"
        )

        df_pos_team_agg = (
            df_entry_draft.groupby(["position", "abbr"])
            .size()
            .to_frame("num_players")
            .reset_index()
        )
        df_team_agg = (
            df_entry_draft.groupby(["abbr"])
            .size()
            .to_frame("num_players")
            .reset_index()
        )
        df_team_agg["position"] = "All Positions"
        df_all_agg = pd.concat([df_pos_team_agg, df_team_agg])

        df_shell = self.team_pos_shell()
        df_team_pos = pd.merge(
            df_shell, df_all_agg, how="left", on=["position", "abbr"]
        )

        df_team_pos["num_players"] = df_team_pos["num_players"].fillna(0)

        return df_team_pos

    def team_pos_trans_agg(self):
        df = self.team_pos_agg()

        # Need a list of tuples to create an additional level to the column index.
        positions = list(df["position"].unique())
        positions.sort()
        pos_index = [("# of Players Drafted on Same Team", pos) for pos in positions]

        full_index = [("", "abbr")] + pos_index
        new_columns = pd.MultiIndex.from_tuples(full_index)

        df = df.pivot_table(index="abbr", columns="position", values="num_players")
        df.reset_index(inplace=True)

        # df.columns = new_columns

        return df

    def pos_agg(self) -> pd.DataFrame:
        df_entry_draft = self.df_draft.loc[
            self.df_draft["draft_entry_id"] == self.draft_entry_id
        ]

        # df_draft doesn't contain any player attributes on it.
        player_vars = ["appearance_id", "position", "bye_week", "abbr"]
        df_entry_draft = pd.merge(
            df_entry_draft, self.df_players[player_vars], how="left", on="appearance_id"
        )

        df = (
            df_entry_draft.groupby("position")
            .size()
            .to_frame("num_players")
            .reset_index()
        )

        df_all_pos = self.df_players[["position"]].dropna().drop_duplicates()
        df = pd.merge(df_all_pos, df, how="left", on="position")

        df["num_players"] = df["num_players"].fillna(0)

        return df

    def create_team_aggs(self) -> pd.DataFrame:
        self.df_pos_bye_week = self.pos_bye_week_agg()
        print("Position/Bye Week created")
        self.df_team_pos = self.team_pos_trans_agg()
        print("Team/Position created")
        self.df_pos = self.pos_agg()
        print("Position created")


class Draft(SaveSessionState):
    def __init__(
        self, draft_params: dict, headers: dict, model, session_state=None
    ) -> None:
        super().__init__(session_state=session_state)

        self.session_state = session_state

        self.initialize_session_state("draft_params", draft_params)
        self.initialize_session_state("headers", headers)
        self.initialize_session_state("model", model)

        self.initialize_session_state("new_draft_selected", True)
        self.initialize_session_state("team_summary", None)
        self.initialize_session_state("df_draft", None)
        self.initialize_session_state("df_entries", None)
        self.initialize_session_state("df_players", None)
        self.initialize_session_state("df_board", None)
        self.initialize_session_state("df_cur_pick", None)
        self.initialize_session_state("df_final_players", None)

        if self.draft_params == draft_params:
            self.new_draft_selected = False
        else:
            # Need to re-initialize these when a new draft is selected
            self.team_summary = None
            self.df_draft = None
            self.df_entries = None
            self.df_players = None
            self.df_board = None
            self.df_cur_pick = None
            self.df_final_players = None

            self.new_draft_selected = True

        self.draft_params = draft_params
        self.headers = headers
        self.model = model

    @staticmethod
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
        df_players["adp_rank"] = df_players.index + 1

        return df_players

    @staticmethod
    def get_draft_entries(headers: dict, params: dict) -> pd.DataFrame:
        draft_id = [params["draft_id"]]
        draft_detail = scrape_site.DraftsDetail(draft_id, headers)
        df_entries = draft_detail.create_df_draft_entries()

        return df_entries

    @staticmethod
    def get_draft(headers: dict, params: dict) -> pd.DataFrame:
        draft_id = [params["draft_id"]]
        draft_detail = scrape_site.DraftsDetail(draft_id, headers)
        df_draft = draft_detail.create_df_drafts()

        return df_draft

    @staticmethod
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

        # This is needed to show how many picks away the user is from selecting next.
        df["actual_next_pick_number"] = np.where(
            df["number"] < df["user_number"],
            df["user_number"],
            df["user_next_pick_number"],
        )
        df["num_picks_away"] = df["actual_next_pick_number"] - df["number"]

        df.drop(columns=list(rename_vars.values()), inplace=True)

        return df

    @staticmethod
    def add_round_pick_str(
        df: pd.DataFrame, num_teams: int, pick_col: str, out_col: str
    ) -> pd.DataFrame:
        """
        Creates a column which formats the pick_col as Round.Pick (e.g. 5.8).

        Parameters
        ----------
        df : pd.DataFrame
            Dataframe to add column to.
        num_teams : int
            Number of teams in the league.
        pick_col : str
            Column name containing the pick number.
        out_col : str
            Name of the new column.

        Returns
        -------
        pd.DataFrame
            Dataframe passed with an additional column (out_col).
        """
        df["_tmp_round"] = np.where(
            df[pick_col] % num_teams == 0,
            (df[pick_col].fillna(0) / num_teams).astype(int),
            ((df[pick_col].fillna(0) / num_teams) + 1).astype(int),
        )
        df["_tmp_round_pick"] = np.where(
            df[pick_col] % num_teams == 0,
            int(num_teams),
            (df[pick_col].fillna(0) % num_teams).astype(int),
        )

        df[out_col] = (
            df["_tmp_round"].astype(str) + "." + df["_tmp_round_pick"].astype(str)
        )
        df[out_col] = np.where(df[pick_col].isna(), "N/A", df[out_col])
        df.drop(columns=["_tmp_round", "_tmp_round_pick"], inplace=True)

        return df

    def create_draft_board(
        self, df_entries: pd.DataFrame, params: dict
    ) -> pd.DataFrame:
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

        keep_vars = [
            "draft_id",
            "draft_entry_id",
            "user_id",
            "username",
            "round",
            "number",
        ]

        df = df[keep_vars]

        df = prepare_drafts.add_next_pick_number(df, filter_nulls=False)
        df = self.add_user_next_pick_number(df, params["draft_entry_id"])

        df = self.add_round_pick_str(
            df, len(df_entries), "number", "current_round_pick"
        )
        df = self.add_round_pick_str(
            df, len(df_entries), "actual_next_pick_number", "actual_next_round_pick"
        )

        return df

    @staticmethod
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

        merge_vars = ["draft_id", "draft_entry_id", "number"]
        draft_vars = list(df_draft.columns)
        board_vars = list(df_board.columns)

        # Need to remove the
        filtered_board_vars = [
            var for var in board_vars if var not in draft_vars or var in merge_vars
        ]

        df = pd.merge(
            df_board[filtered_board_vars], df_draft, how="left", on=merge_vars
        )

        return df

    @staticmethod
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

    @staticmethod
    def get_avail_players(
        df_players: pd.DataFrame, df_draft: pd.DataFrame
    ) -> pd.DataFrame:
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

    @staticmethod
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

    @staticmethod
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

        try:
            y_pred_prob = model.model.predict_proba(df_features)
            y_pred_prob = y_pred_prob[:, 1]
        except:
            y_pred_prob = np.full(len(df_features), np.nan)

        return y_pred_prob

    @staticmethod
    def merge_prediction(
        df: pd.DataFrame, pred: np.array, out_col: str
    ) -> pd.DataFrame:
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

    def should_update_final_players_df(self) -> bool:
        """
        Returns True if the final players board hasn't been created or
        the object's existing pick to have been selected while the draft
        is active.

        This is used to prevent repeating several unecessary steps against
        the same data when the app is refreshed.
        """
        df_cur_pick = self.get_current_pick(self.df_board)
        return (
            self.df_final_players is None
            or not df_cur_pick.equals(self.df_cur_pick)
            and self.df_draft is not None
        )

    def merge_team_summaries(self, df_w_probs: pd.DataFrame) -> pd.DataFrame:
        """
        Merges team summary data onto the primary df of the app.
        """

        self.team_summary = TeamSummary(
            self.df_draft,
            self.df_players,
            self.draft_params["draft_entry_id"],
            session_state=self.session_state,
        )
        self.team_summary.create_team_aggs()

        df_pos_weeks = self.team_summary.df_pos_bye_week
        df_team_pos = self.team_summary.df_team_pos

        df = pd.merge(df_w_probs, df_pos_weeks, how="left", on=["position", "bye_week"])
        df = pd.merge(df, df_team_pos, how="left", on="abbr")

        int_cols = ["num_players", "All Positions", "QB", "WR", "RB", "TE"]
        df[int_cols] = df[int_cols].astype(pd.Int64Dtype())

        return df

    def rename_final_players_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        rename_cols = {
            "full_name": "Player",
            "position": "Position",
            "abbr": "Team",
            "adp": "ADP",
            "adp_rank_round_pick": "ADP Rank",
            "prob": "NPSP",
            "All Positions": "All Pos",
            "QB": "QB",
            "WR": "WR",
            "RB": "RB",
            "TE": "TE",
            "num_players": "# of Pos/Bye Weeks",
        }

        df = df[list(rename_cols.keys())]
        return df.rename(columns=rename_cols)

    def initialize_draft_attrs(self) -> None:
        """
        Initializes the df_draft, df_entries, and df_board attributes when
        the app is opened or a new draft is selected
        """

        if self.df_board is None or self.new_draft_selected == True:
            self.df_players = self.get_players(self.headers, self.draft_params)
            self.df_entries = self.get_draft_entries(self.headers, self.draft_params)
            self.df_board = self.create_draft_board(self.df_entries, self.draft_params)

    def update_draft_attrs(self) -> None:
        """
        Updates draft attrs.
        """

        # get_draft throws an IndexError until the first pick is selected.
        try:
            self.df_draft = self.get_draft(self.headers, self.draft_params)
            self.df_board = self.update_board(self.df_board, self.df_draft)

            # This only gets updated once here to compare the current state's
            # value to the newly updated board to determine if the model
            # needs run again.
            if self.df_cur_pick is None:
                self.df_cur_pick = self.get_current_pick(self.df_board)
            else:
                pass

        except IndexError:
            pass

    def create_df_final_players(self) -> pd.DataFrame:
        """
        Creates the final remaining players dataframe.
        """

        # Check if final players DataFrame needs updating
        if not self.should_update_final_players_df():
            return

        # Update the current pick DataFrame
        self.df_cur_pick = self.get_current_pick(self.df_board)

        # Retrieve available players
        df_available_players = self.get_avail_players(self.df_players, self.df_draft)

        # Add available players to current pick DataFrame
        df_with_players = self.add_avail_players(self.df_cur_pick, df_available_players)

        # Add features to the DataFrame
        df_with_features = add_features.add_features(df_with_players)

        # Create predictions
        probabilities = self.create_predictions(df_with_features, self.model)

        # Merge predictions to the DataFrame
        df_with_probs = self.merge_prediction(df_with_features, probabilities, "prob")

        # Update the full_name column and team summary
        df_with_probs["full_name"] = (
            df_with_probs["first_name"] + " " + df_with_probs["last_name"]
        )

        # Add team summaries, round pick string, and rename columns
        df_with_probs = self.merge_team_summaries(df_with_probs)
        df_with_probs = self.add_round_pick_str(
            df_with_probs, len(self.df_entries), "adp_rank", "adp_rank_round_pick"
        )
        self.df_final_players = self.rename_final_players_columns(df_with_probs)
