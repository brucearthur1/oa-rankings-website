import os
from flask import Flask, render_template, send_from_directory
from database import connection



app = Flask(__name__)

ATHLETES = [
  {
      'id' : 1,
      'name' : 'Michael Phelps',
      'state' : 'SA',
      'class' : 'Men',
      'YOB' : 1985,
      'points' : 5023
  },  
  {
      'id' : 2,
      'name' : 'John Smith',
      'class' : 'Men',
      'YOB' : 2005,
      'points' : 5019
  },  
  {
      'id' : 3,
      'name' : 'Jane Smith',
      'state' : 'WA',
      'class' : 'Women',
      'YOB' : 1995,
      'points' : 4019
  }
    
]

def load_athletes_from_db():
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM athletes")
        result = cursor.fetchall()
        athletes = []
        for row in result:
            athletes.append(row)
        return athletes
      


@app.route("/")
def home_page():
    athletes = load_athletes_from_db()
    return render_template('index.html', athletes=athletes, group='M')


@app.route('/favicon.png')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.png', mimetype='image/png')


if __name__ == "__main__":
  app.run(host='0.0.0.0', debug=True) 

