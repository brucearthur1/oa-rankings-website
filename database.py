import pandas as pd
from database_connection import connection
from datetime import datetime, timedelta
import logging


def str_to_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d')

def convert_place(place):
    cleaned_place = place.strip().replace('\xa0', '')
    if cleaned_place:
        return int(cleaned_place)
    return None

def parse_race_time(race_time_str):
    if race_time_str == 'NC':
        minutes = 0
        seconds = 0
    else:
        minutes, seconds = map(int, race_time_str.split(':'))
    race_time = timedelta(minutes=minutes, seconds=seconds)
    return race_time



# calculate the average points for an athlete over the last 365 days
def calc_average(full_name, event_date_dt):
    start_date_dt = event_date_dt - timedelta(days=364)
    start_date = start_date_dt.strftime('%Y-%m-%d')
    event_date = event_date_dt.strftime('%Y-%m-%d')

    query = """        
        SELECT athletes.eligible, avg(results.race_points/events.ip) as avg_points
        FROM results
        INNER JOIN events ON results.race_code = events.short_desc
        INNER JOIN athletes ON results.full_name = athletes.full_name
        WHERE athletes.full_name = %s
            and events.date between %s and %s
            and results.race_points > 10
        GROUP BY athletes.eligible
        """
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute(query, (full_name, start_date, event_date))
        data = cursor.fetchone()

    if data:
        eligible = data['eligible']
        average = data['avg_points']
    else:
        eligible = None
        average = None

    return eligible, average 


def check_database():
    """
    Checks if the database contains any records in the 'clubs' table.

    Executes a SQL query to select the 'id' from the 'clubs' table with a limit of 1.
    If a record is found, it returns True, indicating that the database is not empty.
    Otherwise, it returns False.

    Returns:
        bool: True if the 'clubs' table contains at least one record, False otherwise.
    """
    query = "SELECT id FROM clubs LIMIT 1"
    #connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute(query)
        data = cursor.fetchone()
    if data:
        return True
    else:
        return False


def confirm_discipline(year):
    with connection.cursor() as cursor:
        query = """
            WITH winning_times AS (
            SELECT
                race_code
                ,CASE 
                    WHEN CHAR_LENGTH(winning_time) = 8 THEN winning_time 
                    WHEN CHAR_LENGTH(winning_time) = 7 THEN winning_time 
                    WHEN CHAR_LENGTH(winning_time) = 15 THEN substr(winning_time,1,8) 
                    ELSE SUBSTR(winning_time, 12, 8) 
                END as winning_time
            from
            (
            SELECT 
                race_code, 
                MIN(race_time) AS winning_time
            FROM results
            WHERE 
                race_time <> '00:00:00'
            GROUP BY race_code
            HAVING winning_time <> '00:00:00'
            ) temp
            ),
            winning_times_compared AS (
            SELECT
                race_code,
                winning_time,
                CASE
                WHEN TIME_TO_SEC(TIMEDIFF('1970-01-01 00:23:00', '1970-01-01 ' || winning_time)) > 0 THEN 1
                ELSE 0
                END AS is_sprint
            FROM winning_times
            )
            UPDATE events
            SET discipline = 'Sprint'
            WHERE short_desc IN (
            SELECT race_code 
            FROM winning_times_compared 
            WHERE is_sprint = 1
            )
            and year(date) = %s
        """
        print(query)
        cursor.execute(query, (year))
        connection.commit()
        print(f"Disciplines updated for { year }")
    



def delete_from_race_tmp(short_desc):
    with connection.cursor() as cursor:
        query = "DELETE FROM race_tmp WHERE race_code = %s"
        cursor.execute(query, (short_desc,))
        connection.commit()
        print("race_tmp data deleted successfully!")


def get_sheets_from_event(list, year):
    connection.autocommit(True)
    with connection.cursor() as cursor:
        query = """
            SELECT events.short_file 
            FROM events LEFT JOIN results ON events.short_file = results.race_code 
            WHERE list = %s
            AND year(date) = %s
            AND results.id IS NULL
        """
        cursor.execute(query, (list, year))
        result = cursor.fetchall()
        sheets = []
        for row in result:
            sheets.append(row)
        return sheets


def get_latest_WRE_date():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        query = "SELECT max(date) FROM events WHERE short_file = 'WRE';"         
        cursor.execute(query)
        date_dict = cursor.fetchone()

        # Access the date value
        max_date = date_dict['max(date)']

        # Convert to string format 'YYYY-MM-DD'
        formatted_date = max_date.strftime('%Y-%m-%d')

        return formatted_date



def insert_athlete_db(update):
    with connection.cursor() as cursor:
        # Define the query with a placeholder 
        query = "INSERT INTO athletes (eventor_id, full_name, given, family, gender, yob, nationality_code, club_id, eligible, last_event_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        #Execute the query with the parameter 
        cursor.execute(query, (update['eventor_id'], update['full_name'], update['given'], update['family'], update['gender'],update['yob'], update['nationality_code'], update['club_id'], update['eligible'], update['last_event_date'])
                       ) 
        connection.commit()


def insert_event_statistics(event_id, event_stats):
    with connection.cursor() as cursor:
        # Define the query with a placeholder 
        query = "INSERT INTO event_stats (id, calculated, mt, st, mp, sp, rule, min, max, ranked, enhancement_factor) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (
            event_id,
            event_stats[0],
            event_stats[1],
            event_stats[2],
            event_stats[3],
            event_stats[4],
            event_stats[5],
            event_stats[6],
            event_stats[7],
            event_stats[8],
            event_stats[9]) )
        connection.commit()
        print("Event statistics inserted successfully!")

def insert_new_results(race_times):
    new_result_data = [
        (
            result['race_code'],
            result['place'],
            result['full_name'],
            result['race_time'],
            result['rp']
        )
        for result in race_times
    ]
    print(new_result_data)
    store_new_results(new_result_data)




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
    query = "SELECT results.*, athletes.id as athlete_id, athletes.eligible, clubs.* FROM results LEFT JOIN athletes ON results.full_name = athletes.full_name LEFT JOIN clubs ON athletes.club_id = clubs.id "
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute(query)
        data = cursor.fetchall()
        results = []
        for row in data:
            results.append(row)

        return results


def load_latest_event_date(full_name):
    query = """
        select 
            max(events.date) as event_date
        from
            results
        inner join 
            events on results.race_code = events.short_desc
        where
            results.full_name = %s
        """
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute(query, full_name)
        data = cursor.fetchone()
    return data['event_date']



def load_unmatched_athletes():
    query = "SELECT results.*, events.list FROM results INNER JOIN events ON results.race_code = events.short_desc LEFT JOIN athletes ON results.full_name = athletes.full_name WHERE athletes.full_name is NULL ORDER BY results.full_name;"
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute(query)
        data = cursor.fetchall()
        unmatched_athletes = []
        for row in data:
            unmatched_athletes.append(row)
    return unmatched_athletes




def load_aus_scores(mylist, start_date, end_date):
    aus_stats_query = """
        SELECT 
            avg(race_points) as mp,
            stddev(race_points) as sp
        FROM results 
        INNER JOIN events ON results.race_code = events.short_desc 
        WHERE events.short_file <> 'WRE' 
        AND events.date between %s and %s
        AND race_points > 10
        AND LOWER(%s) = events.list
        and full_name in
        (
            SELECT DISTINCT results.full_name
            FROM results 
            INNER JOIN events ON results.race_code = events.short_desc 
            WHERE events.short_file = 'WRE' 
            AND events.date between %s and %s
            AND race_points > 10
            AND LOWER(%s) = events.list
        )
        """
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute(aus_stats_query, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), mylist, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), mylist))
        data = cursor.fetchone()

    mp = data['mp']
    sp = data['sp']

    return mp, sp


def load_aus_scores_aus(mylist, start_date, end_date):
    aus_stats_query = """
        SELECT 
            avg(race_points) as mp,
            stddev(race_points) as sp
        FROM results 
        INNER JOIN events ON results.race_code = events.short_desc 
        WHERE events.short_file <> 'WRE' 
        AND events.date between %s and %s
        AND race_points > 10
        AND LOWER(%s) = events.list
        """
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute(aus_stats_query, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), mylist))
        data = cursor.fetchone()

    mp = data['mp']
    sp = data['sp']

    return mp, sp


def load_wre_scores(mylist, start_date, end_date):
    # get wre athletes for the list in the date range
    # parameters start_date and end_date are in date format
    wre_athletes_query = """
        SELECT DISTINCT results.full_name
        FROM results 
        INNER JOIN events ON results.race_code = events.short_desc 
        WHERE events.short_file = 'WRE' 
        AND events.date between %s and %s
        AND race_points > 10
        AND LOWER(%s) = events.list
        """

    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute(wre_athletes_query, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), mylist))
        data = cursor.fetchall()
    athlete_list = data if data else []

    # get wre stats for the list in the date range
    wre_stats_query = """
        SELECT 
            avg(race_points) as mp,
            stddev(race_points) as sp
        FROM results 
        INNER JOIN events ON results.race_code = events.short_desc 
        WHERE events.short_file = 'WRE' 
        AND events.date between %s and %s
        AND race_points > 10
        AND LOWER(%s) = events.list
        """

    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute(wre_stats_query, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), mylist))
        data = cursor.fetchone()

    mp = data['mp']
    sp = data['sp']

    print(f"Overall Average Points (mp): {mp}, Overall Standard Deviation (sp): {sp}")
    return athlete_list, mp, sp




def update_to_athlete_db(id, update):
    with connection.cursor() as cursor:
        # Define the query with a placeholder 
        query = "UPDATE athletes SET full_name=%s WHERE id=%s" 
        #Execute the query with the parameter 
        cursor.execute(query, (update['full_name'], id)
                       ) 
        connection.commit()


def load_event_date(race_code):
    query = "SELECT id, date, ip from events WHERE short_desc = %s"
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute(query, race_code)
        event = cursor.fetchone()
    return event


def load_event_stats(short_desc):
    query = "SELECT * FROM event_stats inner join events on events.id = event_stats.id WHERE short_desc = %s"
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute(query, short_desc)
        stats = cursor.fetchone()
    return stats


# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def load_event_from_db(short_file):
    # Individual event page with event summary and results, so use results_static as point in time calculation prior to any recalibration
    query1 = "SELECT * FROM events WHERE short_desc = %s"
    query2 = "SELECT results_static.*, athletes.id as athlete_id, athletes.eligible, clubs.* FROM results_static LEFT JOIN athletes ON results_static.full_name = athletes.full_name LEFT JOIN clubs ON athletes.club_id = clubs.id WHERE results_static.race_code = %s ORDER BY place"
    
    if not short_file:
        raise ValueError("The short_file parameter is None or empty.")
    
    try:
        connection.autocommit(True)
        with connection.cursor() as cursor:
            logging.debug(f"Executing query1: {query1} with parameter: {short_file}")
            cursor.execute(query1, (short_file,))
            event = cursor.fetchone()
            
            if not event:
                raise ValueError(f"No event found for short_desc: {short_file}")
            
            logging.debug(f"Executing query2: {query2} with parameter: {short_file}")
            cursor.execute(query2, (short_file,))
            data = cursor.fetchall()
            results = []
            for row in data:
                results.append(row)

            return event, results
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise


def load_events_from_db():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM events")
        result = cursor.fetchall()
        events = []
        for row in result:
            events.append(row)
        
        # Load race codes data 
        cursor.execute("SELECT DISTINCT race_code FROM results") 
        result = cursor.fetchall()
        race_codes = []
        for row in result:
            race_codes.append(row['race_code'])
        return events, race_codes


def load_race_tmp(race_code):
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT * from race_tmp where race_code = %s ORDER BY place",race_code)
        result = cursor.fetchall()
        return result


def load_races_by_athlete():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        query = """
            select 
                results.full_name
                ,athletes.id as athlete_id
                ,count(results.id) as race_count
                ,sum(race_points) as total_points
                ,avg(case when race_points > 0 then race_points end) as avg_points
                ,max(cast(race_points as unsigned)) as max_points
                ,min(place) as best_place
                ,count(case when place = 1 then 1 end) as race_wins
                ,min(events.date) as since_date
            from results
            left join athletes on results.full_name = athletes.full_name
            left join events on results.race_code = events.short_desc
            where 
                athletes.eligible <> 'N'
            group by
                results.full_name
                ,athletes.id
            order by
                2 desc
            """
        cursor.execute(query)
        result = cursor.fetchall()
        return result
                      
                       

def load_rankings_from_db():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT results.* , athletes.id as athlete_id, athletes.yob, events.*, clubs.* FROM results INNER JOIN athletes ON results.full_name = athletes.full_name AND athletes.eligible= 'Y' LEFT JOIN events ON results.race_code = events.short_desc LEFT JOIN clubs ON athletes.club_id = clubs.id WHERE 1=1 ORDER BY athletes.id;")
        result = cursor.fetchall()
        rankings = []
        for row in result:
            rankings.append(row)
        return rankings



def load_results_by_athlete(full_name):
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM results LEFT JOIN events ON results.race_code = events.short_desc WHERE results.full_name = %s ORDER BY events.date DESC;", full_name)
        result = cursor.fetchall()
        results = []
        for row in result:
            results.append(row)
        return results


def load_results_for_all_athletes():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM results LEFT JOIN events ON results.race_code = events.short_desc LEFT JOIN athletes ON athletes.full_name = results.full_name WHERE athletes.eligible = 'Y' ORDER BY events.date DESC;")
        result = cursor.fetchall()
        results = []
        for row in result:
            results.append(row)
        return results


def recalibrate_aus_scores(mylist, start_date_dt, end_date_dt, wre_mp, wre_sp, aus_mp, aus_sp): 
    start_date = start_date_dt.strftime('%Y-%m-%d')
    end_date = end_date_dt.strftime('%Y-%m-%d')
    print(f"before base points: {wre_mp}, {wre_sp}")
    print(f"before current year points: {aus_mp}, {aus_sp}")


    with connection.cursor() as cursor:
        # recalibrate ranking points. Make sure that new_points is no less than 10
        update_query = """
            WITH temp AS (
                SELECT 
                    results.id AS myid,
                    results.full_name,
                    results.race_points,
                    -- update the avg_a, stddev_a, stddev_wr, avg_wr  
                    -- (results.race_points - int(aus_mp)) / aus_sp * wre_sp + wre_mp AS new_points
                    GREATEST(
                        (results.race_points - CAST(%s AS FLOAT)) / CAST(%s AS FLOAT) * CAST(%s AS FLOAT) + CAST(%s AS FLOAT),
                        10
                    ) AS new_points
                FROM results
                INNER JOIN events
                    ON results.race_code = events.short_desc
                WHERE 
                    race_points > 10 
                    AND short_file <> 'WRE'
                    AND lower(list) = %s
                    AND events.date between %s and %s
            )
            UPDATE results
            INNER JOIN temp ON results.id = temp.myid
            SET results.race_points = temp.new_points
        """
        cursor.execute(update_query, (aus_mp, aus_sp, wre_sp, wre_mp, mylist, start_date, end_date )) 
        connection.commit() 
        print("Data updated successfully!")




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


def store_events_and_results(new_events, new_results):
    new_event_data = [
        (
            datetime.strptime(event['date'], '%d/%m/%Y').strftime('%Y-%m-%d'),
            event['short_desc'],
            event['long_desc'],
            event['class'],
            event['short_file'],
            event['ip'],
            event['list'],
            event['eventor_id'],
            event['iof_id'],
            event['discipline']  # this defaults to middle/long, but can be changed to sprint if needed
        )
        for event in new_events
    ]
    print(new_event_data)
    store_events_from_WRE(new_event_data)
    print("Finished storing new events:", datetime.now())

    new_result_data = [
        (
            result['race_code'],
            convert_place(result['place']),
            result['athlete_name'],
            parse_race_time(result['race_time']),
            result['race_points']
        )
        for result in new_results
    ]
    print(new_result_data)
    store_new_results(new_result_data)
    print("Finished storing new results:", datetime.now())



def store_events_from_excel(pre_data_to_insert):
    with connection.cursor() as cursor:
        # Define the insert query
        insert_query = """ 
        INSERT INTO events (
        date, 
        short_desc, 
        long_desc, 
        class, 
        short_file,
        ip,
        list,
        eventor_id
        ) 
        VALUES ( %s, %s, %s, %s, %s, %s, %s, %s) 
        """ 

        # Define the select query to check if the row exists
        select_query = "SELECT * FROM events WHERE short_desc = %s AND list = %s"

        # Remove any WREs
        data_to_insert = [row for row in pre_data_to_insert if row[4] != 'WRE']

        # Convert boys to Junior Men and girls to Junior Women
        modified_data_to_insert = []
        for row in data_to_insert:
            row_list = list(row)  # Convert tuple to list
            if row_list[6].lower() == 'boys':
                row_list[6] = 'Junior Men'
            elif row_list[6].lower() == 'girls':
                row_list[6] = 'Junior Women'
            modified_data_to_insert.append(tuple(row_list))  # Convert list back to tuple

        print(modified_data_to_insert)

        # Insert data one row at a time
        for row in modified_data_to_insert:
            cursor.execute(select_query, (row[1], row[6]))
            exists = cursor.fetchone()
            if not exists:
                cursor.execute(insert_query, row)
                print(f"Inserted row: {row}")
            else:
                print(f"Row already exists: {row}")

        connection.commit()
        print("Data inserted successfully! Remember to review Discipline using mySQL Workbench.")



def store_events_from_WRE(data_to_insert):
    with connection.cursor() as cursor:
        for event in data_to_insert:
        
            select_query = "SELECT * FROM `events` WHERE `short_desc` = %s" 
            cursor.execute(select_query, event[1]) 
            result = cursor.fetchone() 
            if result:
                print(f"Event '{event[2]}' already exists in the database.") 
            else:
                # Insert data 
                insert_query = """ 
                INSERT INTO events (
                date, 
                short_desc, 
                long_desc, 
                class, 
                short_file,
                ip,
                list,
                eventor_id,
                iof_id, 
                discipline
                ) 
                VALUES ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                """ 
                
                print(event)

                cursor.execute(insert_query, event) 
        connection.commit() 
        print("Data inserted successfully!")



def store_race_from_excel(sheetname, data_to_insert):
    print(f"Storing race from excel worksheet { sheetname }")
    print(data_to_insert)
    with connection.cursor() as cursor:
        # Set race_points to 0 if it is None
        data_to_insert = [(place, full_name, race_time, 0 if race_points is None else race_points) for place, full_name, race_time, race_points in data_to_insert]

        # Define the select query to check if the row exists
        select_query = "SELECT * FROM results WHERE race_code = %s AND full_name = %s"

        # Define the insert queries
        insert_query_results = """ 
        INSERT INTO results (race_code, place, full_name, race_time, race_points) 
        VALUES (%s, %s, %s, %s, %s) 
        """
        insert_query_results_static = """ 
        INSERT INTO results_static (race_code, place, full_name, race_time, race_points) 
        VALUES (%s, %s, %s, %s, %s) 
        """

        # Insert data one row at a time if it does not already exist
        for place, full_name, race_time, race_points in data_to_insert:
            cursor.execute(select_query, (sheetname, full_name))
            exists = cursor.fetchone()
            if not exists:
                cursor.execute(insert_query_results, (sheetname, place, full_name, race_time, race_points))
                cursor.execute(insert_query_results_static, (sheetname, place, full_name, race_time, race_points))
                print(f"Inserted row: {(sheetname, place, full_name, race_time, race_points)}")
            else:
                print(f"Row already exists: {(sheetname, place, full_name, race_time, race_points)}")

        # Fetch the event date
        select_query = "SELECT date FROM events WHERE short_file = %s"
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


def store_race_tmp_from_excel(sheetname, data_to_insert):
    with connection.cursor() as cursor:
        # Set race_points to 0 if it is None
        data_to_insert = [(place, full_name, race_time, 0 if race_points is None else race_points) for place, full_name, race_time, race_points in data_to_insert]

        # Define the select query to check if the row exists
        select_query = "SELECT * FROM results WHERE race_code = %s AND full_name = %s"

        # Define the insert queries
        insert_query_results = """ 
        INSERT INTO results (race_code, place, full_name, race_time, race_points) 
        VALUES (%s, %s, %s, %s, %s) 
        """
        insert_query_results_static = """ 
        INSERT INTO results_static (race_code, place, full_name, race_time, race_points) 
        VALUES (%s, %s, %s, %s, %s) 
        """

        # Insert data one row at a time if it does not already exist
        for place, full_name, race_time, race_points in data_to_insert:
            cursor.execute(select_query, (sheetname, full_name))
            exists = cursor.fetchone()
            if not exists:
                cursor.execute(insert_query_results, (sheetname, place, full_name, race_time, race_points))
                cursor.execute(insert_query_results_static, (sheetname, place, full_name, race_time, race_points))
                print(f"Inserted row: {(sheetname, place, full_name, race_time, race_points)}")
            else:
                print(f"Row already exists: {(sheetname, place, full_name, race_time, race_points)}")

        # Fetch the event date
        select_query_event_date = "SELECT date FROM events WHERE short_file = %s"
        cursor.execute(select_query_event_date, (sheetname,))
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


############################################################################################################
def store_new_results(data_to_insert):
    """
    Stores results from a World Ranking Event (WRE) into the database.
    This function processes a list of results, checks if each result already exists in the database,
    and inserts new results if they do not exist. It also checks if the athlete associated with each
    result exists in the database, and inserts new athletes if they do not exist. Additionally, it
    updates the last event date for each athlete.
    Args:
        data_to_insert (list of tuples): A list of tuples where each tuple contains the following
                                         information about a result:
                                         (race_code, place, full_name, race_time, race_points).
    Returns:
        None
    """
    print("store_results starting:", datetime.now())
    
    if data_to_insert:
        # look at the first result element of the data_to_insert list and see if the first 2 characters of result[0] are 'wr'
        if data_to_insert and data_to_insert[0][0][:2].lower() == 'wr':
            print("Processing World Ranking Event results")
            wr_flag = True
        else:
            print("Processing non-World Ranking Event results")
            wr_flag = False

        prev_event = ''
        with connection.cursor() as cursor:
            for result in data_to_insert:

                select_query = "SELECT * FROM `results` WHERE `race_code` = %s and full_name = %s" 
                cursor.execute(select_query, (result[0], result[2]))
                #connection.commit() 
                print("existing result check, time:", datetime.now())

                exists = cursor.fetchone() 
                if exists:
                    print(f"Result '{result[0]}{result[2]}' already exists in the database.") 
                else:
                    # Insert results data into results
                    insert_query = """ 
                    INSERT INTO results (race_code, place, full_name, race_time, race_points) 
                    VALUES (%s, %s, %s, %s, %s) 
                    """ 
                    cursor.execute(insert_query, result)

                    # Insert results data into results_static
                    insert_query = """ 
                    INSERT INTO results_static (race_code, place, full_name, race_time, race_points) 
                    VALUES (%s, %s, %s, %s, %s) 
                    """ 
                    cursor.execute(insert_query, result)
                    #connection.commit() 
                    print(f"WRE '{result[0]}{result[2]}' resutls inserted")
                    print("insert result time:", datetime.now())

                    # check if athlete exists.  If not, add them to the athletes table 
                    # Check if the athlete exists 
                    select_query = "SELECT * FROM `athletes` WHERE `full_name` = %s" 
                    cursor.execute(select_query, result[2]) 
                    #connection.commit()
                    print("check athlete exists time:", datetime.now())
                
                    athlete_exists = cursor.fetchone() 
                    if not athlete_exists:
                        print(f"Athlete '{result[2]}' does not exist in the database.")
                        if wr_flag:
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
                            #connection.commit() 
                            print(f"Athlete '{result[0]}{result[2]}' has been added to the database.")
                            print("insert athlete time:", datetime.now())
                        else:
                            print("Not a WRE and athlete is not verified as AUS, so not adding athlete to database.")
                    else:
                        print(f"Athlete '{result[2]}' already exists in the database.") 

                        if result[0] != prev_event:
                            # Fetch the event date
                            select_query = "SELECT date FROM events WHERE short_desc = %s"
                            cursor.execute(select_query, result[0])
                            #connection.commit()

                            print("fetch event date result time:", datetime.now())
                            event_date = cursor.fetchone()
                        prev_event = result[0]
                        if event_date:
                            update_query = """
                                UPDATE athletes
                                SET last_event_date = %s
                                WHERE IFNULL(last_event_date, '0000-01-01') < %s
                                AND full_name = %s
                                """

                            cursor.execute(update_query, (event_date['date'], event_date['date'], result[2]))
                            #connection.commit() 
                            print(f"Athlete '{result[2]}' last update date has been modified to '{event_date['date']}'.")
                            print("update athlete time:", datetime.now())

                        else:
                            print(f"event '{result[0]}' not in database")

            connection.commit()

    print("store_results finished!")


# def store_new_results(data_to_insert):
#     """
#     Stores new results not validated as Australian.
#     This differs from store_results_from_WRE in that it does not check if the athlete is eligible.
#     So, we can not add the athlete to the athletes table until we know more information about the athlete's nationality.
    
#     This function processes a list of results, checks if each result already exists in the database,
#     and inserts new results if they do not exist. It also checks if the athlete associated with each
#     result exists in the database, and inserts new athletes if they do not exist. Additionally, it
#     updates the last event date for each athlete.
#     Args:
#         data_to_insert (list of tuples): A list of tuples where each tuple contains the following
#                                          information about a result:
#                                          (race_code, place, full_name, race_time, race_points).
#     Returns:
#         None
#     """
#     print("store_results starting:", datetime.now())
#     prev_event = ''
#     with connection.cursor() as cursor:
#         for result in data_to_insert:

#             select_query = "SELECT * FROM `results` WHERE `race_code` = %s and full_name = %s" 
#             cursor.execute(select_query, (result[0], result[2]))
#             #connection.commit() 
#             print("existing result check, time:", datetime.now())

#             exists = cursor.fetchone() 
#             if exists:
#                 print(f"Result '{result[0]}{result[2]}' already exists in the database.") 
#             else:
#                 # Insert results data 
#                 insert_query = """ 
#                 INSERT INTO results (race_code, place, full_name, race_time, race_points) 
#                 VALUES (%s, %s, %s, %s, %s) 
#                 """ 
#                 cursor.execute(insert_query, result)

#                 # Insert results data into results_static
#                 insert_query = """ 
#                 INSERT INTO results_static (race_code, place, full_name, race_time, race_points) 
#                 VALUES (%s, %s, %s, %s, %s) 
#                 """ 
#                 cursor.execute(insert_query, result)
#                 #connection.commit() 
#                 print(f"WRE '{result[0]}{result[2]}' resutls inserted")
#                 print("insert result time:", datetime.now())

#                 # check if athlete exists.  If not, add them to the athletes table 
#                 # Check if the athlete exists 
#                 select_query = "SELECT * FROM `athletes` WHERE `full_name` = %s" 
#                 cursor.execute(select_query, result[2]) 
#                 #connection.commit()
#                 print("check athlete exists time:", datetime.now())
               
#                 athlete_exists = cursor.fetchone() 
#                 if athlete_exists:
#                     print(f"Athlete '{result[2]}' already exists in the database.") 

#                     if result[0] != prev_event:
#                         # Fetch the event date
#                         select_query = "SELECT date FROM events WHERE short_desc = %s"
#                         cursor.execute(select_query, result[0])
#                         #connection.commit()

#                         print("fetch event date result time:", datetime.now())
#                         event_date = cursor.fetchone()
#                     prev_event = result[0]
#                     if event_date:
#                         update_query = """
#                             UPDATE athletes
#                             SET last_event_date = %s
#                             WHERE IFNULL(last_event_date, '0000-01-01') < %s
#                             AND full_name = %s
#                             """

#                         cursor.execute(update_query, (event_date['date'], event_date['date'], result[2]))
#                         #connection.commit() 
#                         print(f"Athlete '{result[2]}' last update date has been modified to '{event_date['date']}'.")
#                         print("update athlete time:", datetime.now())

#                     else:
#                         print(f"event '{result[0]}' not in database")

#         connection.commit()

#     print("store_results finished!")


def update_event_ip(race_code, ip):
    with connection.cursor() as cursor:
        update_query = "UPDATE events SET ip = %s WHERE short_desc = %s"
        cursor.execute(update_query, (ip, race_code))
        connection.commit()
        print("Event IP updated successfully!")