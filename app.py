import os
from flask import Flask, render_template, send_from_directory

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



@app.route("/")
def home_page():
    return render_template('index.html', athletes=ATHLETES, group='Women')

@app.route('/favicon.png')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.png', mimetype='image/png')


if __name__ == "__main__":
  app.run(host='0.0.0.0', debug=True) 

