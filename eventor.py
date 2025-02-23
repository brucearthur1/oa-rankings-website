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



def load_from_eventor(event_code, my_class, driver):
    print(f"starting load_from_eventor")
    # get the event page
    event_url = f"https://eventor.orienteering.asn.au/Events/ResultList?eventId={event_code}"

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
    # get current date
    #current_date = date.today()
    #print(f"Today's date is: {current_date}")

    # get latest event date from WREs in events table
    #latest_date_str = get_latest_WRE_date()
    
    # Convert the date strings to datetime objects
    #latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d').date()

    # set latest date to current date minus 14 days
    #latest_date = current_date - timedelta(days=14)


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

