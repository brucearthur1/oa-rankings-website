from datetime import datetime
from excel import import_events_from_excel, add_multiple_races_for_list_year
from pytz import timezone
from database import confirm_discipline, update_athletes_with_iof_ids, load_athletes_with_iof_id, update_athlete_photo
from rankings import recalibrate
from background import upload_year_WRE_races
from scraping import scrape_iof_athlete_search
import requests
import os

sydney_tz = timezone('Australia/Sydney')


def import_year(year):
    print(f"starting import_year {year} at: {datetime.now(sydney_tz)}")

    # import WRE for year
    print(f"Starting year_WRE_upload(): {year} ", datetime.now(sydney_tz))
    year_obj = {}
    year_obj['year'] = str(year)
    upload_year_WRE_races(year_obj)
    
    print("Finished year_WRE_upload():", datetime.now(sydney_tz))
    

    input = {}
    input['start'] = 2
    input['finish'] = 300
    input['path_file'] = "s:\\rankings\\source\\" + str(year) + "\\races.xls"
    input['sheet'] = "races"

    print(input)

    # import AUS events from Excel
    # call import_events_from_excel
    df_html = import_events_from_excel(input)
    print(df_html)
    
    # import AUS results from Excel for each list
    ranking_lists = ['men', 'women', 'junior men', 'junior women']

    for item in ranking_lists:
        input = {}
        if item == 'junior men':
            myfile = 'boys'
        elif item == 'junior women':
            myfile = 'girls'
        else:
            myfile = item
        input['path_file'] = "s:\\rankings\\source\\" + str(year) + "\\" + myfile + ".xls"
        input['list'] = item
        add_multiple_races_for_list_year(input)

    # Remember to review Discipline  (discipline = 'Middle/Long' by default)
    confirm_discipline(year)

    # recalibrate AUS events for the year
    last_day_of_year = datetime(year, 12, 31).date()
    for item in ranking_lists:
        recalibrate(last_day_of_year, item, 1)


    print(f"finished import_year {year} at: {datetime.now(sydney_tz)}")
    return df_html


def scrape_and_update_athletes_with_iof_ids():
    print(f"starting update_athletes_with_iof_ids at: {datetime.now(sydney_tz)}")

    # Iterate through every character in the alphabet
#    for next_character in 'abcdefghijklmnopqrstuvwxyz':
    for next_character in 'mnopqrstuvwxyz':
        # read IOF eventor athlete search page
        athletes = scrape_iof_athlete_search(my_char=next_character)
        print(f"Finished scraping from IOF site for character {next_character}:", datetime.now(sydney_tz))
        # store athletes
        update_athletes_with_iof_ids(athletes)
        print(f"Finished updating athletes with IOF IDs for character {next_character}:", datetime.now(sydney_tz))

    print(f"finished update_athletes_with_iof_ids at: {datetime.now(sydney_tz)}")


def check_for_iof_photo():
    print(f"starting check_for_iof_photo at: {datetime.now(sydney_tz)}")

    # load athletes from db where IOF ID is not null and photo is N
    athletes = load_athletes_with_iof_id()
    print(f"Finished loading athletes with IOF IDs and no photo:", datetime.now(sydney_tz))
    # iterate through athletes
    for athlete in athletes:
        # check if photo exists
        athlete_id = athlete['iof_id']
        #try to open photos/athlete_id.jpg
        photo_path = f"static/{athlete_id}.jpeg"
        if os.path.exists(photo_path):
            update_athlete_photo(athlete_id)
            print(f"Local photo exists for athlete {athlete['full_name']}")
        else:
            print(f"Photo does not exist locally for athlete {athlete['full_name']}")

            # update_athlete_photo(athlete_id)
            # print(f"photo removed for athlete {athlete['full_name']}")

        #try to open IOF photos /athlete_id
        # try:
        #     response = requests.head(f"https://eventor.orienteering.sport/MyPages/ProfilePhoto/9440", timeout=10)
        #     if response.status_code == 200:
        #         print(f"URL exists for athlete {athlete['full_name']}")
        #     resp = requests.get(f"https://eventor.orienteering.sport/MyPages/ProfilePhoto/{athlete_id}", timeout=10, stream=True)
        #     if resp.status_code == 200 and resp.headers.get('Content-Type', '').startswith('image'):
        #         update_athlete_photo(athlete_id)
        #         print(f"IOF photo exists for athlete {athlete['full_name']}")
        #         continue
        #     else:
        #         print(f"IOF Photo not accessible for athlete {athlete['full_name']} (status {resp.status_code})")
        # except requests.RequestException as e:
        #     print(f"IOF Photo request failed for athlete {athlete['full_name']}: {e}")
