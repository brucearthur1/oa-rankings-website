from database_connection import connection

def load_athletes_from_db():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM athletes")
        result = cursor.fetchall()
        athletes = []
        for row in result:
            athletes.append(row)
        return athletes

def load_athlete_from_db(id):
    connection.autocommit(True)
    with connection.cursor() as cursor:
        # Define the query with a placeholder 
        query = "SELECT * FROM athletes WHERE id = %s" 
        #Execute the query with the parameter 
        cursor.execute(query, (id,)) 
        # Fetch the results 
        result = cursor.fetchall() 
        # Print the results
        if len(result) == 0:
            return None
        else:
            return result[0]


def update_to_athlete_db(id, update):
    with connection.cursor() as cursor:
        # Define the query with a placeholder 
        query = "UPDATE athletes SET athlete=%s WHERE id=%s" 
        #Execute the query with the parameter 
        cursor.execute(query, (update['athlete'], id)
                       ) 
        connection.commit()


def store_race_from_excel(sheetname, data_to_insert):
    with connection.cursor() as cursor:
        # Insert data 
        insert_query = """ 
        INSERT INTO result_staging (race_code, place, athlete, race_time, race_points) 
        VALUES ('""" + sheetname + """', %s, %s, %s, %s) 
        """ 
        cursor.executemany(insert_query, data_to_insert) 
        connection.commit() 
        print("Data inserted successfully!")
