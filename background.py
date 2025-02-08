from datetime import datetime
from scraping import load_from_WRE, load_latest_from_WRE, load_year_from_WRE
from database import store_events_and_results
from scraping import setup_Chrome_driver

def process_and_store_data(input):
    print("process_and_store_data started:", datetime.now())
    driver = setup_Chrome_driver()
    new_events, new_results = load_from_WRE(input, driver)
    driver.quit()
    print("Finished scraping from WRE site:", datetime.now())
    store_events_and_results(new_events, new_results)


def process_latest_WRE_races():
    print("Started process_latest_WRE_races:", datetime.now())
    new_events, new_results = load_latest_from_WRE()
    print("Finished scraping from WRE site:", datetime.now())
    store_events_and_results(new_events, new_results)
    print("Finished process_latest_WRE_races:", datetime.now())


def upload_year_WRE_races(year):
    print("Started process_latest_WRE_races:", datetime.now())
    new_events, new_results = load_year_from_WRE(year)
    print("Finished scraping from WRE site:", datetime.now())
    store_events_and_results(new_events, new_results)
    print("Finished process_latest_WRE_races:", datetime.now())
