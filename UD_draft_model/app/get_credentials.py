import streamlit as st
from selenium.common.exceptions import WebDriverException

import UD_draft_model.scrapers.scrape_site.pull_bearer_token as pb
from UD_draft_model.app.save_session_state import SaveSessionState


class Credentials(SaveSessionState):
    def __init__(self, chromedriver_path: str, session_state=None) -> None:
        super().__init__(session_state=session_state)

        self.chromedriver_path = chromedriver_path
        self.initialize_session_state("headers", {})
        self.initialize_session_state("valid_credentials", False)

    def _get_headers(
        self, username: str, password: str, save_headers: bool = False
    ) -> dict:
        """
        Pulls the bearer token and user-agent required to make api requests.

        Parameters
        ----------
        username : str
            UD username/email.
        password : str
            UD password.
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
            headers = pb.pull_required_headers(
                url, self.chromedriver_path, username, password
            )

            if save_headers:
                pb.save_headers(username, headers)

        return headers

    def enter_ud_credentials(self) -> bool:
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

        if self.valid_credentials == False:

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
                        headers = self._get_headers(
                            email, password, self.chromedriver_path
                        )
                        self.valid_credentials = True
                        self.headers = headers
                        placeholder.empty()
                    except KeyError:
                        pass
                    except UnboundLocalError:
                        st.write("Invalid Credentials - Please try again")
                    except WebDriverException:
                        st.write("Unable to check credentials")


#### DELETE THESE ###
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


def enter_ud_credentials(chromdriver_path: str) -> bool:
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


if __name__ == "__main__":
    CHROMEDRIVER_PATH = "/usr/bin/chromedriver"

    credentials = Credentials(CHROMEDRIVER_PATH, session_state=st.session_state)
    credentials.enter_ud_credentials()

    st.button("Re-run")
