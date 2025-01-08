import os
from flask import Flask, render_template, send_from_directory, jsonify
from database import load_athletes_from_db

app = Flask(__name__)


@app.route("/")
def home_page():
    athletes = load_athletes_from_db()
    print('data load and broswer refresh')
    return render_template('index.html', athletes=athletes, group='M')

@app.route("/api/athletes")
def list_athletes():
    athletes = load_athletes_from_db()
    return jsonify(athletes)



@app.route('/favicon.png')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.png', mimetype='image/png')


if __name__ == "__main__":
  app.run(host='0.0.0.0', debug=True) 

