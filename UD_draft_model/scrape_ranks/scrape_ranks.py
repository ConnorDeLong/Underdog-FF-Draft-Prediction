from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from math import ceil
from os import path
from time import sleep
import pandas as pd


def change_dates(driver: webdriver.Chrome, date: str) -> webdriver.Chrome:
    """ 
    Updates the date filters 
    date param formatted as yyyy-mm-dd
    """

    # Updates both date filters, although only the first is needed
    for i in range(0, 2):
        elem = driver.find_elements_by_class_name('form-control')[i]
        elem.clear()
        elem.send_keys(date)
        elem.send_keys(Keys.RETURN)

    return driver


def next_page(driver: webdriver.Chrome) -> webdriver.Chrome:
    """ Selects the next page of data """

    # Get parent navigation element
    name = 'rt-pagination-nav'
    nav = WebDriverWait(driver, timeout=10).until(lambda d: d.find_elements(By.CLASS_NAME, name))[0]

    # Next button always listed last (can't select by the class name for some reason)
    next = nav.find_elements_by_css_selector("*")[-1]
    next.send_keys(Keys.RETURN)

    return driver


def create_date_list(start_date: str, end_date: str) -> list:
    """ Creates a list for every data between the start and end date params """

    start = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.datetime.strptime(end_date, '%Y-%m-%d')

    num_days = (end - start).days

    date_list = []
    for i in range(0, num_days + 1):
        day = start + datetime.timedelta(days=i)
        date_list.append(day.strftime('%Y-%m-%d'))

    return date_list


def extract_page_ranks(driver: webdriver.Chrome) -> pd.DataFrame:
    """ Extracts the current rankings table into a df"""

    # Each element is a row with the children representing a column
    rows = WebDriverWait(driver, timeout=10).until(lambda d: d.find_elements(By.CLASS_NAME,"rt-tr"))

    data = []
    for i, row in enumerate(rows):
        # Don't need the header row
        if i == 0:
            continue
        
        cols = row.find_elements_by_css_selector("*")
        
        extracted_row = []
        for j, col in enumerate(cols):
            # Excluding Old ADP, ADP Change, and Pos Rank
            if j in(4, 5, 7):
                continue

            extracted_row.append(col.text)

        data.append(extracted_row)

    cols = ['player', 'pos', 'team', 'adp', 'rank']

    df = pd.DataFrame(data, columns=cols)

    return df


def extract_day_ranks(driver: webdriver.Chrome, date: str, num_ranks: int=400) -> pd.DataFrame:
    """ 
    Creates df of all ranks from a day up to the number of ranks passed 
    
    """

    driver = change_dates(driver, date)

    num_pages = ceil(num_ranks / 50)

    dfs = []
    for i in range(num_pages):
        if i == 0:
            df = extract_page_ranks(driver)
        else:
            driver = next_page(driver)            
            df = extract_page_ranks(driver)

        dfs.append(df)

    df = pd.concat(dfs)
    df['date'] = date

    return df


def export_day_ranks(url, driver_path, start_date: str, end_date: str
                            , export_folder: str, num_ranks: int=400) -> None:
    """ 
    Exports the ranks for each day from start_date to end_date as separate
    csvs stored in the export_folder param
    """

    dates = create_date_list(start_date, end_date)

    for date in dates:
        driver = webdriver.Chrome(CHROMEDRIVER_PATH)
        driver.get(URL)

        df = extract_day_ranks(driver, date, num_ranks)
        
        driver.close()
        driver.quit()

        date_f = date.replace('-', '')
        full_path = path.join(export_folder, f'df_player_ranks_{date_f}.csv')

        df.to_csv(full_path, index=False)

        sleep(5)

    return None


if __name__ == '__main__':

    CHROMEDRIVER_PATH = '/usr/bin/chromedriver'
    URL = 'https://sam-hoppen.shinyapps.io/UD_ADP/'
    OUTPUT_FOLDER = '~/Python-Projects/UD-Draft-Model/Repo-Work/UD-Draft-Model\
        /data/2022/player_ranks'

    # export_day_ranks(URL, CHROMEDRIVER_PATH, '2022-10-01', '2022-10-08'
    # , OUTPUT_FOLDER, num_ranks=400)