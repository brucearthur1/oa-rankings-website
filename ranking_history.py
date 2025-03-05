# save this for future development
# Python script to calculate the top 5 points for each athlete in each year from 2024 to 2025
# and rank them based on the total top 5 points in descending order


import mysql.connector
from datetime import datetime, timedelta

# Connect to the MySQL database
db = mysql.connector.connect(
    host="your_host",
    user="your_username",
    password="your_password",
    database="your_database"
)

cursor = db.cursor()

# Function to execute the query with given date range
def execute_query(date1, date2):
    query = f"""
    SELECT 
        ROW_NUMBER() OVER (ORDER BY total_top_5_points DESC) AS rank,
        full_name,
        total_top_5_points
    FROM
        (SELECT 
            r.full_name,
            SUM(CAST(r.race_points AS FLOAT)) AS total_top_5_points
         FROM
            (SELECT 
                r.full_name,
                r.race_points,
                ROW_NUMBER() OVER (PARTITION BY r.full_name ORDER BY CAST(r.race_points AS FLOAT) DESC) AS my_rank
             FROM
                results r
             INNER JOIN 
                events e
                ON r.race_code = e.short_desc
             WHERE
                e.list = 'men'
                AND e.date BETWEEN '{date1}' AND '{date2}'
            ) ranked_results
         WHERE
            ranked_results.my_rank <= 5
         GROUP BY
            r.full_name
        ) final_results
    ORDER BY
        total_top_5_points DESC;
    """
    cursor.execute(query)
    result = cursor.fetchall()
    for row in result:
        print(row)

# Set the initial date range
start_date = datetime.strptime('2024-03-05', '%Y-%m-%d')
end_date = datetime.strptime('2025-03-04', '%Y-%m-%d')
delta = timedelta(days=365)

# Iterate and execute the query with different date ranges
while start_date <= end_date:
    date1 = start_date.strftime('%Y-%m-%d')
    date2 = (start_date + delta).strftime('%Y-%m-%d')
    execute_query(date1, date2)
    start_date += delta

# Close the cursor and database connection
cursor.close()
db.close()
