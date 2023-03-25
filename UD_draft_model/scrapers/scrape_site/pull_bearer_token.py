"""
Module is responsible for pulling a bearer token that can be used to scrape the API
"""
import time
import os
import json

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

import UD_draft_model.scrapers.scrape_site.scrape_league_data as scrape_site


def create_webdriver(url, chromedriver_path, username, password):

    capabilities = DesiredCapabilities.CHROME
    capabilities["goog:loggingPrefs"] = {"performance": "ALL"}

    driver = webdriver.Chrome(chromedriver_path)
    driver.get(url)

    # elem = driver.find_elements_by_class_name('styles__field__3fmc7')[0]
    elem = driver.find_elements_by_class_name("styles__field__OeiFa  ")[0]
    elem.clear()
    elem.send_keys(username)
    elem.send_keys(Keys.RETURN)

    # elem = driver.find_elements_by_class_name('styles__field__3fmc7')[0]
    elem = driver.find_elements_by_class_name("styles__field__OeiFa  ")[1]
    elem.clear()
    elem.send_keys(password)
    elem.send_keys(Keys.RETURN)

    return driver


def pull_bearer_token(url, chromedriver_path, username, password):

    driver = create_webdriver(url, chromedriver_path, username, password)

    time.sleep(20)
    logs = driver.get_log("performance")

    for log in logs:
        try:
            log_dict = json.loads(log["message"])
            bearer_token = log_dict["message"]["params"]["response"]["headers"][
                "authorization"
            ]

            if bearer_token[:6] == "Bearer":
                break

        except:
            pass

    driver.close()
    driver.quit()

    return bearer_token


def create_token_path() -> str:
    """
    Creates the path to the bearer_token data.
    """

    relative_path = "scrapers/scrape_site/bearer_token"

    cwd = os.getcwd()
    folder_end_index = cwd.rfind("UD_draft_model") + len("UD_draft_model")

    if cwd.rfind("UD_draft_model") == -1:
        base_path = os.path.join(cwd, "UD_draft_model")
    else:
        base_path = cwd[:folder_end_index]

    token_dir = os.path.join(base_path, relative_path)
    token_path = os.path.join(token_dir, "bearer_token.json")

    return token_path


def read_bearer_tokens(file_path: str = None) -> dict:
    """
    Reads in all user's bearer tokens.
    """

    if file_path is None:
        file_path = create_token_path()

    with open(file_path, "r") as f:
        json_data = json.load(f)

    return json_data


def save_bearer_token(username: str, bearer_token: str) -> None:
    """
    Saves the bearer token to a json file to prevent re-scraping the token
    when it's still active.
    """

    token_path = create_token_path()

    try:
        token_data = read_bearer_tokens(file_path=token_path)
    except FileNotFoundError:
        token_data = {}

    token_data[username] = bearer_token
    print(token_data)

    with open(token_path, "w") as f:
        json.dump(token_data, f)

    return None


def test_bearer_token(bearer_token: str) -> bool:
    """
    Returns a True value if the bearer_token.
    """

    url = "https://api.underdogfantasy.com/v1/user"
    base_data = scrape_site.BaseData()
    base_data.auth_header["authorization"] = bearer_token

    data = base_data.read_in_site_data(url, headers=base_data.auth_header)

    if "error" in (list(data.keys())):
        token_valid = False
    else:
        token_valid = True

    return token_valid


if __name__ == "__main__":
    pass

    import getpass

    ### Variables to change ###
    # chromedriver_path = "/usr/bin/chromedriver"
    # username = input("Enter Underdog username: ")
    # password = getpass.getpass()

    ### Keep as is ###
    # url = "https://underdogfantasy.com/lobby"
    # bearer_token = pull_bearer_token(url, chromedriver_path, username, password)
