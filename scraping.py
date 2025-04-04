from selenium import webdriver
from datetime import date, datetime, timedelta
import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
#from database import get_latest_WRE_date
import os


def setup_Chrome_driver():
    TOKEN = os.getenv('BROWSERLESS_TOKEN')
    browserless_url = "https://chrome.browserless.io/webdriver"

    if os.getenv('VERCEL_ENV'):
        # Set up Browserless.io connection
        chrome_options = webdriver.ChromeOptions()
        chrome_options.set_capability('browserless:token', TOKEN)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless")

        driver = webdriver.Remote(
            command_executor=browserless_url,
            options=chrome_options
        )
    else:
        # original setting without Browserless.io
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')

        # Initialize the Chrome WebDriver
        driver = webdriver.Chrome(options=chrome_options)
        

    return driver



def load_from_WRE(input, driver):
    print(input['event_id'])
    #print(type(input))
    
    #driver = setup_Chrome_driver()
    
    url = "https://ranking.orienteering.org/ResultsView?event=" + input['event_id'] + "&"

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
    full_page_source = driver.page_source
    
    # Now you can use BeautifulSoup to parse the HTML content
    soup = BeautifulSoup(full_page_source, 'html.parser')

    new_events = []

    event_details = soup.find('table', id='MainContent_dvEventDetails')
    if event_details:
        rows = event_details.find_all('tr')
        event_name = rows[0].find_all('td')[1].get_text()
        event_date = rows[1].find_all('td')[1].get_text()
        ip_tag = event_details.find('span', id='MainContent_dvEventDetails_Label8')
        if ip_tag:
            event_ip = ip_tag.get_text()    
        else:
            event_ip = '1'
    else:
        print('Event Details not found')

    new_results = []
    result_m = 0
    result_w = 0

    panel1 = soup.find('div', id='panel1')
    if panel1:
        rows = panel1.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if cells:
                federation = cells[2].get_text()
                if federation == 'AUS':
                    result_m += 1
                    place = cells[0].get_text()
                    athlete_name = cells[1].get_text()
                    race_time = cells[3].get_text()
                    race_points = cells[4].get_text()
                    new_result = {
                        'race_code': "wrm" + input['event_id'],
                        'place': place,
                        'athlete_name': athlete_name,
                        'race_time': race_time,
                        'race_points': race_points
                    }
                    new_results.append(new_result)
        if result_m > 0:

            new_event = {
                'date': event_date,
                'short_desc': "wrm" + input['event_id'],
                'long_desc': event_name,
                'class': "Men",
                'short_file': "WRE",
                'ip': event_ip,
                'list': 'men',
                'eventor_id': None,
                'iof_id': "" + input['event_id'],
                'discipline': input['discipline']
            }
            new_events.append(new_event)
    else:
        print('panel1 not found')

    panel2 = soup.find('div', id='panel2')
    if panel2:
        wrows = panel2.find_all('tr')
        for wrow in wrows:
            wcells = wrow.find_all('td')
            if wcells:
                federation = wcells[2].get_text()
                if federation == 'AUS':
                    result_w += 1
                    place = wcells[0].get_text()
                    athlete_name = wcells[1].get_text()
                    race_time = wcells[3].get_text()
                    race_points = wcells[4].get_text()
                    new_result = {
                        'race_code': "wrw" + input['event_id'],
                        'place': place,
                        'athlete_name': athlete_name,
                        'race_time': race_time,
                        'race_points': race_points
                    }
                    new_results.append(new_result)
        if result_w > 0:
            new_event = {
                'date': event_date,
                'short_desc': "wrw" + input['event_id'],
                'long_desc': event_name,
                'class': "Women",
                'short_file': "WRE",
                'ip': event_ip,
                'list': 'women',
                'eventor_id': None,
                'iof_id': input['event_id'],
                'discipline': input['discipline']
            }
            new_events.append(new_event)
    else:
        print('panel2 not found')

    # Close the WebDriver
    #driver.quit()
    print('Close browser for', url)
    #time.sleep(1)
    
    return new_events, new_results


def get_event_ids(current_date, latest_date, driver):
    # get event ids with results between last date and current date
    print(f"Get IOF EventIDs between {latest_date} and {current_date}")

    # Set up the Chrome driver
    #service = Service(ChromeDriverManager().install())
    #options = webdriver.ChromeOptions()
    #options.add_argument("--headless")
    #driver = webdriver.Chrome(service=service, options=options)
    #driver = setup_Chrome_driver()

    url = "https://ranking.orienteering.org/Calendar/"

    # Load the webpage
    driver.get(url)  # Replace with the path to your HTML file

    new_events = []

    #current_date = datetime.strptime(current_date_str, '%Y-%m-%d')

    # Get the year from the datetime object
    current_year = current_date.year
    latest_year = latest_date.year
    years = []

    if latest_year <= current_year:
        for year in range(latest_year, current_year + 1):
            years.append(str(year))


    options = ['F','FS']

    for year in years:
        print(f"Searching: {year}")
        # Find the dropdown element
        select_element = driver.find_element(By.ID, "year")

        # Create a Select object
        select = Select(select_element)

        # Select an option by value
        select.select_by_value(year)

        # Optionally, wait for the page to load the new content (adjust the sleep time as needed)
        time.sleep(1)

        for option in options:
            print(f"Searching: {option}")
            # Find the dropdown element
            select_element = driver.find_element(By.ID, "discipline")

            # Create a Select object
            select = Select(select_element)

            # Select an option by value
            select.select_by_value(option)

            # Optionally, wait for the page to load the new content (adjust the sleep time as needed)
            time.sleep(1)

            # Get the updated page source
            updated_html = driver.page_source

            # Parse the updated HTML with BeautifulSoup
            soup = BeautifulSoup(updated_html, 'html.parser')


            gvCalendar = soup.find('table', id='MainContent_gvCalendar')
            if gvCalendar:
                rows = gvCalendar.find_all('tr')
                for row in rows:
                    # Check if the row contains any <th> elements
                    if row.find_all('th'):
                        continue  # Skip rows with <th> elements
                    
                    # Process rows with <td> elements            event_date = row.find_all('td')[0].get_text()
                    event_date_str = row.find_all('td')[0].get_text()
                    event_date = datetime.strptime(event_date_str, '%d/%m/%Y').date()

                    # Check if event_date is between latest_date and current_date
                    if latest_date < event_date <= current_date:
                        event_name = row.find_all('td')[2].get_text()

                        # Use a regular expression to find the img tag with id starting with 'MainContent_gvCalendar_Image2'
                        img_tag = row.find('img', id=re.compile(r'^MainContent_gvCalendar_Image2'))
                        # Initialize the completed variable
                        completed = False
                        # Check the src attribute
                        if img_tag and img_tag.get('src') == "../Content/Check.png":

                            # if the WRE is in Australia, don't import this WRE
                            td_element = row.find_all('td')[1]
                            # Find the <span> element with class 'flag-hint'
                            flag_hint_span = td_element.find('span', class_='flag-hint')
                            # Extract the text 'AUS' from the flag-hint span
                            event_country = flag_hint_span.get_text(strip=True)

                            if event_country != 'AUS':
                                print(event_date)
                                print(event_name)
                                completed = True
                                # Extract the <a> tag
                                a_tag = row.find_all('td')[2].find('a')

                                # Get the href attribute
                                href_text = a_tag.get('href')
                                print(href_text)

                                # Use a regular expression to extract the event ID
                                match = re.search(r'event=(\d+)', href_text)
                                if match:
                                    event = {}
                                    event['event_id'] = match.group(1)
                                    print(event['event_id'])
                                    if option == 'F':
                                        event['discipline'] = 'Middle/Long'
                                    elif option == 'FS':
                                        event['discipline'] = 'Sprint'
                                    new_events.append(event)
                                else:
                                    print("Event ID not found")

                        print(f"Has WRE scores: {completed}")
                    else:
                        print("The event_date is not between latest_date and current_date.")
                
            else:
                print(f"Table of events not found: {option}")

    # Close the browser
    #driver.quit()

    return new_events


def load_latest_from_WRE():
    # get current date
    current_date = date.today()
    #print(f"Today's date is: {current_date}")

    # get latest event date from WREs in events table
    #latest_date_str = get_latest_WRE_date()
    
    # Convert the date strings to datetime objects
    #latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d').date()

    # set latest date to current date minus 7 days
    latest_date = current_date - timedelta(days=7)

    driver = setup_Chrome_driver()

    # get event ids with results between last date and current date
    events_codes = get_event_ids(current_date, latest_date, driver)
    print(events_codes)

    # for each event, retrieve the new_events and new_results by scraping the web page
    new_events = []
    new_results = []

    for event_code in events_codes:
        
        
        events, results = load_from_WRE(event_code, driver)
        for event in events:
            new_events.append(event)
        for result in results:
            new_results.append(result)

    # Close the WebDriver
    driver.quit()

    return new_events, new_results





def load_year_from_WRE(year):
    year_int = int(year['year'])

    # Define the start and end dates for the given year
    start_date = date(year_int, 1, 1)
    end_date = date(year_int, 12, 31)

    driver = setup_Chrome_driver()

    # get event ids with results between last date and current date
    event_codes = get_event_ids(end_date, start_date, driver)
    print(event_codes)

    # for each event, retrieve the new_events and new_results by scraping the web page
    new_events = []
    new_results = []



    for event_code in event_codes:
        events, results = load_from_WRE(event_code, driver)
        for event in events:
            new_events.append(event)
        for result in results:
            new_results.append(result)

    # Close the WebDriver
    driver.quit()

    return new_events, new_results


def scrape_iof_athlete_search(my_char=''):
    driver = setup_Chrome_driver()
    url = "https://eventor.orienteering.org/Athletes"
    print('\033[94m' + 'Open browser for ' + url + '\033[0m')
    # Load the webpage
    driver.get(url)
    time.sleep(2)
    # Get the full page source including data loaded by JavaScript
    full_page_source = driver.page_source
    print('\033[94m' + f"{full_page_source=}" + '\033[0m')
    
    # Now you can use BeautifulSoup to parse the HTML content
    soup = BeautifulSoup(full_page_source, 'html.parser')
    
    # Find the search form and fill in the search criteria
    search_form_div = driver.find_element(By.ID, "search_athlete")
    if search_form_div:
        search_form = search_form_div.find_element(By.TAG_NAME, "form")
        # Find the input field for the search query
        try:
            search_gender = search_form.find_element(By.ID, "PersonSex")
            # Enter the search query (e.g., "AUS")
            search_gender.send_keys("Female")
            
            search_lastname = search_form.find_element(By.ID, "LastName")
            # Enter the search query (e.g., "AUS")
            search_lastname.send_keys(my_char)

            search_nationality = search_form.find_element(By.ID, "CountryId")
            # Enter the search query (e.g., "AUS")
            search_nationality.send_keys("Australia")
            
            search_volume = search_form.find_element(By.ID, "MaxNumberOfResults")
            # Enter the search query (e.g., "AUS")
            search_volume.send_keys(500)
        except Exception as e:
            print(f"Search input not found: {e}")
            # Enter the search query (e.g., "AUS")
        else:
            print("Search input not found")


    # Find the search form and click the search button
    search_button = driver.find_element(By.ID, "Search")
    if search_button:
        search_button.click()
    else:
        print("Search button not found")
    time.sleep(2)

    # Get the updated page source
    updated_html = driver.page_source
    # Parse the updated HTML with BeautifulSoup
    soup = BeautifulSoup(updated_html, 'html.parser')

    athletes = []
    # Find the table with athlete information
    div = soup.find('div', id='athleteList')
    if div:
        print
        # Find the table with athlete information
        table = div.find('table')

        if table:
            rows = table.find_all('tr')
            for row in rows:
                # Check if the row contains any <th> elements
                if row.find_all('th'):
                    continue  # Skip rows with <th> elements
                # Process rows with <td> elements
                cells = row.find_all('td')
                if cells:
                    athlete = {}
                    athlete['iof_id'] = cells[0].get_text(strip=True)
                    athlete['full_name'] = cells[1].get_text(strip=True)
                    athlete['eventor_id'] = cells[2].get_text(strip=True)
                    athlete['nationality'] = cells[3].get_text(strip=True)
                    athlete['discipline'] = cells[4].get_text(strip=True)
                    athletes.append(athlete)
        else:
            print('\033[94m' + 'Athlete table not found' + '\033[0m')
    else:
        print('\033[94m' + 'Athlete list not found' + '\033[0m')

    print(f"Found {len(athletes)} athletes")
    # Print the athletes
    for athlete in athletes:
        print(athlete)


    # close the driver
    driver.quit()

    return athletes
    