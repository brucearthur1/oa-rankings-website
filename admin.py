from datetime import datetime
from excel import import_events_from_excel, add_multiple_races_for_list_year
from pytz import timezone
from database import confirm_discipline
from rankings import recalibrate
from background import upload_year_WRE_races

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
    recalibrate(last_day_of_year, 1)


    print(f"finished import_year {year} at: {datetime.now(sydney_tz)}")
    return df_html