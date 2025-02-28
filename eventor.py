from scraping import setup_Chrome_driver
from datetime import date, datetime, timedelta
import time

from bs4 import BeautifulSoup


def deduct_list_name_from_class_name(my_class):
    pre_my_list_name = ""
    if "18" in my_class or "20" in my_class or "senior" in my_class.lower():
        pre_my_list_name = "junior "
    if my_class.startswith("W"):
        post_my_list_name = "women"
    else:
        post_my_list_name = "men"
    my_list_name = pre_my_list_name + post_my_list_name

    return my_list_name



            # event = {
            #     'event_date': event_date,
            #     'long_desc': long_desc,
            #     'short_desc': event_code,
            #     'results_href': results_href,            
            #     'event_discipline': event_discipline,
            #     'event_classification': event_classification,
            #     'event_format': event_format,
            #     'event_distance': event_distance
            # }


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




def load_from_eventor(event_code, my_class, driver):
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
                            'short_desc': "au" + event_code + my_class,
                            'long_desc': event_name,
                            'class': my_class,
                            'short_file': "au" + event_code + my_class,
                            'ip': 1,
                            'list': my_list_name,
                            'eventor_id': event_code,
                            'iof_id': None,
                            'discipline': 'Middle/Long'
                        }
                        new_events.append(new_event)


                else:
                    print("Next <p> tag not found")
            else:
                print("Toolbar <p> tag not found")
        else:
            print("Name not found")


        # get results for the specified class
        # Find the element with class "eventClassHeader" and <h3> text = my_class
        class_header = result_list.find('h3', text=my_class)
        if class_header:
            print(f"Found class header: {class_header.text}")

            # Find the table with class "resultList"
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




def load_race_from_eventor(input, driver):
    print(f"starting load_race_from_eventor")

    # for each event, retrieve the new_events and new_results by scraping the web page
    new_events = []
    new_results = []

    event_code = input['eventor_race_id']
    my_class = input['class']
    print(f"event_code: {event_code}")
    print(f"my_class: {my_class}")

    events, results = load_from_eventor(event_code, my_class, driver)
    
    for event in events:
        new_events.append(event)
    for result in results:
        new_results.append(result)


    return new_events, new_results



def scrape_events_from_eventor(end_date, days_prior):
    print("Started scrape_events_from_eventor:", datetime.now())

    # Define the start date for scraping
    start_date = end_date - timedelta(days=days_prior)

    driver = setup_Chrome_driver()
    new_events = []

    # scrape recent events from Eventor
    # get the event page
    events_url = f"https://eventor.orienteering.asn.au/Events?competitionTypes=level1%2Clevel2&classifications=National%2CChampionship%2CRegional&disciplines=Foot&startDate={ start_date }&endDate={ end_date }&map=false&mode=List&showMyEvents=false&cancelled=false&isExpanded=true"
    print(f"{events_url=}")
    
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
    else:
        print("eventList element not found")


    driver.quit()
    print("Finished scrape_events_from_eventor:", datetime.now())   

    return new_events