from scraping import setup_Chrome_driver
from datetime import date, datetime, timedelta
from database import load_event_from_db, store_race_tmp, confirm_discipline, delete_from_results, delete_from_event_stats, store_events, insert_new_results 
from rankings import calculate_race_rankings
from eventor import deduct_list_name_from_class_name
import time

from bs4 import BeautifulSoup


def get_soup(driver, my_url):
    print(f"starting get_soup")
    print('Open browser for', my_url)
    page = ''
    timer = 0
    while page == '':
        try:
            driver.get(my_url)
            break
        except:
            print("Connection refused")
            timer += 10
            print("Sleep for", timer, "seconds")
            time.sleep(timer)
            print("Continue...")
            continue

    # Wait for the page to fully load (you may need to adjust the sleep time based on the page)
    time.sleep(1)

    # Get the full page source including data loaded by JavaScript
    full_page_source = driver.page_source
    
    # Now you can use BeautifulSoup to parse the HTML content
    soup = BeautifulSoup(full_page_source, 'html.parser')
    return soup



def load_from_old_site(my_year, driver):
    print(f"starting load_from_old_site")
    # get the event page
    year_url = f"https://rankings.orienteering.asn.au/{my_year}/men.htm"

    new_results = []
    new_events = []

    soup = get_soup(driver, year_url)

    # find <font color="#009933">Latest Ranking Events</font>
    row_element = soup.find('font', color="#009933", text="Latest Ranking Events")
    
    # Find the next row with an <a> tag and get the href link
    next_row = row_element.find_next('tr')
    table_element = row_element.find_parent('table')
    while next_row and next_row.find_parent('table') == table_element:
        a_tag = next_row.find('a')
        if a_tag and 'href' in a_tag.attrs:
            my_class = a_tag.text.strip()
            href_link = a_tag['href']
            #print(f"Found href link: {href_link}")
            if not href_link.startswith("http://"):
                # Extract the event code from the href link
                event_code = href_link.split('.htm')[0]
                print(f"\033[94mEvent code: {event_code}\033[0m")
                # test to see if the event is already loaded
                event, results = load_event_from_db(event_code)
                if event:
                    print(f"Event {event_code} already loaded")
                    #print(f"Event details: {event}")
                    event_id = event['id']
                    print(f"Event ID: {event_id}")
                    #print(f"Results: {results}")
                    if results:
                        review_calculate_store_results(results, event_code, event_id)
                        # get the next row
                        next_row = next_row.find_next('tr')
                    else:
                        print(f"No results found for event {event_code}")

                        # attempt to load the results from the oldsite event page
                        new_results = scrape_results_oldsite(my_year, event_code, driver)

                        if new_results:
                            review_calculate_store_results(new_results, event_code, event_id)

                        # get the next row
                        next_row = next_row.find_next('tr')

                else:
                    print(f"Event {event_code} not loaded yet")
                    # Process the event page to extract event details and results
                    
                    new_event, new_results = scrape_event_results_from_old_site(my_year, event_code, driver, my_class)
                    if new_event:
                        #print(f"New event: {new_event}")
                        tuple_event = tuple(new_event.values())
                        new_events = []
                        new_events.append(tuple_event)
                        #print(f"New events: {new_events}")
                        # store the new event in the database
                        store_events(new_events)
                        
                        # get the event ID
                        event_id = load_event_from_db(event_code)[0]['id']

                    if new_results:
                        review_calculate_store_results(new_results, event_code, event_id)

                    # get the next row
                    next_row = next_row.find_next('tr')
                
            else:
                print("Skipping the link to external IOF WRE site")
                # get the next row
                next_row = next_row.find_next('tr')

        else:
            print("No <a> tag with href found in the this row")
            # get the next row      
            next_row = next_row.find_next('tr')

    if my_year:
        print(my_year)
        # Remember to review Discipline  (discipline = 'Middle/Long' by default)
        confirm_discipline(int(my_year))

    return new_events, new_results




def load_year_old_site(input, driver):
    print(f"starting load_year_old_site")

    # for each event, retrieve the new_events and new_results by scraping the web page
    new_events = []
    new_results = []

    my_year = input['year']
    print(f"my_year: {my_year}")
    
    events, results = load_from_old_site(my_year, driver)
    
    for event in events:
        new_events.append(event)
    for result in results:
        new_results.append(result)

    return new_events, new_results



def review_calculate_store_results(results, event_code, event_id):
    print(f"starting review_calculate_store_results")
    #print(f"results: {results}")
    max_race_points = max(result['race_points'] for result in results)
    if float(max_race_points) > 700:
        print(f"Max race points within range: {max_race_points}")
        
        # store the results in the database
        
        # print("Testing store_results")
        # print(f"results: {results}")
        for result in results:
            try:
                result['place'] = int(result['place'])
            except ValueError:
                result['place'] = 0
        insert_new_results(results)
        
    else:
        print(f"\033[91mNeed to recalculate based on max_points = : {max_race_points}\033[0m")
        #print(f"store results in race_tmp { results }")
        for result in results:
            result['place'] = int(result['place'])
        data_to_insert = [tuple(result.values())[1:5] for result in results]
        #print(f"data_to_insert: {data_to_insert}")
        
        store_race_tmp(event_code, data_to_insert)

        # remove old results from the database
        delete_from_results(event_code)
        delete_from_event_stats(event_id)

        # recalculate the ranking scores
        calculate_race_rankings(event_code)




def scrape_event_results_from_old_site(my_year, event_code, driver, my_class):
    new_event = {}
    new_results = []

    # get the event page
    event_url = f"https://rankings.orienteering.asn.au/{my_year}/{event_code}.htm"


    soup = get_soup(driver, event_url)
    
    # Find the h2 element
    h2_element = soup.find('h2')
    if h2_element:
        # Extract event long description from the <font> tag
        font_element = h2_element.find('font')
        if font_element:
            event_long_desc = font_element.text.strip()
            #print(f"Event long description: {event_long_desc}")
        # Extract event short description from the <p> tag after <h2>
        p_element = h2_element.find_next('p')
        if p_element:
            # Extract event date from the <i> tag
            i_element = p_element.find('i')
            if i_element:
                event_date_str = i_element.text.strip()
                # handle either dd-mm-yy or dd-mm-yyyy
                try:
                    event_date_str2 = datetime.strptime(event_date_str, '%d-%b-%y').strftime('%Y-%m-%d')
                except ValueError:
                    event_date_str2 = datetime.strptime(event_date_str, '%d-%b-%Y').strftime('%Y-%m-%d')

                # Find the <td> element containing text "IP"
                td_ip_element = soup.find('td', text='IP')
                if td_ip_element:
                    # Extract the IP value from the next <td> element
                    next_td_element = td_ip_element.find_next('td')
                    if next_td_element:
        
                        new_event['date'] = event_date_str2
                        new_event['short_desc'] = event_code
                        new_event['long_desc'] = event_long_desc
                        new_event['class'] = my_class
                        new_event['short_file'] = event_code
                        new_event['ip'] = next_td_element.text.strip()
                        new_event['list'] = deduct_list_name_from_class_name(my_class)
                        new_event['eventor_id'] = None
                        new_event['iof_id'] = None
                        new_event['discipline'] = 'Middle/Long'  # this defaults to middle/long, but can be changed to sprint if needed
    
                # indent as needed
                new_results = scrape_results_oldsite(my_year, event_code, driver)

    return new_event, new_results 



def scrape_results_oldsite(my_year, event_code, driver):
    new_results = []

    # get the event page
    event_url = f"https://rankings.orienteering.asn.au/{my_year}/{event_code}.htm"

    soup = get_soup(driver, event_url)
    
    # Find the h2 element
    h2_element = soup.find('h2')
    if h2_element:

        # Find the table element
        result_table = h2_element.find_next('table')
        if result_table:
            #print("Found resultList table")
            # Extract the <tbody> from the table
            tbody = result_table.find('tbody')
            if tbody:
                #print("Found tbody in resultList table")
                # Process the rows in the tbody
                rows = tbody.find_all('tr')
                for row in rows:
                    # Extract data from each row as needed
                    columns = row.find_all('td')
                    if columns:
                        # Example: Extracting text from each column
                        row_data = [col.text.strip() for col in columns]
                        #print(f"Row data: {row_data}")
                        # You can further process the row_data as needed
                        if row_data[3] == '':
                            row_data[3] = 0
                        new_result = {
                            'race_code': event_code,
                            'place': row_data[0],
                            'full_name': row_data[1],
                            'race_time': row_data[2],
                            'race_points': row_data[3]  # You can calculate race points if needed
                        }
                        new_results.append(new_result)
    #print(f"new_results: {new_results}")
    return new_results

