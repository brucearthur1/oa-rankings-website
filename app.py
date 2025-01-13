import os
import pandas as pd
from flask import Flask, render_template, send_from_directory, jsonify, request
from database import load_athletes_from_db, load_athlete_from_db, update_to_athlete_db, store_race_from_excel, store_events_from_excel, load_events_staging_from_db, load_event_from_db
from excel import load_from_xls, load_from_xlsx
from datetime import datetime


app = Flask(__name__)


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

@app.route("/athletes")
def athletes_page():
    athletes = load_athletes_from_db()
    return render_template('athletes.html', athletes=athletes, group='W')

@app.route("/api/athletes")
def list_athletes():
    athletes = load_athletes_from_db()
    return jsonify(athletes)

@app.route("/athlete/<id>")
def show_athlete(id):
    athlete= load_athlete_from_db(id)
    if not athlete:
        return "Not found", 404
    return render_template('athletepage.html',athlete=athlete)


@app.route("/athlete/<id>/apply", methods=['post'])
def update_athlete(id):
    data = request.form
    athlete = load_athlete_from_db(id)
    #store this in the DB
    update_to_athlete_db(id, data)
    #send an email
    #display an acknowledgement 
    return render_template('update_submitted.html', 
                           update=data,
                           athlete=athlete)

@app.route("/events", methods=['GET', 'POST']) 
def events_page(): 
    list_filter = request.form.get('list_filter', '').strip().lower() 
    start_date = request.form.get('start_date', '').strip() 
    end_date = request.form.get('end_date', '').strip()    
    # Ensure date_filter is in the 'YYYY-MM-DD' format 
    try:
        start_date = pd.to_datetime(start_date).strftime('%Y-%m-%d') if start_date else '' 
        end_date = pd.to_datetime(end_date).strftime('%Y-%m-%d') if end_date else '' 
    except ValueError:
        start_date = ''
        end_date = ''    
    
    events, race_codes = load_events_staging_from_db() 
    
    if list_filter: 
        events = [event for event in events if list_filter == event['list'].lower()] 
    if start_date and end_date:
        events = [event for event in events if start_date <= pd.to_datetime(event['date']).strftime('%Y-%m-%d') <= end_date]        
        #events = [event for event in events if pd.to_datetime(event['date']).strftime('%Y-%m-%d') == date_filter] 
    
    return render_template('events.html', events=events, race_codes=race_codes)

@app.route("/event/<short_file>")
def show_event(short_file):
    event, results = load_event_from_db(short_file)
    if not event:
        return "Not found", 404
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
    

@app.route('/favicon.png')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.png', mimetype='image/png')


@app.template_filter('strftime') 
def _jinja2_filter_datetime(date, fmt=None): 
    return date.strftime(fmt) if fmt else date.strftime('%d/%m/%Y')


if __name__ == "__main__":
  app.run(host='0.0.0.0', debug=True) 

