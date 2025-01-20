from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from bs4 import BeautifulSoup


def load_from_WRE(input):
    print(input)
    
    # Set up Chrome options to run in headless mode
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')

    # Initialize the Chrome WebDriver
    driver = webdriver.Chrome(options=chrome_options)
    
    url = "https://ranking.orienteering.org/ResultsView?event=" + input['IOF_event_id'] + "&"

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
    time.sleep(2)

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
        event_ip = event_details.find('span', id='MainContent_dvEventDetails_Label8').get_text()
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
                        'race_code': "wrm" + input['IOF_event_id'],
                        'place': place,
                        'athlete_name': athlete_name,
                        'race_time': race_time,
                        'race_points': race_points
                    }
                    new_results.append(new_result)
        if result_m > 0:

            new_event = {
                'date': event_date,
                'short_desc': "wrm" + input['IOF_event_id'],
                'long_desc': event_name,
                'class': "Men",
                'short_file': "WRE",
                'map_link': None,
                'graph': None,
                'ip': event_ip,
                'list': 'men',
                'eventor_id': None,
                'iof_id': input['IOF_event_id']
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
                        'race_code': "wrw" + input['IOF_event_id'],
                        'place': place,
                        'athlete_name': athlete_name,
                        'race_time': race_time,
                        'race_points': race_points
                    }
                    new_results.append(new_result)
        if result_w > 0:
            new_event = {
                'date': event_date,
                'short_desc': "wrw" + input['IOF_event_id'],
                'long_desc': event_name,
                'class': "Women",
                'short_file': "WRE",
                'map_link': None,
                'graph': None,
                'ip': event_ip,
                'list': 'women',
                'eventor_id': None,
                'iof_id': input['IOF_event_id']
            }
            new_events.append(new_event)
    else:
        print('panel2 not found')

    # Close the WebDriver
    driver.quit()
    print('Close browser for', url)
    time.sleep(1)
    
    return new_events, new_results
