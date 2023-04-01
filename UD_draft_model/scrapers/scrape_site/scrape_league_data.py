import requests
import pandas as pd
import time


class BaseData:
    def __init__(self, headers: dict, clear_json_attrs: bool = True):
        """
        Provides basic functionality to scrape the UD API and store the
        data into dfs.

        Parameters
        ----------
        headers : dict
            Headers to be passed to the API request.
            This MUST include a 'user-agent' key which can be scraped from
            the pull_bearer_token module. 'authorization' header (i.e. the
            bearer token) is not always required.
        clear_json_attrs : bool, optional
            Clears the json attrs created from scraping the API, by default True.
        """

        self._clear_json_attrs = clear_json_attrs

        self.auth_header = headers.copy()
        self.auth_header["accept"] = "application/json"

        # user-agent and/or accept headers sometimes required
        # self.auth_header = {
        #     "accept": "application/json",
        #     "user-agent": "Mozilla/5.0 (X11; Linux x86_64) \
        #                         AppleWebKit/537.36 (KHTML, like Gecko) \
        #                         Chrome/99.0.4844.51 Safari/537.36",
        # }

        self._player_scores_wk_1_id = 78
        self._player_scores_wk_last_id = 78 + 17

    def build_all_dfs(self, sleep_time: int = 0):
        """
        Overwrites every 'df_' attribute with a df that is created by running the
        'create_' method that matches it. This serves as the primary method
        for building the dfs associated with the class
        """

        attrs = [attr for attr in dir(self) if attr.startswith("df_")]
        for attr in attrs:
            method_name = "create_" + attr
            self.__dict__[attr] = getattr(self, method_name)()
            try:
                self.__dict__[attr] = getattr(self, method_name)()
            except:
                print(getattr(self, method_name), "failed to run")

            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                pass

        if self._clear_json_attrs == True:
            self.clear_json_attrs()

    def clear_json_attrs(self):
        """
        Clears all the atttributes that hold the json data pulled from the API.
        By default, this is executed when the build_all_dfs method is run
        """

        attrs = [attr for attr in dir(self) if attr.startswith("json")]
        for attr in attrs:
            self.__dict__[attr] = {}

    def read_in_site_data(self, url, headers: dict = None) -> dict:
        """Pulls in the raw data from the API and returns it as a dict"""

        if headers is None:
            headers = {}

        response = requests.get(url, headers=headers)

        site_data = response.json()

        return site_data

    def create_scraped_data_df(self, scraped_data: list) -> pd.DataFrame:
        """
        Converts a list of dictionaries into a df where the keys of the dicts are
        used for the columns and the values are placed in the rows.
        NOTE: this assumes the keys in all dicts are the same.
        """

        # Get the dicionary keys to identify the columns of the list for each output dict key
        output_data_cols = []
        for output_data_col in scraped_data[0].keys():
            output_data_cols.append(output_data_col)

        final_data_dict = {"columns": output_data_cols}
        for data_dict_id, data in enumerate(scraped_data):
            all_data_elements = []
            for output_data_col in output_data_cols:
                try:
                    data_element = data[output_data_col]
                except:
                    # Note: This should probably be conditional on the data type,
                    # but just using N/A for now.
                    data_element = "N/A"

                all_data_elements.append(data_element)

            final_data_dict[data_dict_id] = all_data_elements

        final_data_df = self._convert_data_dict_to_df(final_data_dict)

        return final_data_df

    def _convert_data_dict_to_df(self, scraped_data_dict: dict) -> pd.DataFrame:
        """
        Converts the dict from the create_scraped_data_dict function to a df
        NOTE: The input dict takes the following form:
        {'columns': [<column names>], 1: [<column values>], 2: [<column_values>], ...}
        """

        columns = scraped_data_dict["columns"]

        data_keys = list(scraped_data_dict.keys())[1:]

        data_for_df = []
        for data_key in data_keys:
            data = scraped_data_dict[data_key]

            data_for_df.append(data)

        final_df = pd.DataFrame(data=data_for_df, columns=columns)

        return final_df

    def _create_week_id_mapping(self) -> pd.DataFrame:
        """Creates a map between the APIs Week ID and the actual Week number"""

        wk_numbers = []
        wk_ids = []
        for wk_number, wk_id in enumerate(
            range(self._player_scores_wk_1_id, self._player_scores_wk_last_id + 1)
        ):
            wk_numbers.append(wk_number + 1)
            wk_ids.append(wk_id)

        mapping = {"week_number": wk_numbers, "week_id": wk_ids}
        df_mapping = pd.DataFrame(data=mapping)

        return df_mapping


class DraftsDetail(BaseData):
    """Compiles all major league specific data into dataframes"""

    def __init__(self, league_ids: list, headers: str, clear_json_attrs: bool = True):
        super().__init__(headers, clear_json_attrs=clear_json_attrs)

        self.league_ids = league_ids

        self.url_drafts = {}
        self.url_weekly_scores = {}
        for league_id in league_ids:
            url_draft = "https://api.underdogfantasy.com/v2/drafts/" + league_id
            url_weekly_scores = (
                "https://api.underdogfantasy.com/v1/drafts/"
                + league_id
                + "/weekly_scores"
            )

            self.url_drafts[league_id] = url_draft
            self.url_weekly_scores[league_id] = url_weekly_scores

        self.json_drafts = {}
        self.json_weekly_scores = {}

        self.df_drafts = pd.DataFrame()
        self.df_draft_entries = pd.DataFrame()
        self.df_weekly_scores = pd.DataFrame()

    def create_df_drafts(self) -> pd.DataFrame:
        dfs = []
        for league_id in self.league_ids:
            df = self._create_df_draft_ind_league(league_id)
            dfs.append(df)

        final_df = pd.concat(dfs)

        return final_df

    def create_df_draft_entries(self) -> pd.DataFrame:
        dfs = []
        for league_id in self.league_ids:
            df = self._create_df_draft_entries_ind_league(league_id)
            dfs.append(df)

        final_df = pd.concat(dfs)

        return final_df

    def create_df_weekly_scores(self) -> pd.DataFrame:
        dfs = []
        for league_id in self.league_ids:
            df = self._create_df_weekly_scores_ind_league(league_id)
            dfs.append(df)

        final_df = pd.concat(dfs)
        final_df.reset_index(inplace=True)

        week_mapping = self._create_week_id_mapping()
        final_df = pd.merge(final_df, week_mapping, on="week_id")

        return final_df

    def _create_df_draft_ind_league(self, league_id: str) -> pd.DataFrame:
        self.json_drafts[league_id] = self.read_in_site_data(
            self.url_drafts[league_id], headers=self.auth_header
        )
        scraped_data = self.json_drafts[league_id]["draft"]["picks"]

        initial_scraped_df = self.create_scraped_data_df(scraped_data)
        initial_scraped_df.drop(["projection_average"], axis=1, inplace=True)

        initial_scraped_df["draft_id"] = league_id

        return initial_scraped_df

    def _create_df_draft_entries_ind_league(self, league_id: str) -> pd.DataFrame:
        """
        Creates a df of all users in the draft, sorted by pick order.
        """

        json = self.read_in_site_data(self.url_drafts[league_id], self.auth_header)

        df_entries = self.create_scraped_data_df(json["draft"]["draft_entries"])
        df_users = self.create_scraped_data_df(json["draft"]["users"])

        df_users.rename(columns={"id": "user_id"}, inplace=True)
        df_users = df_users[["user_id", "username"]]

        df = pd.merge(df_entries, df_users, how="left", on="user_id")
        df = df.sort_values(by="pick_order").reset_index(drop=True)

        df["draft_id"] = league_id

        return df

    def _create_df_weekly_scores_ind_league(self, league_id: str) -> pd.DataFrame:
        self.json_weekly_scores[league_id] = self.read_in_site_data(
            self.url_weekly_scores[league_id], headers=self.auth_header
        )
        scraped_data = self.json_weekly_scores[league_id]["draft_weekly_scores"]

        initial_scraped_df = self.create_scraped_data_df(scraped_data)

        weekly_scores = self._pull_out_weekly_scores(initial_scraped_df)

        initial_scraped_df.drop(["week", "draft_entries_points"], axis=1, inplace=True)

        final_scraped_df = pd.merge(
            left=weekly_scores, right=initial_scraped_df, on="id", how="left"
        )
        final_scraped_df.drop(["id"], axis=1, inplace=True)

        return final_scraped_df

    def _pull_out_weekly_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Each row represents one week where each teams score is contained
        within a dicitonary for that week. This pulls those scores out and
        puts them in a Team/Week level df
        """

        df = df.copy()

        all_weekly_scores = []
        for index, row in df.iterrows():
            row_id = row["id"]
            week_id = row["week"]["id"]
            status = row["week"]["status"]
            points_dict = row["draft_entries_points"]

            for user_id, points in points_dict.items():
                weekly_scores = [row_id, week_id, status, user_id, points]

                all_weekly_scores.append(weekly_scores)

        columns = ["id", "week_id", "status", "user_id", "total_points"]
        df = pd.DataFrame(data=all_weekly_scores, columns=columns)

        return df


class DraftsActive(BaseData):

    url = "https://api.underdogfantasy.com/v3/user/active_drafts"

    def __init__(self, headers: str, clear_json_attrs: bool = True):
        super().__init__(headers, clear_json_attrs=clear_json_attrs)

        self.json = {}
        self.df_active_drafts = None

    def create_df_active_drafts(self) -> pd.DataFrame:
        """
        Creates a draft level df of all active drafts.
        """

        self.json = self.read_in_site_data(DraftsActive.url, headers=self.auth_header)

        try:
            df = self.create_scraped_data_df(self.json["drafts"])
            df = self._add_contest_refs(df)
        except IndexError:
            print(f"No data found in {DraftsActive.url} - no df will be returned")
            df = None

        if self.clear_json_attrs:
            self.json = {}

        return df

    def _add_contest_refs(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Scoring type required to get the rankings (appearances) used
        for the draft and rounds needed to build a draft shell.
        """

        contest_refs = ContestRefs(self.auth_header)
        df_styles = contest_refs.create_df_contest_styles()
        df_styles = df_styles[["id", "scoring_type_id", "rounds"]]
        df_styles.rename(columns={"id": "contest_style_id"}, inplace=True)

        df = pd.merge(df, df_styles, how="left", on="contest_style_id")

        return df


class Drafts(BaseData):
    """
    Compiles all completed or settled draft level data for a slate.
    """

    def __init__(self, headers: str, slate, clear_json_attrs: bool = True):
        """
        Note: This requires the user-agent header - Should be able to grab this
        with the bearer token, but hard coding for now
        """

        super().__init__(headers, clear_json_attrs=clear_json_attrs)

        self.slate = slate

        url_suffix = f"/{self.slate.slate_type}_drafts"
        self.url_base_leagues = (
            "https://api.underdogfantasy.com/v2/user/slates/"
            + self.slate.id
            + url_suffix
        )
        self.url_tourney_league_ids = (
            "https://api.underdogfantasy.com/v1/user/slates/"
            + self.slate.id
            + "/tournament_rounds"
        )

        self.json_leagues = {}
        self.df_all_leagues = pd.DataFrame()

    def create_df_all_leagues(self, league_urls: list = None) -> pd.DataFrame:
        if league_urls is None:
            league_urls = self.get_league_urls()

        leagues = []
        for i, league_url in enumerate(league_urls):
            df = self._create_df_leagues(league_url, "league_" + str(i + 1))
            leagues.append(df)

        df_all_leagues = pd.concat(leagues)
        df_all_leagues.reset_index(inplace=True)
        df_all_leagues.drop(columns=["index"], inplace=True)

        return df_all_leagues

    def get_league_urls(self) -> list:
        """
        Creates a list of all urls which store draft level data for the slate.
        """

        try:
            tourney_league_urls = self._create_tourney_league_urls()
        except IndexError:
            tourney_league_urls = []

        if self.slate.draft_count > 0:
            base_league_url = [self.url_base_leagues]
        else:
            base_league_url = []

        urls = base_league_url + tourney_league_urls

        return urls

    def _create_df_leagues(self, url_base: str, json_leagues_key: str) -> pd.DataFrame:
        self.json_leagues[json_leagues_key] = self._create_json_leagues(url_base)
        scraped_data = self.json_leagues[json_leagues_key]

        leagues_df_list = []
        for leagues_page in scraped_data.values():
            leagues_page_df = self.create_scraped_data_df(leagues_page["drafts"])
            leagues_df_list.append(leagues_page_df)

        leagues_df = pd.concat(leagues_df_list)

        return leagues_df

    def _create_json_leagues(self, url_base: str) -> dict:
        """
        Loops through all the different pages that contain the league level data
        and stores each as an entry in a dict
        """

        url_exists = True
        i = 1
        leagues_json_dict = {}
        while url_exists:
            if i == 1:
                url = url_base
            else:
                url = url_base + "?page=" + str(i)

            leagues = self.read_in_site_data(url, headers=self.auth_header)

            if len(leagues["drafts"]) > 0:
                leagues_json_dict["page_" + str(i)] = leagues
            else:
                url_exists = False

            i += 1

        return leagues_json_dict

    def _create_df_tourney_league_ids(self) -> pd.DataFrame:
        """
        Tournament leagues (i.e. Puppy 1, Puppy 2, etc.) require the ID of the
        tourney in order to find all entries in it - This creates of all tourney
        IDs that has at least one entry
        """

        json_tourney_league_ids = self.read_in_site_data(
            self.url_tourney_league_ids, headers=self.auth_header
        )
        scraped_data = json_tourney_league_ids["tournament_rounds"]

        initial_scraped_df = self.create_scraped_data_df(scraped_data)

        # Pulling out the 'id' from the 'tournament' dict in case this is whats needed
        tournament_col = initial_scraped_df["tournament"].to_list()
        tournament_df = self.create_scraped_data_df(tournament_col)
        tournament_df.rename(columns={"id": "tournament_id"}, inplace=True)
        tournament_df = tournament_df["tournament_id"]

        initial_scraped_df.drop(["tournament"], axis=1, inplace=True)
        final_df = initial_scraped_df.join(tournament_df)

        return final_df

    def _create_tourney_league_urls(self) -> list:
        """
        Creates a list of all the URLs that contain entries
        """

        tourney_league_ids = list(self._create_df_tourney_league_ids()["id"])

        base_url = "https://api.underdogfantasy.com/v1/user/tournament_rounds/"
        tourney_league_urls = []
        for tourney_league_id in tourney_league_ids:
            tourney_league_url = base_url + tourney_league_id + "/drafts"

            tourney_league_urls.append(tourney_league_url)

        return tourney_league_urls


class Slates(BaseData):
    """
    Compiles all available and completed slates for a specific slate type.
    """

    url_slates_available = "https://stats.underdogfantasy.com/v1/sports/nfl/slates"
    url_slates_completed = "https://api.underdogfantasy.com/v2/user/completed_slates"
    url_slates_settled = (
        "https://api.underdogfantasy.com/v1/user/sports/nfl/settled_slates"
    )

    def __init__(self, headers: str, slate_type: str, clear_json_attrs: bool = True):
        """
        slate_type must be 'available', 'completed', or 'settled'
        """

        super().__init__(headers, clear_json_attrs=clear_json_attrs)

        self.slate_type = slate_type

        self.df_slates = None
        self.slates = []

        self.json = {}

    def create_df_slates(
        self, headers: dict = None, clear_json: bool = False
    ) -> pd.DataFrame:
        """
        Creates df of all the slates found.
        """

        if headers is None:
            headers = self.auth_header

        url = self._get_url()

        self.json = self.read_in_site_data(url, headers=self.auth_header)

        try:
            df = self.create_scraped_data_df(self.json["slates"])

            # This is stored as a list, but seems to always only contain
            # one id.
            df["contest_style_ids"] = df["contest_style_ids"].apply(lambda x: x[0])
        except IndexError:
            print(f"No data found in {url} - no df will be returned")
            df = None

        self.slates = self._create_slates(df)

        if clear_json:
            self.json = {}

        return df

    def _get_url(self) -> str:
        """
        Selects the url to be used based on the slate_type.
        """

        if self.slate_type == "available":
            url = Slates.url_slates_available
        elif self.slate_type == "completed":
            url = Slates.url_slates_completed
        elif self.slate_type == "settled":
            url = Slates.url_slates_settled

        return url

    def _create_slates(self, df_slates: pd.DataFrame) -> list:
        """
        Creates a list of Slate objects.
        """

        slates = []
        for i in range(len(df_slates)):
            slate = Slate(df_slates.iloc[i], self.slate_type)

            slates.append(slate)

        return slates


class Slate:
    def __init__(self, df_slate: pd.Series, slate_type):
        self.id = df_slate["id"]
        self.contest_style_ids = df_slate["contest_style_ids"]
        self.description = df_slate["description"]
        self.title = df_slate["title"]
        self.slate_type = slate_type

        try:
            self.draft_count = df_slate["draft_count"]
            self.tournament_draft_count = df_slate["tournament_draft_count"]
        except:
            pass


class ReferenceData(BaseData):
    """Compiles all major reference data into dataframes"""

    def __init__(
        self,
        headers: str,
        slate_id: str,
        scoring_type_id: str,
        clear_json_attrs: bool = True,
    ):
        super().__init__(headers, clear_json_attrs=clear_json_attrs)

        self.slate_id = slate_id
        self.scoring_type_id = scoring_type_id

        # week ID seems right but can't find the correct url for it
        # self._player_scores_wk_1_id = 78
        self._player_scores_wk_1_id = 1186

        self.url_players = (
            "https://stats.underdogfantasy.com/v1/slates/" + self.slate_id + "/players"
        )
        self.url_appearances = (
            "https://stats.underdogfantasy.com/v1/slates/"
            + self.slate_id
            + "/scoring_types/"
            + self.scoring_type_id
            + "/appearances"
        )
        self.url_teams = "https://stats.underdogfantasy.com/v1/teams"

        base_url_player_scores = "https://stats.underdogfantasy.com/v1/weeks/"
        end_url_player_scores = (
            "/scoring_types/" + self.scoring_type_id + "/appearances"
        )
        self.urls_player_scores = {
            "player_scores_wk_"
            + str(i + 1): base_url_player_scores
            + str(wk_id)
            + end_url_player_scores
            for i, wk_id in enumerate(
                range(self._player_scores_wk_1_id, self._player_scores_wk_1_id + 17)
            )
        }

        self.df_players = pd.DataFrame()
        self.df_appearances = pd.DataFrame()
        self.df_teams = pd.DataFrame()
        self.df_players_master = pd.DataFrame()
        self.df_player_scores = pd.DataFrame()

    def build_all_dfs(self):
        attrs = [attr for attr in dir(self) if attr.startswith("df_")]
        for attr in attrs:
            if attr == "df_players_master":
                pass
            else:
                try:
                    method_name = "create_" + attr
                    self.__dict__[attr] = getattr(self, method_name)()
                except:
                    print(getattr(self, method_name), "failed to run")

        # This ensures the dfs it depends on are created
        self.df_players_master = self.create_df_players_master()

        if self._clear_json_attrs == True:
            self.clear_json_attrs()

    def create_df_players(self) -> pd.DataFrame:
        self.json_players = self.read_in_site_data(
            self.url_players, headers=self.auth_header
        )

        initial_scraped_df = self.create_scraped_data_df(self.json_players["players"])
        initial_scraped_df.drop(["image_url"], axis=1, inplace=True)
        initial_scraped_df.rename(columns={"id": "player_id"}, inplace=True)

        return initial_scraped_df

    def create_df_appearances(self) -> pd.DataFrame:
        self.json_appearances = self.read_in_site_data(
            self.url_appearances, headers=self.auth_header
        )

        initial_scraped_df = self.create_scraped_data_df(
            self.json_appearances["appearances"]
        )
        initial_scraped_df.drop(
            ["latest_news_item_updated_at", "score"], axis=1, inplace=True
        )

        # 'projection' column values are dicitionaries which can be converted to a df and merged
        projection_col = initial_scraped_df["projection"].to_list()
        projection_df = self.create_scraped_data_df(projection_col)

        projection_df.drop(["id", "scoring_type_id"], axis=1, inplace=True)
        projection_df.rename(
            columns={"points": "season_projected_points"}, inplace=True
        )

        final_df = pd.merge(
            initial_scraped_df,
            projection_df,
            left_index=True,
            right_index=True,
            how="left",
        )
        final_df.drop(["projection"], axis=1, inplace=True)

        df_pos_map = self._create_position_mapping(final_df)
        final_df = pd.merge(final_df, df_pos_map, on="position_id", how="left")

        final_df.rename(columns={"id": "appearance_id"}, inplace=True)

        return final_df

    def create_df_teams(self) -> pd.DataFrame:
        self.json_teams = self.read_in_site_data(
            self.url_teams, headers=self.auth_header
        )

        initial_scraped_df = self.create_scraped_data_df(self.json_teams["teams"])

        keep_vars = ["id", "abbr", "name"]
        final_df = initial_scraped_df[keep_vars].copy()

        final_df.rename(columns={"name": "team_name", "id": "team_id"}, inplace=True)

        return final_df

    def create_df_players_master(self) -> pd.DataFrame:
        """Creates a master lookup for player attributes"""

        if len(self.df_appearances) == 0:
            self.df_appearances = self.create_df_appearances()

        if len(self.df_players) == 0:
            self.df_players = self.create_df_players()

        if len(self.df_teams) == 0:
            self.df_teams = self.create_df_teams()

        # Team is more accurate in the df_players data and position from df_appearances
        # reflects the posisiton at the time of the draft
        df_appearances = self.df_appearances.drop(["team_id"], axis=1, inplace=False)
        df_players = self.df_players.drop(["position_id"], axis=1, inplace=False)

        final_df = pd.merge(df_appearances, df_players, on="player_id", how="left")

        final_df = pd.merge(final_df, self.df_teams, on="team_id", how="left")

        return final_df

    def create_df_player_scores(self):
        """
        This no longer appears to work due to either a change in the endpoint
        or the starting point week id is wrong
        """

        self.json_player_scores = {
            "player_scores_wk_"
            + str(i + 1): self.read_in_site_data(
                self.urls_player_scores["player_scores_wk_" + str(i + 1)],
                headers=self.auth_header,
            )
            for i, wk_id in enumerate(
                range(self._player_scores_wk_1_id, self._player_scores_wk_1_id + 17)
            )
        }

        player_scores_df_list = []
        for wk_id in range(1, 18):
            if (
                len(
                    self.json_player_scores["player_scores_wk_" + str(wk_id)][
                        "appearances"
                    ]
                )
                > 0
            ):
                player_scores_json = self.json_player_scores[
                    "player_scores_wk_" + str(wk_id)
                ]
                player_scores_df = self._create_df_player_scores_one_wk(
                    player_scores_json["appearances"]
                )
                player_scores_df["week_number"] = wk_id

                player_scores_df_list.append(player_scores_df)
            else:
                pass

        player_scores_df = pd.concat(player_scores_df_list)
        player_scores_df.reset_index(inplace=True)

        return player_scores_df

    def _create_df_player_scores_one_wk(self, scraped_data: list) -> pd.DataFrame:
        """
        Each weeks player scores are contained in its own URL - this creates a df
        of those scores for one week
        """

        initial_scraped_df = self.create_scraped_data_df(scraped_data)
        initial_scraped_df.drop(["latest_news_item_updated_at"], axis=1, inplace=True)

        # 'projection' column values are dicitionaries which can be converted to a df and merged
        projection_col = initial_scraped_df["projection"].to_list()
        projection_df = self.create_scraped_data_df(projection_col)

        projection_df = projection_df[["points"]]
        projection_df.rename(columns={"points": "projected_points"}, inplace=True)

        score_col = initial_scraped_df["score"].to_list()
        score_df = self.create_scraped_data_df(score_col)

        score_df = score_df[["points"]]
        score_df.rename(columns={"points": "actual_points"}, inplace=True)

        final_df = pd.merge(
            initial_scraped_df,
            projection_df,
            left_index=True,
            right_index=True,
            how="left",
        )
        final_df = pd.merge(
            final_df, score_df, left_index=True, right_index=True, how="left"
        )

        final_df.drop(["projection", "score"], axis=1, inplace=True)

        return final_df

    def _create_position_mapping(self, df_appearances: pd.DataFrame) -> pd.DataFrame:
        """
        Creates df that maps position to position_id since this cant be found in the API
        """

        df_pos_map = df_appearances.copy()

        df_pos_map["position"] = df_pos_map["position_rank"].str[0:2]
        df_pos_map = df_pos_map[["position_id", "position"]].loc[
            df_pos_map["position"].notnull()
        ]
        df_pos_map = df_pos_map.drop_duplicates(
            subset=["position", "position_id"], keep="first"
        )

        return df_pos_map


class ContestRefs(BaseData):
    """
    Compiles all major contest related data into dataframes.
    Note that this includes contests specific to a user (e.g. completed
    slates, settled slates, etc.)
    """

    url_scoring_types = "https://stats.underdogfantasy.com/v1/scoring_types"
    url_contest_styles = "https://stats.underdogfantasy.com/v1/contest_styles"

    def __init__(self, headers: str, clear_json_attrs: bool = True):
        super().__init__(headers, clear_json_attrs=clear_json_attrs)

        self.df_scoring_types = None
        self.df_contest_styles = None

        self.json = {}

    def create_df_scoring_types(
        self, headers: dict = None, clear_json: bool = False, update_attr: bool = False
    ) -> pd.DataFrame:
        """
        Creates a scoring type level df with the scoring types of all existing
        NFL contests.

        Notes:
            - This is needed to automate the "appearances" (i.e. draft rank)
            pull which uses the id as part of the url string
            - 'display_stats' contains more descriptive information about each
            scoring_type, but that data isn't needed now and would take some
            time to pull out and structure.
        """

        if headers is None:
            headers = self.auth_header

        self.json["scoring_types"] = self.read_in_site_data(
            ContestRefs.url_scoring_types, headers=self.auth_header
        )

        df = self.create_scraped_data_df(self.json["scoring_types"]["scoring_types"])

        df = df.loc[df["sport_id"] == "NFL"]

        if update_attr:
            self.df_scoring_types = df

        if clear_json:
            del self.json["scoring_types"]

        return df

    def create_df_contest_styles(
        self, headers: dict = None, clear_json: bool = False, update_attr: bool = False
    ) -> pd.DataFrame:

        if headers is None:
            headers = self.auth_header

        self.json["contest_styles"] = self.read_in_site_data(
            ContestRefs.url_contest_styles, headers=self.auth_header
        )

        df = self.create_scraped_data_df(self.json["contest_styles"]["contest_styles"])

        df = df.loc[df["sport_id"] == "NFL"]

        if update_attr:
            self.df_contest_styles = df

        if clear_json:
            del self.json["contest_styles"]

        return df


def create_underdog_df_dict(bearer_token: str, sleep_time: int = 0) -> dict:
    """
    Creates a dictionary of dfs containing the most relevant UD data

    TODO: Update to align with the refactored code.
    """

    pass

    # ref_data = ReferenceData()
    # ref_data.build_all_dfs()

    # user_data = UserData(bearer_token)
    # user_data.build_all_dfs()
    # league_ids = list(user_data.df_all_leagues["id"])

    # league_data = LeagueData(league_ids, bearer_token)
    # league_data.build_all_dfs(sleep_time=sleep_time)

    # df_players_master = ref_data.df_players_master
    # df_player_scores = ref_data.df_player_scores

    # player_vars = [
    #     "appearance_id",
    #     "player_id",
    #     "position",
    #     "team_name",
    #     "first_name",
    #     "last_name",
    # ]
    # df_drafts = pd.merge(
    #     league_data.df_drafts,
    #     df_players_master[player_vars],
    #     on="appearance_id",
    #     how="left",
    # )
    # df_weekly_scores = league_data.df_weekly_scores

    # final_dict = {
    #     "df_players_master": df_players_master,
    #     "df_player_scores": df_player_scores,
    #     "df_drafts": df_drafts,
    #     "df_weekly_scores": df_weekly_scores,
    #     "df_league_info": user_data.df_all_leagues,
    # }

    # return final_dict


if __name__ == "__main__":
    ##############################################################
    ####################### Get all DFs ##########################
    ##############################################################

    import getpass

    import UD_draft_model.scrapers.scrape_site.pull_bearer_token as pb

    pd.set_option("display.max_rows", 50)
    pd.set_option("display.max_columns", 50)

    ### Variables to change ###
    chromedriver_path = "/usr/bin/chromedriver"
    username = input("Enter Underdog username: ")
    # password = getpass.getpass()

    ### Keep as is ###
    # url = "https://underdogfantasy.com/lobby"
    # bearer_token = pull_bearer_token(url, chromedriver_path, username, password)

    headers = pb.read_headers()[username]
    valid_token = pb.test_headers(headers)

    if valid_token == False:
        password = getpass.getpass()
        url = "https://underdogfantasy.com/lobby"
        bearer_token = pb.pull_bearer_token(url, chromedriver_path, username, password)

        pb.save_bearer_token(username, bearer_token)

    ### Pull all major UD data elements ###
    draft_id = "2d30ccdc-4b4a-4d19-9532-d13b1cc33a3b"
    draft_detail = DraftsDetail([draft_id], headers)
    drafts_active = DraftsActive(headers)
    slates = Slates(headers, "completed")
    df_slates = slates.create_df_slates()
    slate = slates.slates[0]
    drafts = Drafts(headers, slate)
    # refs = ReferenceData(headers, slate.id, )

    df_a = draft_detail.create_df_drafts()
    df_b = drafts_active.create_df_active_drafts()

    # print(df_a)
    print(type(slate.id))
    # print(drafts_active.auth_header)

    # underdog_data = create_underdog_df_dict(bearer_token, sleep_time=5)
