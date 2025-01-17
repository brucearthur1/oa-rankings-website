import pandas as pd
from database_connection import connection


def get_sheets_from_event(list):
    connection.autocommit(True)
    with connection.cursor() as cursor:
        query = "SELECT events_staging.short_file FROM events_staging LEFT JOIN result_staging ON events_staging.short_file = result_staging.race_code WHERE list = %s AND result_staging.id IS NULL"         
        cursor.execute(query, list)
        result = cursor.fetchall()
        sheets = []
        for row in result:
            sheets.append(row)
        return sheets

def insert_athlete_db(update):
    with connection.cursor() as cursor:
        # Define the query with a placeholder 
        query = "INSERT INTO athletes (eventor_id, full_name, given, family, gender, yob, nationality_code, club_id, eligible) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        #Execute the query with the parameter 
        cursor.execute(query, (update['eventor_id'], update['full_name'], update['given'], update['family'], update['gender'],update['yob'], update['nationality_code'], update['club_id'], update['eligible'])
                       ) 
        connection.commit()



def load_athletes_from_db():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM athletes LEFT JOIN clubs ON athletes.club_id = clubs.id WHERE nationality_code = 'AUS' AND last_event_date is not NULL")
        result = cursor.fetchall()
        athletes = []
        for row in result:
            athletes.append(row)
        return athletes

def load_athlete_from_db(id):
    connection.autocommit(True)
    with connection.cursor() as cursor:
        # Define the query with a placeholder 
        query = "SELECT * FROM athletes LEFT JOIN clubs ON athletes.club_id = clubs.id WHERE nationality_code = 'AUS' AND athletes.id = %s" 
        #Execute the query with the parameter 
        cursor.execute(query, (id,)) 
        # Fetch the results 
        result = cursor.fetchall() 
        # Print the results
        if len(result) == 0:
            return None
        else:
            return result[0]


def load_athletes_from_results():
    query = "SELECT result_staging.*, athletes.id as athlete_id, athletes.eligible, clubs.* FROM result_staging LEFT JOIN athletes ON result_staging.full_name = athletes.full_name LEFT JOIN clubs ON athletes.club_id = clubs.id "
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute(query)
        data = cursor.fetchall()
        results = []
        for row in data:
            results.append(row)

        return results


def update_to_athlete_db(id, update):
    with connection.cursor() as cursor:
        # Define the query with a placeholder 
        query = "UPDATE athletes SET full_name=%s WHERE id=%s" 
        #Execute the query with the parameter 
        cursor.execute(query, (update['full_name'], id)
                       ) 
        connection.commit()

def load_event_from_db(short_file):
    query1 = "SELECT * FROM events_staging WHERE short_desc = %s"
    query2 = "SELECT result_staging.*, athletes.id as athlete_id, athletes.eligible, clubs.* FROM result_staging LEFT JOIN athletes ON result_staging.full_name = athletes.full_name LEFT JOIN clubs ON athletes.club_id = clubs.id WHERE result_staging.race_code = %s ORDER BY place"
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute(query1, short_file)
        event = cursor.fetchone()
        
        # Load race codes data 
        cursor.execute(query2, short_file)
        data = cursor.fetchall()
        results = []
        for row in data:
            results.append(row)

        return event, results



def load_events_staging_from_db():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM events_staging")
        result = cursor.fetchall()
        events = []
        for row in result:
            events.append(row)
        
        # Load race codes data 
        cursor.execute("SELECT DISTINCT race_code FROM result_staging") 
        result = cursor.fetchall()
        race_codes = []
        for row in result:
            race_codes.append(row['race_code'])
        return events, race_codes



def load_oldWRE_events_from_db():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute("select mid(short_desc,3) as 'IOF_event_id' from events_staging where short_file = 'WRE' and created_at < '2025-01-20 00:00:00.00';")
        result = cursor.fetchall()
        list = []
        for row in result:
            list.append(row)
        return list


def load_rankings_from_db():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT result_staging.* , athletes.id as athlete_id, athletes.yob, events_staging.*, clubs.* FROM result_staging INNER JOIN athletes ON result_staging.full_name = athletes.full_name AND athletes.eligible= 'Y' LEFT JOIN events_staging ON result_staging.race_code = events_staging.short_desc LEFT JOIN clubs ON athletes.club_id = clubs.id WHERE 1=1 ORDER BY athletes.id;")
        result = cursor.fetchall()
        rankings = []
        for row in result:
            rankings.append(row)
        return rankings



def load_results_by_athlete(full_name):
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM result_staging LEFT JOIN events_staging ON result_staging.race_code = events_staging.short_desc WHERE result_staging.full_name = %s ORDER BY events_staging.date DESC;", full_name)
        result = cursor.fetchall()
        results = []
        for row in result:
            results.append(row)
        return results


def store_athletes_in_db(data_to_insert):
    with connection.cursor() as cursor:
        # Insert data 
        insert_query = "INSERT INTO athletes (eventor_id, full_name, given, family, gender, yob, nationality_code, club_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.executemany(insert_query, data_to_insert) 
        connection.commit() 
        print("Data inserted successfully!")



def store_clubs_in_db(data_to_insert):
    with connection.cursor() as cursor:
        # Insert data 
        insert_query = "INSERT INTO clubs (club_type, id, club_name, short_name, state, country) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.executemany(insert_query, data_to_insert) 
        connection.commit() 
        print("Data inserted successfully!")


def store_events_from_excel(data_to_insert):
    with connection.cursor() as cursor:
        # Insert data 
        insert_query = """ 
        INSERT INTO events_staging (
        date, 
        short_desc, 
        long_desc, 
        class, 
        short_file,
        map_link,
        graph,
        ip,
        list,
        eventor_id
        ) 
        VALUES ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
        """ 
        print(data_to_insert)
        cursor.executemany(insert_query, data_to_insert) 
        connection.commit() 
        print("Data inserted successfully!")



def store_events_from_WRE(data_to_insert):
    with connection.cursor() as cursor:
        for event in data_to_insert:
        
            select_query = "SELECT * FROM `events_staging` WHERE `short_desc` = %s" 
            cursor.execute(select_query, event[1]) 
            result = cursor.fetchone() 
            if result:
                print(f"Event '{event[2]}' already exists in the database.") 
            else:
                # Insert data 
                insert_query = """ 
                INSERT INTO events_staging (
                date, 
                short_desc, 
                long_desc, 
                class, 
                short_file,
                map_link,
                graph,
                ip,
                list,
                eventor_id,
                iof_id
                ) 
                VALUES ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                """ 
                
                print(event)

                cursor.execute(insert_query, event) 
        connection.commit() 
        print("Data inserted successfully!")



def store_race_from_excel(sheetname, data_to_insert):
    with connection.cursor() as cursor:
        # Insert data 
        insert_query = """ 
        INSERT INTO result_staging (race_code, place, full_name, race_time, race_points) 
        VALUES (%s, %s, %s, %s, %s) 
        """ 
        cursor.executemany(insert_query, [(sheetname, place, full_name, race_time, race_points) for place, full_name, race_time, race_points in data_to_insert])
        

        # Fetch the event date
        select_query = "SELECT date FROM events_staging WHERE short_file = %s"
        cursor.execute(select_query, (sheetname,))
        event_date = cursor.fetchone()

        for item in data_to_insert:
            update_query = """
                UPDATE athletes
                SET last_event_date = %s
                WHERE IFNULL(last_event_date, '0000-01-01') < %s
                AND full_name = %s
                """

            cursor.execute(update_query, (event_date['date'], event_date['date'], item[1]))

        connection.commit()

        print("Data inserted successfully!")



def store_results_from_WRE(data_to_insert):
    with connection.cursor() as cursor:
        for result in data_to_insert:

            select_query = "SELECT * FROM `result_staging` WHERE `race_code` = %s and full_name = %s" 
            cursor.execute(select_query, (result[0], result[2])) 
            exists = cursor.fetchone() 
            if exists:
                print(f"Result '{result[0]}{result[2]}' already exists in the database.") 
            else:
                # Insert results data 
                insert_query = """ 
                INSERT INTO result_staging (race_code, place, full_name, race_time, race_points) 
                VALUES (%s, %s, %s, %s, %s) 
                """ 
                cursor.execute(insert_query, result)
                print(f"WRE '{result[0]}{result[2]}' resutls inserted")

                # check if athlete exists.  If not, add them to the athletes table 
                # Check if the athlete exists 
                select_query = "SELECT * FROM `athletes` WHERE `full_name` = %s" 
                cursor.execute(select_query, result[2]) 
                athlete_exists = cursor.fetchone() 
                if athlete_exists:
                    print(f"Athlete '{result[2]}' already exists in the database.") 
                else:
                    names = result[2].split(' ') 
                    # Assume the first part is the given name and the last part is the family name 
                    given_name = names[0] 
                    family_name = ' '.join(names[1:])
                    if result[0][2] == 'm':
                        gender = 'M' 
                    elif result[0][2] == 'w':
                        gender = 'F' 
                    else: 
                        gender = None

                    # Insert the new athlete 
                    insert_query = """ INSERT INTO `athletes` ( 
                    `eventor_id`, `full_name`, `given`, `family`, `gender`, `yob`, `nationality_code`, `club_id`, `eligible`, `last_event_date` 
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) """ 
                    cursor.execute(insert_query, ( None, result[2], given_name, family_name, gender, None, 'AUS', None, 'Y', None )) 
                    connection.commit() 
                    print(f"Athlete '{result[0]}{result[2]}' has been added to the database.")


                # Fetch the event date
                select_query = "SELECT date FROM events_staging WHERE short_desc = %s"
                cursor.execute(select_query, result[0])
                event_date = cursor.fetchone()
                if event_date:
                    update_query = """
                        UPDATE athletes
                        SET last_event_date = %s
                        WHERE IFNULL(last_event_date, '0000-01-01') < %s
                        AND full_name = %s
                        """

                    cursor.execute(update_query, (event_date['date'], event_date['date'], result[2]))
                else:
                    print(f"event '{result[0]}' not in database")

        connection.commit()

        print("Athlete last_event_date updated successfully!")
