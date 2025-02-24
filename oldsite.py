from scraping import setup_Chrome_driver
from datetime import date, datetime, timedelta
from database import load_event_from_db, store_race_tmp, confirm_discipline, delete_from_results, delete_from_event_stats 
from rankings import calculate_race_rankings
import time

from bs4 import BeautifulSoup


def load_from_old_site(my_year, driver):
    print(f"starting load_from_old_site")
    # get the event page
    event_url = f"https://rankings.orienteering.asn.au/{my_year}/men.htm"

    new_results = []
    new_events = []

    print('Open browser for', event_url)
    page = ''
    timer = 0
    while page == '':
        try:
            driver.get(event_url)
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

    # find <font color="#009933">Latest Ranking Events</font>
    row_element = soup.find('font', color="#009933", text="Latest Ranking Events")
    
    # Find the next row with an <a> tag and get the href link
    next_row = row_element.find_next('tr')
    table_element = row_element.find_parent('table')
    while next_row and next_row.find_parent('table') == table_element:
        a_tag = next_row.find('a')
        if a_tag and 'href' in a_tag.attrs:
            href_link = a_tag['href']
            print(f"Found href link: {href_link}")
            if href_link != "http://ranking.orienteering.org":
                # Extract the event code from the href link
                event_code = href_link.split('.htm')[0]
                print(f"Event code: {event_code}")
                # test to see if the event is already loaded
                event, results = load_event_from_db(event_code)
                if event:
                    print(f"Event {event_code} already loaded")
                    print(f"Event details: {event}")
                    event_id = event['id']
                    print(f"Event ID: {event_id}")
                    #print(f"Results: {results}")
                    if results:
                        max_race_points = max(result['race_points'] for result in results)
                        if float(max_race_points) > 790:
                            print(f"Max race points within range: {max_race_points}")
                            next_row = next_row.find_next('tr')
                        else:
                            print(f"Need to recalculate based on max_points = : {max_race_points}")
                            print(f"store results in race_tmp { results }")
                            for result in results:
                                result['place'] = int(result['place'])
                            data_to_insert = [tuple(result.values())[1:5] for result in results]
                            print(f"data_to_insert: {data_to_insert}")
                            
                            store_race_tmp(event_code, data_to_insert)

                            # remove old results from the database
                            delete_from_results(event_code)
                            delete_from_event_stats(event_id)

                            # recalculate the ranking scores
                            calculate_race_rankings(event_code)

                            # get the next row
                            next_row = next_row.find_next('tr')
                    else:
                        print(f"No results found for event {event_code}")
                        # get the next row
                        next_row = False

                else:
                    print(f"Event {event_code} not loaded yet")
                    # Process the event page to extract event details and results
                    # new_events, new_results = get_event_from_old_site(event_code, driver)
                    # these new_events and new_results will be returned to the calling function
                
                    # end testing here
                    next_row = False
            else:
                print("Skipping the link to the ranking.orienteering.org site")
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


    # result_list = soup.find(class_="individualResultList")
    # if result_list:
    #     print("Found individualResultList")
    #     # get the event details
    #     # Look for <h2> tags containing "Official results for "
    #     name_tag = result_list.find('h2', text=lambda x: x and 'Official results for ' in x)
    #     if name_tag:
    #         event_name = name_tag.text.split('Official results for ')[1].strip()
    #         print(f"Event name from <h2>: {event_name}")

    #         # Find the <p> tag after the specified <p> tag
    #         toolbar_tag = result_list.find('p', class_='toolbar16 printHidden')
    #         if toolbar_tag:
    #             next_p_tag = toolbar_tag.find_next_sibling('p')
    #             if next_p_tag:
    #                 print(f"Next <p> tag content: {next_p_tag.text}")
                    
    #                 if 'Date: ' in next_p_tag.text:
    #                     event_date_str = next_p_tag.text.split('Date: ')[1].strip()
    #                     print(f"Event date: {event_date_str}")

    #                     my_list_name = deduct_list_name_from_class_name(my_class)

    #                     # Convert event_date_str to "YYYY-MM-DD" format
    #                     event_date = datetime.strptime(event_date_str, '%A %d %B %Y').strftime('%d/%m/%Y')
    #                     new_event = {
    #                         'date': event_date,
    #                         'short_desc': "au" + event_code + my_class,
    #                         'long_desc': event_name,
    #                         'class': my_class,
    #                         'short_file': "au" + event_code + my_class,
    #                         'ip': 1,
    #                         'list': my_list_name,
    #                         'eventor_id': event_code,
    #                         'iof_id': None,
    #                         'discipline': 'Middle/Long'
    #                     }
    #                     new_events.append(new_event)


    #             else:
    #                 print("Next <p> tag not found")
    #         else:
    #             print("Toolbar <p> tag not found")
    #     else:
    #         print("Name not found")


    #     # get results for the specified class
    #     # Find the element with class "eventClassHeader" and <h3> text = my_class
    #     class_header = result_list.find('h3', text=my_class)
    #     if class_header:
    #         print(f"Found class header: {class_header.text}")

    #         # Find the table with class "resultList"
    #         result_table = result_list.find('table', class_='resultList')
    #         if result_table:
    #             print("Found resultList table")
    #             # Extract the <tbody> from the table
    #             tbody = result_table.find('tbody')
    #             if tbody:
    #                 print("Found tbody in resultList table")
    #                 # Process the rows in the tbody
    #                 rows = tbody.find_all('tr')
    #                 for row in rows:
    #                     # Extract data from each row as needed
    #                     columns = row.find_all('td')
    #                     if columns:
    #                         # Example: Extracting text from each column
    #                         row_data = [col.text.strip() for col in columns]
    #                         print(f"Row data: {row_data}")
    #                         # You can further process the row_data as needed
    #                         new_result = {
    #                             'race_code': "au" + event_code + my_class,
    #                             'place': row_data[0],
    #                             'athlete_name': row_data[1],
    #                             'club': row_data[2],
    #                             'race_time': row_data[3],  
    #                             'race_points': 0
    #                         }
    #                         new_results.append(new_result)

    #             else:
    #                 print("tbody not found in resultList table")
    #         else:
    #             print("resultList table not found")
            
    #     else:
    #         print(f"Class header with text '{my_class}' not found")

    # else:
    #     print("individualResultList not found")


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

