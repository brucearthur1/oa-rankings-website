import os
from flask import Flask, render_template, send_from_directory, jsonify, request
from database import load_athletes_from_db, load_athlete_from_db, update_to_athlete_db 

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



@app.route('/favicon.png')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.png', mimetype='image/png')


if __name__ == "__main__":
  app.run(host='0.0.0.0', debug=True) 

