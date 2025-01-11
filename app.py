import os
from flask import Flask, render_template, send_from_directory, jsonify, request
from database import load_athletes_from_db, load_athlete_from_db, update_to_athlete_db, store_race_from_excel 
from excel import load_race_from_excel

app = Flask(__name__)


@app.route("/")
def home_page():
    athletes = load_athletes_from_db()
    print('data load and browser refresh')
    return render_template('index.html', athletes=athletes, group='M')

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


@app.route('/race/read_xls')
def race_read_xls():
    return render_template('race_read_xls.html')

@app.route("/race/new", methods=['post'])
def uploaded_race():
    input = request.form
    df = load_race_from_excel(input)
    
    # Slice the DataFrame to start from row 2 (index 1) and columns C to E (index 2 to 4) 
    partial_df = df.iloc[1:91, 1:5] 
    # Drop rows that are completely empty in the sliced DataFrame 
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

