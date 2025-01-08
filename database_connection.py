import pymysql
from dotenv import load_dotenv 
import os 

load_dotenv() 

timeout = 10
connection = pymysql.connect(
    charset="utf8mb4",
    connect_timeout=timeout,
    cursorclass=pymysql.cursors.DictCursor,
    db=os.getenv('DB'),
    host=os.getenv('HOST'),
    password=os.getenv('PASSWORD'),
    read_timeout=timeout,
    port=int(os.getenv('PORT')),
    user=os.getenv('USER'),
    write_timeout=timeout,
)

#try:
#  cursor = connection.cursor()
#  cursor.execute("SELECT * FROM athletes")

#  result_dicts = []
#  for row in cursor.fetchall():
#    result_dicts.append(row)

#  print(result_dicts)

#finally:
#  connection.close()
