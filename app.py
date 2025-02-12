import os
from flask import Flask, render_template, send_from_directory, jsonify, request
from database import load_athletes_from_db, load_athlete_from_db, update_to_athlete_db, store_race_from_excel, store_events_from_excel, load_events_from_db, load_event_from_db, store_clubs_in_db, store_athletes_in_db, insert_athlete_db, load_athletes_from_results, load_results_by_athlete, load_rankings_from_db, load_results_for_all_athletes, store_race_tmp_from_excel, load_event_stats, load_unmatched_athletes
from excel import load_from_xls, load_from_xlsx, load_multiple_from_xlsx, import_events_from_excel, add_multiple_races_for_list_year
from datetime import datetime, timedelta, timezone
from formatting import convert_to_time_format, is_valid_time_format
from xml_util import load_clubs_from_xml, load_athletes_from_xml
from collections import defaultdict
from threading import Thread
from background import process_and_store_data, process_latest_WRE_races, upload_year_WRE_races
from pytz import timezone
from browserless import browserless_selenium
from rankings import calculate_race_rankings, recalibrate_year
from admin import import_year



app = Flask(__name__)

# Ensure Sydney timezone is used
sydney_tz = timezone('Australia/Sydney')

@app.template_filter('strftime') 
def _jinja2_filter_datetime(date, fmt=None): 
    return date.strftime(fmt) if fmt else date.strftime('%d/%m/%Y')

# Define the custom filter
def _jinja2_filter_seconds_to_time(seconds):
    """Convert seconds to HH:MM:SS format."""
    return str(timedelta(seconds=seconds))

# Register the custom filter with Jinja2
app.jinja_env.filters['_jinja2_filter_seconds_to_time'] = _jinja2_filter_seconds_to_time

app.jinja_env.filters['_jinja2_filter_datetime'] = _jinja2_filter_datetime

app.jinja_env.filters['is_valid_time_format'] = is_valid_time_format


#home page for Rankings
@app.route('/')
def index():
    athletes = load_rankings_from_db()  # Your function to get athletes
    current_date = datetime.now(sydney_tz).date()
    twelve_months_ago = current_date - timedelta(days=365)

    # Ensure athlete['date'] and athlete['race_points'] are in the correct format
    for athlete in athletes:
        if isinstance(athlete['date'], str):
            athlete['date'] = datetime.strptime(athlete['date'], '%Y-%m-%d').date()
        athlete['race_points'] = float(athlete['race_points'])
        athlete['athlete_id'] = str(athlete['athlete_id'])  # Convert athlete_id to string
        if athlete['list']:
            athlete['list'] = str.lower(athlete['list'])
        else:
            print(f"athlete '{athlete['full_name']}' has no list")
        if athlete['discipline']:
            athlete['discipline'] = str.lower(athlete['discipline'])
        else:
            print(f"athlete '{athlete['full_name']}' has no discipline")

    # Helper function to aggregate athletes based on discipline
    def aggregate_athletes(athletes, discipline=None):
        aggregated_athletes = {}
        for athlete in athletes:
            if athlete['date'] >= twelve_months_ago:
                if discipline is None or athlete['discipline'] == discipline:
                    key = (athlete['full_name'], athlete['club_name'], athlete['state'], athlete['list'], athlete['athlete_id'], athlete['yob'])
                    if key not in aggregated_athletes:
                        aggregated_athletes[key] = []
                    aggregated_athletes[key].append(athlete['race_points'])

        final_aggregated_athletes = []
        for key, points in aggregated_athletes.items():
            points.sort(reverse=True)
            top_5_points = points[:5]
            sum_top_5_points = sum(top_5_points)
            final_aggregated_athletes.append({
                'full_name': key[0],
                'club_name': key[1],
                'state': key[2],
                'list': key[3],
                'athlete_id': key[4],  
                'yob': key[5],
                'sum_top_5_points': sum_top_5_points
            })

        final_aggregated_athletes.sort(key=lambda x: x['sum_top_5_points'], reverse=True)
        return final_aggregated_athletes

    # Aggregating athletes
    final_aggregated_athletes = {
        'all': aggregate_athletes(athletes),
        'sprint': aggregate_athletes(athletes, discipline='sprint'),
        'middle/long': aggregate_athletes(athletes, discipline='middle/long')
    }

    # Get unique lists
    unique_lists = sorted(set(athlete['list'] for athlete in final_aggregated_athletes['all']))

    formatted_date = current_date.strftime('%d %B %Y')
    return render_template('index.html', final_aggregated_athletes=final_aggregated_athletes, unique_lists=unique_lists, current_date=formatted_date)

##############


@app.route("/about")
def about_page():
    return render_template('about.html')

@app.route("/admin")
def admin_page():
    return render_template('admin.html')

@app.route("/admin/athletes")
def admin_athletes():
    unmatched_athletes  = load_unmatched_athletes()
    return render_template('athleteadmin.html', athletes=unmatched_athletes)

@app.route("/admin/import_years")
def admin_import_years():
    return render_template('import_years.html')

@app.route("/admin/import_years_go")
def admin_import_years_go():
    start_year = request.args.get('start')
    end_year = request.args.get('finish')
    if start_year and end_year:
        for year in range(int(start_year), int(end_year) + 1):
            print(year)
            print(type(year))

            import_year(year)


    return render_template('admin.html')


@app.route("/admin/recalibrate")
def admin_recalibrate():
    return render_template('year_recalibrate.html')

@app.route("/admin/recalibrate_year")
def admin_recalibrate_year():
    input = request.args.get('year')
    update = recalibrate_year(input)
    return render_template('update_submitted.html', update=update)    

@app.route("/athlete/add")
def add_athlete():
    full_name = request.args.get('full_name')
    list = request.args.get('list')
    if list:
        if list.lower() in ('men','junior men'):
            gender = 'M'
        elif list.lower() in ('women','junior women'):
            gender = 'F'
        else:
            gender = None
    else:
        gender = None
    # Split the full_name string into parts 
    name_parts = full_name.split(' ') 
    # Extract given_name and family_name 
    given_name = name_parts[0] 
    family_name = ' '.join(name_parts[1:])  # Join remaining parts in case of multiple surnames 
    update = {}
    update['eventor_id'] = None
    update['full_name'] = full_name
    update['given'] = given_name
    update['family'] = family_name
    update['gender'] = gender
    update['yob'] = None
    update['nationality_code'] = 'AUS'
    update['club_id'] = None
    update['eligible'] = 'N'
    insert_athlete_db(update=update)
    return render_template('update_submitted.html', update=update)

# Admin function to mark athlete as ineligible (not Australian)
@app.route("/athlete/ineligible")
def add_ineligible_athlete():
    full_name = request.args.get('full_name')
    list = request.args.get('list')
    if list:
        if list.lower() in ('men','junior men'):
            gender = 'M'
        elif list.lower() in ('women','junior women'):
            gender = 'F'
        else:
            gender = None
    else:
        gender = None
    # Split the full_name string into parts 
    name_parts = full_name.split(' ') 
    # Extract given_name and family_name 
    given_name = name_parts[0] 
    family_name = ' '.join(name_parts[1:])  # Join remaining parts in case of multiple surnames 
    update = {}
    update['eventor_id'] = None
    update['full_name'] = full_name
    update['given'] = given_name
    update['family'] = family_name
    update['gender'] = gender
    update['yob'] = None
    update['nationality_code'] = None
    update['club_id'] = None
    update['eligible'] = 'N'
    insert_athlete_db(update=update)
    return render_template('update_submitted.html', update=update)
    

# Athletes page
@app.route("/athletes")
def athletes_page():
    athletes = load_athletes_from_db()
    return render_template('athletes.html', athletes=athletes)

# test function to view athletes in json format
@app.route("/api/athletes")
def list_athletes():
    athletes = load_athletes_from_db()
    return jsonify(athletes)


# individual Athlete
@app.route("/athlete/<id>")
def show_athlete(id):
    athlete = load_athlete_from_db(id)
    if not athlete:
        return "Not found", 404
    
    results = load_results_by_athlete(full_name=athlete['full_name'])
    
    # Convert data types and format race time
    for result in results:
        if result['race_time']:
            result['race_time'] = convert_to_time_format(result['race_time'])
        
        # Convert dates and points
        if isinstance(result['date'], str):
            result['date'] = datetime.strptime(result['date'], '%Y-%m-%d').date()
        if isinstance(result['race_points'], str):
            result['race_points'] = float(result['race_points'])
        if isinstance(result['list'], str):
            result['list'] = result['list'].lower()
        if isinstance(result['discipline'], str):
            result['discipline'] = result['discipline'].lower()
        if result['place'] is None:
            result['place'] = ""
    
    # Calculate the date range
    current_date = datetime.now(sydney_tz)
    twelve_months_ago = (current_date - timedelta(days=365)).date()
    current_year = current_date.year
    
    # Segment results by list and discipline and filter within the last 12 months
    segmented_results = defaultdict(lambda: defaultdict(list))
    for result in results:
        if result['date'] and result['date'] >= twelve_months_ago:
            segmented_results[result['list']][result['discipline']].append(result)
            segmented_results[result['list']]['all'].append(result)
    
    # Calculate statistics for each segment (list and discipline)
    segmented_stats = defaultdict(lambda: defaultdict(dict))
    for list_name, discipline_results in segmented_results.items():
        for discipline, recent_results in discipline_results.items():
            sorted_recent_results = sorted(recent_results, key=lambda x: x['race_points'], reverse=True)
            top_5_recent_results = sorted_recent_results[:5]
            total_top_5_recent = sum(result['race_points'] for result in top_5_recent_results)
            # Filter out results with race_points <= 0
            positive_results = [result for result in recent_results if result['race_points'] > 0]
            average_recent_points = sum(result['race_points'] for result in positive_results) / len(positive_results) if positive_results else 0
            count_recent_results = len(recent_results)
            
            segmented_stats[list_name][discipline] = {
                'top_5_recent_results': top_5_recent_results,
                'total_top_5_recent': total_top_5_recent,
                'average_recent_points': average_recent_points,
                'count_recent_results': count_recent_results
            }

    # Load results for all athletes to calculate ranking
    all_results = load_results_for_all_athletes()

    # Convert data types for all results and filter within the last 12 months
    all_athlete_stats = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for result in all_results:
        if result['date'] and result['date'] >= twelve_months_ago:
            if isinstance(result['race_points'], str):
                result['race_points'] = float(result['race_points'])
            if isinstance(result['list'], str):
                result['list'] = result['list'].lower()
            if isinstance(result['discipline'], str):
                result['discipline'] = result['discipline'].lower()
            all_athlete_stats[result['full_name']][result['list']][result['discipline']].append(result)
            all_athlete_stats[result['full_name']][result['list']]['all'].append(result)
    
    # Calculate rankings for each athlete within each list and discipline
    rankings = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for athlete_name, athlete_results in all_athlete_stats.items():
        for list_name, discipline_results in athlete_results.items():
            for discipline, recent_results in discipline_results.items():
                if list_name in ["junior men", "junior women"]:
                    athlete_yob = next((result['yob'] for result in recent_results if result.get('yob')), None)
                    if athlete_yob and current_year - athlete_yob >= 21:
                        rankings[athlete_name][list_name][discipline] = "No longer eligible"
                        continue

                sorted_recent_results = sorted(recent_results, key=lambda x: x['race_points'], reverse=True)
                top_5_recent_results = sorted_recent_results[:5]
                total_top_5_recent = sum(result['race_points'] for result in top_5_recent_results)
                rankings[athlete_name][list_name][discipline] = total_top_5_recent
    
    # Determine the rank of the current athlete within each list and discipline
    athlete_ranking = defaultdict(lambda: defaultdict(str))
    for list_name, discipline_stats in segmented_stats.items():
        for discipline in discipline_stats.keys():
            if list_name in ["junior men", "junior women"] and current_year - athlete['yob'] >= 21:
                athlete_ranking[list_name][discipline] = "no longer eligible"
            else:
                sorted_rankings = sorted(
                    [(name, rank_points) for name, rank_points in rankings.items() if isinstance(rank_points[list_name][discipline], (int, float))],
                    key=lambda x: x[1][list_name][discipline], reverse=True
                )
                athlete_ranking[list_name][discipline] = next((rank + 1 for rank, (name, _) in enumerate(sorted_rankings) if name == athlete['full_name']), None)

    return render_template('athletepage.html', athlete=athlete, results=results, segmented_stats=segmented_stats, athlete_ranking=athlete_ranking, datetime=datetime)
###################

# Admin function to allow user to edit athlete name
@app.route("/athlete/<id>/edit")
def edit_athlete(id):
    athlete= load_athlete_from_db(id)
    if not athlete:
        return "Not found", 404
    return render_template('edit_athlete.html',athlete=athlete)

# Admin function to apply update to athlete name
@app.route("/athlete/<id>/apply", methods=['post'])
def update_athlete(id):
    data = request.form
    #store this in the DB
    update_to_athlete_db(id, data)
    return render_template('update_submitted.html', update=data)

# Admin function to read Eventor xml file and add athletes to database
@app.route('/athletes/read_xml')
def read_athletes_from_xml():
    athlete_list = load_athletes_from_xml()
    #store this in the DB
    store_athletes_in_db(athlete_list)
    #display an acknowledgement 
    return render_template('athletes_submitted.html', athlete_list=athlete_list)


# admin function to import clubs from Eventor xml list
@app.route('/clubs/read_xml')
def read_clubs_from_xml():
    club_list = load_clubs_from_xml()
    #store this in the DB
    store_clubs_in_db(club_list)

    #display an acknowledgement 
    return render_template('clubs_submitted.html', club_list=club_list)


# Events page
@app.route("/events", methods=['GET', 'POST']) 
def events_page(): 
    events, race_codes = load_events_from_db() 
    return render_template('events.html', events=events, race_codes=race_codes)

# Indiviudal event page with event summary and results
@app.route("/event/<short_file>")
def show_event(short_file):
    event, results = load_event_from_db(short_file)
    if not event:
        return "Not found", 404
    
    # Convert race_time to datetime objects 
    for result in results: 
        if result['race_time']:
            result['race_time'] = convert_to_time_format(result['race_time'])
        if result['place'] is None:
            result['place'] = ""

    # Sort results to place rows with empty place at the bottom
    results = sorted(results, key=lambda x: (x['place'] == "", x['place']))
    stats = load_event_stats(event['short_desc'])

    return render_template('event.html',event=event,results=results,stats=stats)


# admin function to allow the user to read events from Excel
@app.route('/events/read_xls')
def events_read_xls():
    return render_template('events_read_xls.html')

# admin function to read the events from Excel and store into the events table
@app.route("/events/import", methods=['post'])
def imported_events():
    input = request.form

    # call import_events_from_excel
    df_html = import_events_from_excel(input)

    #display an acknowledgement 
    return render_template('events_submitted.html', df_html=df_html)


# admin function to allow the user to enter the IOF event_id to import from WRE
@app.route('/race/read_WRE')
def race_read_WRE():
    return render_template('race_read_wre.html')

# admin function to allow the user to enter the Excel file and race_code to import
@app.route('/race/read_xls')
def race_read_xls():
    return render_template('race_read_xls.html')

# admin function to allow the user to enter the Excel file and race_code to import race times only
@app.route('/race_times/read_xls')
def race_times_read_xls():
    return render_template('race_times_read_xls.html')


# admin function to process race times only and insert in race_tmp table
@app.route('/race_times/new', methods=['post'])
def race_times_new():
    input = request.form
    df = load_from_xlsx(input)
    # Slice the DataFrame to start from row 2 (index 1) and columns C to E (index 2 to 4) 
    partial_df = df.iloc[1:91, 1:5] 
    # Drop rows that are empty column 2 in the sliced DataFrame 
    parsed_df = partial_df.dropna(subset=[partial_df.columns[2]])
    # Convert the DataFrame to a list of tuples for insertion into MySQL 
    data_to_insert = [tuple(row) for row in parsed_df.to_numpy()]
    #store this in the DB
    store_race_tmp_from_excel(input['sheet'], data_to_insert)

    calculate_race_rankings(input['sheet'])

    df_html = parsed_df.to_html()
    #display an acknowledgement 
    return render_template('race_submitted.html', df_html=df_html)


# admin function to allow the user to enter the Excel file to import all races from the file
@app.route('/races/read_xls')
def races_read_xls():
    return render_template('races_read_xls.html')


# Admin function to read the input file, load race data from Excel, and store race data
@app.route("/race/new", methods=['post'])
def uploaded_race():
    input = request.form
    df = load_from_xlsx(input)
    # Slice the DataFrame to start from row 2 (index 1) and columns C to E (index 2 to 4) 
    partial_df = df.iloc[1:91, 1:5] 
    # Drop rows that are empty column 2 in the sliced DataFrame 
    parsed_df = partial_df.dropna(subset=[partial_df.columns[2]])
    # Convert the DataFrame to a list of tuples for insertion into MySQL 
    data_to_insert = [tuple(row) for row in parsed_df.to_numpy()]
    #store this in the DB
    store_race_from_excel(input['sheet'], data_to_insert)

    df_html = parsed_df.to_html()
    #display an acknowledgement 
    return render_template('race_submitted.html', df_html=df_html)

# Admin function to read the input file, load race data from Excel, and store race data
@app.route("/race/new/<event_code>")
def upload_race(event_code):
    ranking_list = request.args.get('list')
    print(ranking_list)
    input = {}
    input['path_file'] = "s:/Rankings/source/2024/" + ranking_list + ".xls"
    input['sheet'] = event_code
    df = load_from_xlsx(input)
    # Slice the DataFrame to start from row 2 (index 1) and columns C to E (index 2 to 4) 
    partial_df = df.iloc[1:91, 1:5] 
    # Drop rows that are empty column 2 in the sliced DataFrame 
    parsed_df = partial_df.dropna(subset=[partial_df.columns[2]])
    # Convert the DataFrame to a list of tuples for insertion into MySQL 
    data_to_insert = [tuple(row) for row in parsed_df.to_numpy()]
    #store this in the DB
    store_race_from_excel(input['sheet'], data_to_insert)

    df_html = parsed_df.to_html()
    #display an acknowledgement 
    return render_template('race_submitted.html', df_html=df_html)

# Admin function to read the input file, load multiple races from Excel, and store race data
@app.route("/races/new", methods=['post'])
def uploaded_races():
    input = request.form
    
    df_list = add_multiple_races_for_list_year(input)

        
    #display an acknowledgement 
    return render_template('races_submitted.html', df_list=df_list )


# icon for browser header
@app.route('/favicon.png')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.png', mimetype='image/png')


# Render health-check called automatically every 5 seconds
@app.route('/health-check')
def health_check():
    # Simulated checks
    #database_status = check_database()  # Simulated function to check database status

    #status = 'healthy' if database_status else 'unhealthy'
    #return jsonify({'status': status}), 200 if status == 'healthy' else 503
    return jsonify({"status": "OK"}) 

# Starts a background task look up the IOF WR site for specificed race with AUS results - and if so add to database
# returns a response in a few ms, but starts a background thread to perform the work
@app.route("/race/new_WRE", methods=['POST'])
def upload_wre_race():
    input = {}
    input['event_id'] = request.form.get('event_id')
    input['discipline'] = request.form.get('discipline')
    print("Starting upload_WRE_race_task():", datetime.now(sydney_tz))
    # Start the background task
    thread = Thread(target=process_and_store_data, args=(input,))
    thread.start()

    # Render the template using Jinja2
    print("Render response upload_wRE_race_task():", datetime.now(sydney_tz))
    return render_template('events_submitted.html', df_html=input)


# Starts a background task look up the IOF WR site to look for latest races with AUS results - and if so add to database
# Called by cron-job.org each day at 7am (Sydney) 
# returns a response in a few ms, but starts a background thread to perform the work
@app.route("/race/latest_WRE")
def upload_latest_wre_races():
    print("Starting upload_latest_wre_races():", datetime.now(sydney_tz))
    # Start the background task
    #thread = Thread(target=process_latest_WRE_races)
    #thread.start()

    process_latest_WRE_races() #synchonous call for now


    # Render the template using Jinja2
    print("Render response upload_latest_wre_races():", datetime.now(sydney_tz))
    return render_template('events_submitted.html', df_html=input)


@app.route("/races/year_WRE")
def year_WRE():
    return render_template('year_WRE.html')    

@app.route("/races/year_WRE_upload", methods=['POST'])
def year_WRE_upload():
    year = request.form
    print(f"Starting year_WRE_upload(): {year} ", datetime.now(sydney_tz))
    upload_year_WRE_races(year)
    # Render the template using Jinja2
    print("Render response year_WRE_upload():", datetime.now(sydney_tz))
    return render_template('events_submitted.html', df_html=input)


@app.route("/scrape")
def scrape():
    # test function for browserless.io
    browserless_selenium()

    return "Scraping"


# main function
if __name__ == "__main__":
    app.run(debug=True, port=5000)
