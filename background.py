from datetime import datetime
from scraping import load_from_WRE, load_latest_from_WRE
from database import store_events_and_results

sydney_tz = 'Australia/Sydney'

def process_and_store_data(input):
    print("process_and_store_data started:", datetime.now(sydney_tz))
    new_events, new_results = load_from_WRE(input['IOF_event_id'])
    print("Finished scraping from WRE site:", datetime.now(sydney_tz))
    store_events_and_results(new_events, new_results)


def process_latest_WRE_races():
    print("Started process_latest_WRE_races:", datetime.now(sydney_tz))
    new_events, new_results = load_latest_from_WRE()
    print("Finished scraping from WRE site:", datetime.now(sydney_tz))
    store_events_and_results(new_events, new_results)
    print("Finished process_latest_WRE_races:", datetime.now(sydney_tz))
