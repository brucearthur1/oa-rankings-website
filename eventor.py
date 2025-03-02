from scraping import setup_Chrome_driver
from datetime import date, datetime, timedelta
from database import test_race_exist
import time

from bs4 import BeautifulSoup
import re


def deduct_list_name_from_class_name(my_class):
    pre_my_list_name = ""
    if "18" in my_class or "20" in my_class or "senior" in my_class.lower():
        pre_my_list_name = "junior "
    if my_class.lower().startswith("w"):
        post_my_list_name = "women"
    else:
        post_my_list_name = "men"
    my_list_name = pre_my_list_name + post_my_list_name

    return my_list_name



def filter_classes(my_classes):
    # my_classes is a list of my_class dictionaries
    # Filter out classes that are not relevant
    filtered_classes = []
    for my_class in my_classes:
        if any(keyword in my_class['class_name'].lower() for keyword in ["men", "women", "elite", "21e", "20e", "21a", "20a", "18a", "sport", "sb", "sg"]) and \
            all(substring not in my_class['class_name'].lower() for substring in ["21as", "20as"]):
            filtered_classes.append(my_class)
    return filtered_classes


def filter_event(event):
    include_event = False
    if event['results_href'] and \
        (event['event_discipline'] == 'F' or event['event_discipline'] == '') and \
        'relay' not in event['long_desc'].lower() and \
        ('school' not in event['long_desc'].lower() or event['event_classification'] == 'nat' ) and \
        (event['event_classification'] == 'champs' or event['event_classification'] == 'nat' or \
         event['event_classification'] == 'int' or \
         (event['event_classification'] == 'sta' and 'champ' in event['long_desc'].lower())) and \
        event['event_format'] == '' : 
        include_event = True
    return include_event



def get_html_from_url(url, driver):
    print(f"starting get_html_from_url")

    print('Open browser for', url)
    page = ''
    timer = 0
    while page == '':
        try:
            driver.get(url)
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
    return driver.page_source




def load_from_eventor_by_class(event_code, my_class, driver):
    print(f"starting load_from_eventor")
    new_results = []
    new_events = []

    # get the event page
    event_url = f"https://eventor.orienteering.asn.au/Events/ResultList?eventId={event_code}"

    full_page_source = get_html_from_url(event_url, driver)
    
    # Now you can use BeautifulSoup to parse the HTML content
    soup = BeautifulSoup(full_page_source, 'html.parser')

    # Find the element with class "individualResultList"
    result_list = soup.find(class_="individualResultList")
    if result_list:
        print("Found individualResultList")
        # get the event details
        # Look for <h2> tags containing "Official results for "
        name_tag = result_list.find('h2', text=lambda x: x and 'Official results for ' in x)
        if name_tag:
            event_name = name_tag.text.split('Official results for ')[1].strip()
            print(f"Event name from <h2>: {event_name}")

            # Find the <p> tag after the specified <p> tag
            toolbar_tag = result_list.find('p', class_='toolbar16 printHidden')
            if toolbar_tag:
                next_p_tag = toolbar_tag.find_next_sibling('p')
                if next_p_tag:
                    print(f"Next <p> tag content: {next_p_tag.text}")
                    
                    if 'Date: ' in next_p_tag.text:
                        event_date_str = next_p_tag.text.split('Date: ')[1].strip()
                        print(f"Event date: {event_date_str}")

                        my_list_name = deduct_list_name_from_class_name(my_class)

                        # Convert event_date_str to "YYYY-MM-DD" format
                        event_date = datetime.strptime(event_date_str, '%A %d %B %Y').strftime('%d/%m/%Y')
                        new_event = {
                            'date': event_date,
                            'short_desc': "au" + event_code.lower() + my_class.lower(),
                            'long_desc': event_name,
                            'class': my_class,
                            'short_file': "au" + event_code.lower() + my_class.lower(),
                            'ip': 1,
                            'list': my_list_name,
                            'eventor_id': event_code,
                            'iof_id': None,
                            'discipline': 'Middle/Long'  #can get this from eventor
                        }
                        new_events.append(new_event)


                else:
                    print("Next <p> tag not found")
            else:
                print("Toolbar <p> tag not found")
        else:
            print("Name not found")

        print(f"{result_list=}")
        # get results for the specified class
        # Find the element with class "eventClassHeader" and <h3> text = my_class
        class_header = result_list.find('h3', text=my_class)
        if class_header:
            print(f"Found class header: {class_header.text}")

            # Find the table with class "resultList"
            # Find the parent element
            parent_element = class_header.find_parent('div')
            if parent_element:
                print("Parent element found:", parent_element)
            else:
                print("No parent element found.")
            grand_parent_element = parent_element.find_parent('div')
            if grand_parent_element:
                print("Grand parent element found:", grand_parent_element)
            else:
                print("No grand parent element found.")

            result_table = grand_parent_element.find_next_sibling('table', class_='resultList')
            if result_table:
                print("Found resultList table")
                # Extract the <tbody> from the table
                tbody = result_table.find('tbody')
                if tbody:
                    print("Found tbody in resultList table")
                    # Process the rows in the tbody
                    rows = tbody.find_all('tr')
                    for row in rows:
                        # Extract data from each row as needed
                        columns = row.find_all('td')
                        if columns:
                            # Example: Extracting text from each column
                            row_data = [col.text.strip() for col in columns]
                            print(f"Row data: {row_data}")
                            # You can further process the row_data as needed
                            new_result = {
                                'race_code': "au" + event_code + my_class,
                                'place': row_data[0],
                                'athlete_name': row_data[1],
                                'club': row_data[2],
                                'race_time': row_data[3],  
                                'race_points': 0
                            }
                            new_results.append(new_result)

                else:
                    print("tbody not found in resultList table")
            else:
                print("resultList table not found")
            
        else:
            print(f"Class header with text '{my_class}' not found")

    else:
        print("individualResultList not found")


    return new_events, new_results




def load_race_from_eventor_by_class(input, driver):
    print(f"starting load_race_from_eventor_by_class")
    # for each event, retrieve the new_events and new_results by scraping the web page
    new_events = []
    new_results = []
    event_code = input['eventor_race_id']
    my_class = input['class']
    print(f"event_code: {event_code}")
    print(f"my_class: {my_class}")

    events, results = load_from_eventor_by_class(event_code, my_class, driver)
    
    for event in events:
        new_events.append(event)
    for result in results:
        new_results.append(result)

    return new_events, new_results


def load_race_from_eventor_by_ids(eventId, eventClassId, eventRaceId, driver):
    print(f"starting load_from_eventor_by_ids")
    new_results = []
    new_events = []

    event_code = eventId

    # get the specific event/class/race page
    event_url = f"https://eventor.orienteering.asn.au/Events/ResultList?eventId={eventId}&eventClassId={eventClassId}&eventRaceId={eventRaceId}&overallResults=False"

    full_page_source = get_html_from_url(event_url, driver)
    
    # Now you can use BeautifulSoup to parse the HTML content
    soup = BeautifulSoup(full_page_source, 'html.parser')

    # Find the element with class "individualResultList"
    result_list = soup.find(class_="individualClassResultList")
    if result_list:
        print("Found individualResultList")
        # get the event details
        # Look for <h2> tags containing "Official results for "
        name_tag = result_list.find('h2', text=lambda x: x and 'Official results for ' in x)
        if name_tag:
            event_name = name_tag.text.split('Official results for ')[1].strip()
            print(f"Event name from <h2>: {event_name}")

            # Find the <p> tag after the specified <p> tag
            toolbar_tag = result_list.find('p', class_='toolbar16 printHidden')
            if toolbar_tag:
                next_p_tag = toolbar_tag.find_next_sibling('p')
                if next_p_tag:
                    print(f"Next <p> tag content: {next_p_tag.text}")
                    
                    if 'Date: ' in next_p_tag.text:
                        event_date_str = next_p_tag.text.split('Date: ')[1].strip()
                        event_date_str = event_date_str.split('-')[0].strip()
                        print(f"Event date: {event_date_str}")

                        # get name of class from the filters panel
                        filters_tag = soup.find('p', class_='filters')
                        if filters_tag:
                            # Analyze each text block in filters_tag in between each of the <a> tags and find the text in the format " | text | "
                            for tag in filters_tag.find_all(text=True, recursive=False):
                                text = tag.strip()
                                if re.match(r'^\|\s.*\s\|$', text):
                                    my_class = text.strip('| ').strip()
                                    print(f"Class name from filters: {my_class}")
                                    break
                        # get the name of the class from h3 tag
                        else:
                            my_class = result_list.find('h3').text.strip()

                        my_list_name = deduct_list_name_from_class_name(my_class)

                        # Convert event_date_str to "YYYY-MM-DD" format
                        event_date = datetime.strptime(event_date_str, '%A %d %B %Y').strftime('%d/%m/%Y')
                        new_event = {
                            'date': event_date,
                            'short_desc': "au" + event_code.lower() + my_class.lower() + eventRaceId.lower(),
                            'long_desc': event_name,
                            'class': my_class,
                            'short_file': "au" + event_code.lower() + my_class.lower(),
                            'ip': 1,
                            'list': my_list_name,
                            'eventor_id': event_code,
                            'iof_id': None,
                            'discipline': 'Middle/Long'  #can get this from eventor
                        }
                        new_events.append(new_event)


                else:
                    print("Next <p> tag not found")
            else:
                print("Toolbar <p> tag not found")
        else:
            print("Name not found")

        #print(f"{result_list=}")
        # get results for the specified class
        # Find the element with class "eventClassHeader" and <h3> text = my_class

        result_table = result_list.find('table', class_='resultList')
        if result_table:
            print("Found resultList table")
            # Extract the <tbody> from the table
            tbody = result_table.find('tbody')
            if tbody:
                print("Found tbody in resultList table")
                # Process the rows in the tbody
                rows = tbody.find_all('tr')
                for row in rows:
                    # Extract data from each row as needed
                    columns = row.find_all('td')
                    if columns:
                        # Example: Extracting text from each column
                        row_data = [col.text.strip() for col in columns]
                        print(f"Row data: {row_data}")
                        # You can further process the row_data as needed
                        # fix bug where place is 0
                        if row_data[0] == 0:
                            race_place = '999'
                        else:
                            race_place = row_data[0]

                        new_result = {
                            'race_code': "au" + event_code.lower() + my_class.lower() + eventRaceId.lower(),
                            'place': race_place,
                            'athlete_name': row_data[1],
                            'club': row_data[2],
                            'race_time': row_data[3],  
                            'race_points': 0
                        }
                        new_results.append(new_result)

            else:
                print("tbody not found in resultList table")
        else:
            print("resultList table not found")
            

    else:
        print("individualResultList not found")


    return new_events, new_results




def scrape_events_from_eventor(end_date, days_prior):
    print("Started scrape_events_from_eventor:", datetime.now())

    # Define the start date for scraping
    start_date = end_date - timedelta(days=days_prior)

    driver = setup_Chrome_driver()
    new_events = []
    races = []

    # scrape recent events from Eventor
    # get the event page
    events_url = f"https://eventor.orienteering.asn.au/Events?competitionTypes=level1%2Clevel2%2Clevel3&classifications=National%2CChampionship%2CRegional%2CLocal&disciplines=Foot&startDate={ start_date }&endDate={ end_date }&map=false&mode=List&showMyEvents=false&cancelled=false&isExpanded=true"
    #events_url = f"https://eventor.orienteering.asn.au/Events?competitionTypes=level1%2Clevel2&classifications=National%2CChampionship%2CRegional&disciplines=Foot&startDate={ start_date }&endDate={ end_date }&map=false&mode=List&showMyEvents=false&cancelled=false&isExpanded=true"

    full_page_source = get_html_from_url(events_url, driver)
    
    # Now you can use BeautifulSoup to parse the HTML content
    soup = BeautifulSoup(full_page_source, 'html.parser')


    # Find the element <div id="eventList">
    event_list = soup.find(id="eventList")
    if event_list:
        table_body = event_list.find('tbody')
        rows = table_body.find_all('tr')
        for row in rows:

            event_date = ''
            long_desc = ''
            event_code = ''
            results_href = ''

            # Extract data from each row as needed
            columns = row.find_all('td')
            if columns:

                # Extract the value of span data_date= in column 0
                date_span = columns[0].find('span', {'data-date': True})
                if date_span:
                    event_date = date_span['data-date']
                else:
                    event_date = columns[0].text.strip()

                long_desc = columns[1].text.strip()

                # Extract the event code from the href attribute in the <a> tag in column 1
                event_link = columns[1].find('a', href=True)
                if event_link:
                    event_code = event_link['href'].split('/')[-1]
                else:
                    event_code = 'unknown'

                # Find the column with class "icons"
                icons_column = row.find('td', class_='icons')
                if icons_column:
                    results_img = icons_column.find('img', alt="Results")
                    if results_img:
                        # Get the href text from the parent <a> tag
                        parent_a_tag = results_img.find_parent('a', href=True)
                        if parent_a_tag:
                            results_href = parent_a_tag['href']

                event_discipline = columns[5].text.strip()
                event_classification = columns[6].text.strip()
                event_format = columns[7].text.strip()
                event_distance = columns[8].text.strip()

            # You can further process the row_data as needed
            event = {
                'event_date': event_date,
                'long_desc': long_desc,
                'short_desc': event_code,
                'results_href': results_href,            
                'event_discipline': event_discipline,
                'event_classification': event_classification,
                'event_format': event_format,
                'event_distance': event_distance
            }
            include_event = filter_event(event)
            if include_event:
                new_events.append(event)

        for event in new_events:
            # search eventor for eligible classes
            stages = []
            event_url = f"https://eventor.orienteering.asn.au{event['results_href']}"
    
            event_full_page_source = get_html_from_url(event_url, driver)
    
            # Now you can use BeautifulSoup to parse the HTML content
            event_soup = BeautifulSoup(event_full_page_source, 'html.parser')

            # check for a multi-day event
            dummy_tag = event_soup.find('p', class_='toolbar16 printHidden')
            multi_day_tag = dummy_tag.find_next_sibling('p', class_='toolbar16')
            if multi_day_tag:
                print("Multi-day event")
                # get the details of each stage
                stage_tags = multi_day_tag.find_all('a')
                for link in stage_tags:
                    stage_name = link.text.strip()
                    stage_href = link['href']
                    stages.append({'stage_name': stage_name, 'stage_href': stage_href})
            else:
                print("Single day event")
                stages.append({'stage_name': '', 'stage_href': None})

            # Find the classes for an event
            filters_tag = event_soup.find('p', class_='filters')
            if filters_tag:
                my_classes = []
                class_links = filters_tag.find_all('a')
                for link in class_links:
                    href_tag = link['href']
                    eventClassId = href_tag.split('&eventClassId=')[1].split('&')[0]
                    eventRaceId = href_tag.split('&eventRaceId=')[1].split('&')[0]
                    class_name = link.text.strip()  # class name from the filters panel
                    my_classes.append({'class_name': class_name, 'href_tag': href_tag, 'eventClassId': eventClassId, 'eventRaceId': eventRaceId})

                print(f"Classes found: {my_classes}")

                event['classes'] = filter_classes(my_classes)

                for stage in stages:
                    for race_class in event['classes']:
                        # event['classes'] is a list of my_class dictionaries

                        if stage['stage_href']:
                            results_link = stage['stage_href']
                            stageRaceId = stage['stage_href'].split('&eventRaceId=')[1].split('&')[0]
                        else:
                            results_link = race_class['href_tag']
                            stageRaceId = race_class['eventRaceId']

                        # this doesn't work when class_name is used inconsistently within some events e.g. W20A in the filters, but W17-20A in the results
                        # this could be solved by gathering the class name from the results for each class instead of the filters panel, but I have left it for now
                        race_code = "au" + event['short_desc'].lower() + race_class['class_name'].lower() + stageRaceId.lower()
                        # check to see if race has already been uploaded
                        race_exists = test_race_exist(race_code)

                        new_race = {
                            'event_date': event['event_date'],
                            'long_desc': event['long_desc'] + " " + stage['stage_name'],
                            'short_desc': event['short_desc'],
                            'results_href': results_link,            
                            'event_discipline': event['event_discipline'],
                            'event_classification': event['event_classification'],
                            'event_format': event['event_format'],
                            'event_distance': event['event_distance'],
                            'event_class': race_class['class_name'],
                            'event_exists': race_exists,
                            'stage_name': stage['stage_name'],
                            'eventClassId': race_class['eventClassId'],
                            'eventRaceId': stageRaceId
                        }
                        if new_race:
                            races.append(new_race)
            else:
                print("Classes <p> tag not found")
    else:
        print("eventList element not found")

    driver.quit()
    print("Finished scrape_events_from_eventor:", datetime.now())   
    print(f"{races=}")
    return races