from datetime import datetime
from scraping import load_from_WRE, load_latest_from_WRE, load_year_from_WRE
from database import store_events_and_results, store_race_tmp, store_events, confirm_discipline
from scraping import setup_Chrome_driver
from eventor import load_race_from_eventor_by_class, load_race_from_eventor_by_ids
from eventor_api import load_race_from_eventor_api_by_ids
from rankings import calculate_race_rankings
from oldsite import load_year_old_site


def get_year_old_site(input):
    print("get_year_old_site started:", datetime.now())
    driver = setup_Chrome_driver()
    new_events, new_results = load_year_old_site(input, driver)
    driver.quit()
    print("Finished scraping from old site:", datetime.now())
    #store_events_and_results(new_events, new_results)



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



def process_and_store_eventor_event_by_class(input):
    print("process_and_store_eventor_event_by_class started:", datetime.now())
    driver = setup_Chrome_driver()
    new_events, new_results = load_race_from_eventor_by_class(input, driver)
    driver.quit()
    print("Finished scraping race from Eventor site:", datetime.now())

    pre_data_to_insert = []
    print(f"store events: {new_events}")

    for event in new_events:
        print(f"store event: {event}")
        print(f"event_date: {event['date']}")
        # Convert event_date format if necessary
        if 'date' in event and isinstance(event['date'], str):
            try:
                event_date = datetime.strptime(event['date'], '%d/%m/%Y')
                event['date'] = event_date.strftime('%Y-%m-%d')
            except ValueError:
                pass
        print(f"reformatted date: {event['date']}")
        # store the event in the DB
        row = tuple(event.values())
        pre_data_to_insert.append(row)

    store_events(pre_data_to_insert)


    #store results in race_tmp in the DB
    
    for result in new_results:
        try:
            result['place'] = int(result['place'])
        except (ValueError, TypeError):
            result['place'] = 0
    #print(f"store results in race_tmp { new_results }")
    data_to_insert = [{k: v for k, v in result.items() if k not in ['race_code', 'club']} for result in new_results]
    # convert MM:SS to 00:MM:SS
    for result in data_to_insert:
        if isinstance(result['race_time'], str) and result['race_time'].startswith('-'):
            result['race_time'] = "no time"
            result['place'] = 0
        if isinstance(result['race_time'], str) and ':' in result['race_time']:
            parts = result['race_time'].split(':')
            if len(parts) == 2:
                result['race_time'] = f"00:{result['race_time']}"
    data_to_insert = [tuple(result.values()) for result in data_to_insert]
    print(f"data_to_insert: {data_to_insert}")
    new_class = input['class'].replace(' ', '').strip().lower()
    short_desc = "au" + input['eventor_race_id'] + new_class
    store_race_tmp(short_desc, data_to_insert)


    for event in new_events:
        print(f"preparing to calculate")
        print(event)
        calculate_race_rankings(event['short_desc'])
        my_year = datetime.strptime(event['date'], '%Y-%m-%d').year
        if my_year:
            print(my_year)
            # Remember to review Discipline  (discipline = 'Middle/Long' by default)
            confirm_discipline(int(my_year))


    print("Finished process_and_store_eventor_event_by_class:", datetime.now())



def process_and_store_eventor_event_by_ids(eventId, eventClassId, eventRaceId):
    print("process_and_store_eventor_event_by_ids started:", datetime.now())
    
    # firstly, scrape the event from Eventor
    # driver = setup_Chrome_driver()
    # new_events, new_results = load_race_from_eventor_by_ids(eventId, eventClassId, eventRaceId, driver)
    # driver.quit()
    # print("Finished scraping race from Eventor site:", datetime.now())

    # alternatively, obtain the data from Eventor API
    new_events, new_results = load_race_from_eventor_api_by_ids(eventId, eventClassId, eventRaceId)
    print("Finished obtaining result data from Eventor APIs:", datetime.now())

    pre_data_to_insert = []
    print(f"store events: {new_events}")

    # this should only result in one event
    for event in new_events:
        print(f"store event: {event}")
        print(f"event_date: {event['date']}")
        # Convert event_date format if necessary
        if 'date' in event and isinstance(event['date'], str):
            try:
                event_date = datetime.strptime(event['date'], '%d/%m/%Y')
                event['date'] = event_date.strftime('%Y-%m-%d')
            except ValueError:
                pass
        print(f"reformatted date: {event['date']}")
        # store the event in the DB
        row = tuple(event.values())
        pre_data_to_insert.append(row)
        

    store_events(pre_data_to_insert)


    #store results in race_tmp in the DB
    for result in new_results:
        try:
            result['place'] = int(result['place'])
        except (ValueError, TypeError):
            result['place'] = 0
    #print(f"store results in race_tmp { new_results }")
    data_to_insert = [{k: v for k, v in result.items() if k not in ['race_code', 'club']} for result in new_results]
    # convert MM:SS to 00:MM:SS
    for result in data_to_insert:
        if isinstance(result['race_time'], str) and result['race_time'].startswith('-'):
            result['race_time'] = "no time"
            result['place'] = 0
        if isinstance(result['race_time'], str) and ':' in result['race_time']:
            parts = result['race_time'].split(':')
            if len(parts) == 2:
                result['race_time'] = f"00:{result['race_time']}"
    data_to_insert = [tuple(result.values()) for result in data_to_insert]
    print(f"data_to_insert: {data_to_insert}")

    if new_events:
        short_desc = new_events[0]['short_desc']
        store_race_tmp(short_desc, data_to_insert)

        print(f"preparing to calculate")
        print(new_events[0])
        calculate_race_rankings(new_events[0]['short_desc'])
        my_year = datetime.strptime(new_events[0]['date'], '%Y-%m-%d').year
        if my_year:
            print(my_year)
            # Remember to review Discipline  (discipline = 'Middle/Long' by default)
            confirm_discipline(int(my_year))


    print("Finished process_and_store_eventor_event_by_class:", datetime.now())
