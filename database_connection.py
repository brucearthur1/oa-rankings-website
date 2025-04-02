import pymysql
from dotenv import load_dotenv 
import os 

load_dotenv() 

timeout = 15
connection = pymysql.connect(
    charset="utf8mb4",
    connect_timeout=timeout,
    cursorclass=pymysql.cursors.DictCursor,
    db=os.getenv('DB'),
    host=os.getenv('HOST'),
    password=os.getenv('PASSWORD'),
    read_timeout=timeout,
    port=int(os.getenv('PORTNO')),
    user=os.getenv('USER'),
    write_timeout=timeout
)
