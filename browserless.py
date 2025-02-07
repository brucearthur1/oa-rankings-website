from selenium import webdriver
from bs4 import BeautifulSoup
import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select



r_url = "https://ranking.orienteering.org/Calendar/"
TOKEN = "Rj8w0zg4AOMwlz47aae56c970af02cdccf56ff5bb7"
#b_url = f"https://production-sfo.browserless.io/content?token={TOKEN}"
browserless_url = 'https://chrome.browserless.io/webdriver'



def browserless_selenium():
    # Step 1: Set up Browserless.io connection
    # Selenium 4
    chrome_options = webdriver.ChromeOptions()
    chrome_options.set_capability('browserless:token', TOKEN)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")

    driver = webdriver.Remote(
        command_executor=browserless_url,
        options=chrome_options
    )

    driver.get(r_url)
    print(driver.title)
    
    year = '2019'
    print(f"Searching: {year}")
    # Find the dropdown element
    select_element = driver.find_element(By.ID, "MainContent_ddlSelectYear")

    # Create a Select object
    select = Select(select_element)
    # Select an option by value
    select.select_by_value(year)

    # Optionally, wait for the page to load the new content (adjust the sleep time as needed)
    time.sleep(2)

    # Get the updated page source
    updated_html = driver.page_source

    # Parse the updated HTML with BeautifulSoup
    soup = BeautifulSoup(updated_html, 'html.parser')
    print(soup.title.string)

    gvCalendar = soup.find('table', id='MainContent_gvCalendar')
    if gvCalendar:
        rows = gvCalendar.find_all('tr')
        for row in rows:
            # Check if the row contains any <th> elements
            if row.find_all('th'):
                continue  # Skip rows with <th> elements
            
            # Process rows with <td> elements            event_date = row.find_all('td')[0].get_text()
            event_date_str = row.find_all('td')[0].get_text()
            print(event_date_str)
        
    else:
        print(f"Table of events not found: ")




    driver.quit()