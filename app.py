import os
import pandas as pd
from flask import Flask, render_template, send_from_directory, jsonify, request
from database import load_athletes_from_db, load_athlete_from_db, update_to_athlete_db, store_race_from_excel, store_events_from_excel, load_events_staging_from_db, load_event_from_db, store_clubs_in_db, store_athletes_in_db, insert_athlete_db
from excel import load_from_xls, load_from_xlsx
from datetime import datetime
from formatting import convert_to_time_format
from xml_util import load_clubs_from_xml, load_athletes_from_xml

app = Flask(__name__)

@app.template_filter('strftime') 
def _jinja2_filter_datetime(date, fmt=None): 
    return date.strftime(fmt) if fmt else date.strftime('%d/%m/%Y')

app.jinja_env.filters['_jinja2_filter_datetime'] = _jinja2_filter_datetime


def is_valid_time_format(time_str):
    try: 
        datetime.strptime(time_str, "%H:%M:%S") 
        return True 
    except ValueError:
        return False 

app.jinja_env.filters['is_valid_time_format'] = is_valid_time_format



@app.route("/")
def home_page():
    athletes = load_athletes_from_db()
    return render_template('index.html', athletes=athletes, group='M')

@app.route("/about")
def about_page():
    return render_template('about.html')

@app.route("/admin")
def admin_page():
    return render_template('admin.html')


@app.route("/athlete/add")
def add_athlete():
    ########### continue this


    athletes = load_athletes_from_db()
    return render_template('athletes.html', athletes=athletes)

@app.route("/athlete/ineligible")
def add_ineligible_athlete():
    ########## test this

    full_name = request.args.get('full_name')
    list = request.args.get('list')
    
    if list:
        if list.lower() in ('men','boys'):
            gender = 'M'
        elif list.lower() in ('women','girls'):
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

    print(update)
    insert_athlete_db(update=update)
    
    return render_template('update_submitted.html', update=update)
    

@app.route("/athletes")
def athletes_page():
    athletes = load_athletes_from_db()
    return render_template('athletes.html', athletes=athletes)



@app.route("/api/athletes")
def list_athletes():
    athletes = load_athletes_from_db()
    return jsonify(athletes)

@app.route("/athlete/<id>")
def show_athlete(id):
    athlete= load_athlete_from_db(id)
    if not athlete:
        return "Not found", 404
    return render_template('athletepage.html',athlete=athlete, datetime=datetime)

@app.route("/athlete/<id>/edit")
def edit_athlete(id):
    athlete= load_athlete_from_db(id)
    if not athlete:
        return "Not found", 404
    return render_template('edit_athlete.html',athlete=athlete)


@app.route("/athlete/<id>/apply", methods=['post'])
def update_athlete(id):
    data = request.form
    #store this in the DB
    update_to_athlete_db(id, data)

    #athlete = load_athlete_from_db(id)
    #display an acknowledgement 
    return render_template('update_submitted.html', 
                           update=data)


@app.route('/athletes/read_xml')
def read_athletes_from_xml():
    athlete_list = load_athletes_from_xml()
    #store this in the DB
    store_athletes_in_db(athlete_list)

    #display an acknowledgement 
    return render_template('athletes_submitted.html', athlete_list=athlete_list)

@app.route('/clubs/read_xml')
def read_clubs_from_xml():
    club_list = load_clubs_from_xml()
    #store this in the DB
    store_clubs_in_db(club_list)

    #display an acknowledgement 
    return render_template('clubs_submitted.html', club_list=club_list)


@app.route("/events", methods=['GET', 'POST']) 
def events_page(): 
    #list_filter = request.form.get('list_filter', '').strip().lower() 
    #start_date = request.form.get('start_date', '').strip() 
    #end_date = request.form.get('end_date', '').strip()    
    # Ensure date_filter is in the 'YYYY-MM-DD' format 
    #try:
    #    start_date = pd.to_datetime(start_date).strftime('%Y-%m-%d') if start_date else '' 
    #    end_date = pd.to_datetime(end_date).strftime('%Y-%m-%d') if end_date else '' 
    #except ValueError:
    #    start_date = ''
    #    end_date = ''    
    
    events, race_codes = load_events_staging_from_db() 
    
    #if list_filter: 
    #    events = [event for event in events if list_filter == event['list'].lower()] 
    #if start_date and end_date:
    #    events = [event for event in events if start_date <= pd.to_datetime(event['date']).strftime('%Y-%m-%d') <= end_date]        
    #    #events = [event for event in events if pd.to_datetime(event['date']).strftime('%Y-%m-%d') == date_filter] 
    
    return render_template('events.html', events=events, race_codes=race_codes)

@app.route("/event/<short_file>")
def show_event(short_file):
    event, results = load_event_from_db(short_file)
    if not event:
        return "Not found", 404
    
    # Convert race_time to datetime objects 
        
    for result in results: 
        if result['race_time']:
            result['race_time'] = convert_to_time_format(result['race_time'])



    return render_template('event.html',event=event,results=results)


@app.route('/events/read_xls')
def events_read_xls():
    return render_template('events_read_xls.html')

@app.route("/events/import", methods=['post'])
def imported_events():
    input = request.form
    df = load_from_xls(input)
    # Slice the DataFrame to start from row start to finish and columns (index 0 to 9) 
    partial_df = df.iloc[int(input['start'])-2:int(input['finish'])-1, 0:10] 
    # Drop rows if all rows are empty in the sliced DataFrame 
    parsed_df = partial_df.dropna(how='all')

    # Format the date column to DD/MM/YYYY 
    parsed_df['Date'] = parsed_df['Date'].dt.strftime('%Y-%m-%d')

    # Convert the DataFrame to a list of tuples for insertion into MySQL 
    data_to_insert = [tuple(row) for row in parsed_df.to_numpy()]
    #store this in the DB
    store_events_from_excel(data_to_insert)

    df_html = parsed_df.to_html()
    #display an acknowledgement 
    return render_template('events_submitted.html', df_html=df_html)

@app.route('/race/read_xls')
def race_read_xls():
    return render_template('race_read_xls.html')

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



@app.route('/favicon.png')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.png', mimetype='image/png')




if __name__ == "__main__":
  app.run(host='0.0.0.0', debug=True) 

