import pandas as pd
from database_connection import connection
from datetime import datetime, timedelta, date
import logging
import pytz  # Import pytz for timezone handling
import re

# Ensure Sydney timezone is used
sydney_tz = pytz.timezone('Australia/Sydney')  # Use pytz to get the Sydney timezone

def str_to_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d')

def convert_place(place):
    cleaned_place = place.strip().replace('\xa0', '')
    if cleaned_place:
        return int(cleaned_place)
    return None

def parse_race_time(race_time_str):
    if race_time_str:
        #print(race_time_str)
        if not any(char.isdigit() for char in race_time_str):
            minutes = 0
            seconds = 0
        else:
            if race_time_str.count(':') == 1:
                minutes, seconds = map(int, race_time_str.split(':'))
            elif race_time_str.count(':') == 2:
                hours, minutes, seconds = map(int, race_time_str.split(':'))
                minutes += hours * 60
    else:
        minutes = 0
        seconds = 0
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
        cursor.execute(query, (year))
        connection.commit()
        print(f"Disciplines updated for { year }")
    


def delete_from_event_stats(id):
    with connection.cursor() as cursor:
        query = "DELETE FROM event_stats WHERE id = %s"
        cursor.execute(query, (id,))
        connection.commit()
        print("event_stats data deleted successfully!")


def delete_from_race_tmp(short_desc):
    with connection.cursor() as cursor:
        query = "DELETE FROM race_tmp WHERE race_code = %s"
        cursor.execute(query, (short_desc,))
        connection.commit()
        print("race_tmp data deleted successfully!")

def delete_from_results(short_desc):
    with connection.cursor() as cursor:
        query1 = "DELETE FROM results WHERE race_code = %s"
        # query2 = "DELETE FROM results_static WHERE race_code = %s"
        cursor.execute(query1, (short_desc,))
        # cursor.execute(query2, (short_desc,))
        connection.commit()
        print("results data deleted successfully!")


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

        # Check if the row already exists
        select_query = "SELECT * FROM event_stats WHERE id = %s"
        cursor.execute(select_query, (event_id,))
        exists = cursor.fetchone()

        if exists:
            print(f"Event statistics for id '{event_id}' already exist in the database.")
        else:
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
            result['race_points'],
            result['race_points']  #additional column for race_points_static
        )
        for result in race_times
    ]
    #print(new_result_data)
    store_new_results(new_result_data)




def load_athletes_from_db():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM athletes LEFT JOIN clubs ON athletes.club_id = clubs.id WHERE nationality_code = 'AUS' AND last_event_date is not NULL order by last_event_date desc, athletes.family, athletes.given")
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


def load_age_grade_records_lists():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        query = """
            SELECT 
                age,
                athlete_id,
                full_name,
                discipline,
                list,
                ranking_points,
                age_adjustment,
                snapshot_date
            FROM age_records
            ORDER BY 
                list, 
                discipline, 
                age;
         """
        cursor.execute(query)
        athletes = cursor.fetchall()
        return athletes

    

def load_approaching_milestones():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        query = """
            WITH all_races AS (
                SELECT 
                    a.id AS athlete_id, 
                    a.full_name, 
                    e.list, 
                    'All' AS discipline, 
                    e.date, 
                    e.long_desc, 
                    ROW_NUMBER() OVER (PARTITION BY a.id, e.list ORDER BY e.date) AS race_count
                FROM 
                    athletes a
                INNER JOIN 
                    results r ON a.full_name = r.full_name
                INNER JOIN 
                    events e ON e.short_desc = r.race_code
                WHERE 
                    a.eligible = 'Y'
                UNION ALL
                SELECT 
                    a.id AS athlete_id, 
                    a.full_name, 
                    e.list, 
                    e.discipline, 
                    e.date, 
                    e.long_desc, 
                    ROW_NUMBER() OVER (PARTITION BY a.id, e.list, e.discipline ORDER BY e.date) AS race_count
                FROM 
                    athletes a
                INNER JOIN 
                    results r ON a.full_name = r.full_name
                INNER JOIN 
                    events e ON e.short_desc = r.race_code
                WHERE 
                    a.eligible = 'Y'
            ),
            ranked_races AS (
                SELECT 
                    athlete_id, 
                    full_name, 
                    list, 
                    discipline, 
                    date, 
                    long_desc, 
                    race_count, 
                    RANK() OVER (PARTITION BY athlete_id, list, discipline ORDER BY race_count DESC) AS rank_position
                FROM 
                    all_races
            )
            SELECT *
            FROM ranked_races
            WHERE rank_position = 1
                AND date > DATE_SUB(CURRENT_DATE, INTERVAL 90 DAY)
                AND (
                    race_count + 1 IN (10, 25, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500)
                    OR race_count + 2 IN (10, 25, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500)
                    OR race_count + 3 IN (10, 25, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500)
                )
            ORDER BY race_count DESC
         """
        cursor.execute(query)
        athletes = cursor.fetchall()
        return athletes



def load_athlete_ranking_history(athlete_id, effective_date):
    connection.autocommit(True)
    with connection.cursor() as cursor:
        query = """
            SELECT snapshot_date, discipline, list, ranking, ranking_points FROM ranking_history 
            WHERE athlete_id = %s and snapshot_date <= %s
            ORDER BY snapshot_date
        """
        cursor.execute(query, (athlete_id, effective_date))
        data = cursor.fetchall()
        return data

# load athletes from db where IOF ID is not null and photo is null
def load_athletes_with_iof_id():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        query = "SELECT * FROM athletes WHERE iof_id IS NOT NULL AND has_iof_photo = 'Y'"
        cursor.execute(query)
        data = cursor.fetchall()
        athletes = []
        for row in data:
            athletes.append(row)
    return athletes


def load_event_date(race_code):
    query = "SELECT id, date, ip, list from events WHERE short_desc = %s"
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
    query2 = """
        SELECT results.race_code, results.place, results.full_name, results.race_time, results.race_points_static as race_points,
        athletes.id as athlete_id, athletes.eligible, clubs.* 
        FROM results
        LEFT JOIN athletes ON results.full_name = athletes.full_name 
        LEFT JOIN clubs ON athletes.club_id = clubs.id 
        WHERE results.race_code = %s 
        ORDER BY place
        """
    
    if not short_file:
        raise ValueError("The short_file parameter is None or empty.")
    
    try:
        connection.autocommit(True)
        with connection.cursor() as cursor:
            #logging.debug(f"Executing query1: {query1} with parameter: {short_file}")
            cursor.execute(query1, (short_file,))
            event = cursor.fetchone()

            results = []
            if event:
                #logging.debug(f"Executing query2: {query2} with parameter: {short_file}")
                cursor.execute(query2, (short_file,))
                data = cursor.fetchall()
                for row in data:
                    results.append(row)

            return event, results
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise


def load_events_from_db():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM events order by date desc")
        result = cursor.fetchall()
        events = []
        for row in result:
            events.append(row)
        
        # Load race codes data 
        cursor.execute("SELECT DISTINCT race_code FROM results") 
        result = cursor.fetchall()
        race_codes = []
        for row in result:
            race_codes.append(row['race_code'].lower())
        return events, race_codes

def load_high_scores_lists():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        query = """
            SELECT a.id as athlete_id, a.full_name, e.list, e.discipline, e.date, e.long_desc, e.short_desc, r.race_points as race_points
            FROM athletes a
            INNER JOIN results r ON a.full_name = r.full_name
            INNER JOIN events e ON e.short_desc = r.race_code
            WHERE a.eligible = 'Y'
            and (cast(r.race_points as float) > 1100 and e.list like 'junior%' or cast(r.race_points as float)>1200)
            order by cast(r.race_points as float) desc
        """
        cursor.execute(query)
        athletes = cursor.fetchall()
        return athletes



def load_participation_lists():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        query = """
            SELECT a.id as athlete_id, a.full_name, e.list, e.discipline, count(*) as races, YEAR(e.date) as year
            FROM athletes a
            INNER JOIN results r ON a.full_name = r.full_name
            INNER JOIN events e ON e.short_desc = r.race_code
            WHERE a.eligible = 'Y'
            GROUP BY a.id, a.full_name, e.list, e.discipline, YEAR(e.date) 
        """
        cursor.execute(query)
        athletes = cursor.fetchall()
        return athletes


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
            WITH ranked_results AS (
                SELECT 
                    r.full_name,
                    e.date,
                    e.long_desc, 
                    e.short_desc, 
                    CAST(r.race_points AS UNSIGNED) AS race_points,
                    ROW_NUMBER() OVER (PARTITION BY r.full_name ORDER BY CAST(r.race_points AS UNSIGNED) DESC) AS rn
                FROM results r
                INNER JOIN events e ON r.race_code = e.short_desc
                JOIN (
                    SELECT full_name, MAX(CAST(race_points AS UNSIGNED)) AS max_race_points
                    FROM results 
                    GROUP BY full_name
                ) AS max_results
                ON r.full_name = max_results.full_name AND CAST(r.race_points AS UNSIGNED) = max_results.max_race_points
            ),
            stats as (
                SELECT 
                    results.full_name,
                    athletes.id AS athlete_id,
                    COUNT(results.id) AS race_count,
                    SUM(race_points) AS total_points,
                    AVG(CASE WHEN race_points > 0 THEN race_points END) AS avg_points,
                    MAX(CAST(race_points AS UNSIGNED)) AS max_points,
                    MIN(place) AS best_place,
                    COUNT(CASE WHEN place = 1 THEN 1 END) AS race_wins,
                    ROUND(COUNT(CASE WHEN race_points = 0 THEN 1 END) / COUNT(results.id) * 100, 1) AS dnf_rate,
                    MIN(events.date) AS since_date
                FROM results
                INNER JOIN athletes ON results.full_name = athletes.full_name
                INNER JOIN events ON results.race_code = events.short_desc
                WHERE athletes.eligible <> 'N'
                GROUP BY results.full_name, athletes.id
                
            )

            SELECT 
                stats.full_name,
                stats.athlete_id,
                stats.race_count,
                stats.total_points,
                stats.avg_points,
                stats.max_points,
                stats.best_place,
                stats.race_wins,
                stats.dnf_rate,
                stats.since_date,
                rr.date as max_points_date, rr.long_desc as max_points_event, rr.short_desc as max_points_code
            FROM stats
            INNER JOIN ranked_results rr ON stats.full_name = rr.full_name
            WHERE rr.rn = 1
            ORDER BY race_count DESC
        """
        cursor.execute(query)
        result = cursor.fetchall()
        return result
                      

def load_rankings_from_db(effective_date, age_grade=False):
    if effective_date is None:
        effective_date = datetime.now(sydney_tz).date()
    effective_date_str = effective_date.strftime('%Y-%m-%d')
    connection.autocommit(True)
    if age_grade:
        select_query = """
            SELECT 
                results.race_points,
                results.full_name,
                athletes.id AS athlete_id,
                athletes.yob,
                athletes.iof_id,
                athletes.has_iof_photo,
                age_grades.age_adjustment,
                events.date,
                events.list,
                events.discipline,
                clubs.club_name,
                clubs.state
            FROM
                results
                INNER JOIN	athletes ON results.full_name = athletes.full_name	AND athletes.eligible = 'Y'
                INNER JOIN	events ON results.race_code = events.short_desc
                LEFT JOIN	clubs ON athletes.club_id = clubs.id
                LEFT JOIN age_grades ON athletes.gender = age_grades.gender AND  (year(%s) - athletes.yob) = age_grades.age
            WHERE
                events.date <= %s
            ORDER BY athletes.id;
                        """
    else:
        select_query = """
            SELECT 
                results.race_points,
                results.full_name,
                athletes.id AS athlete_id,
                athletes.yob,
                athletes.iof_id,
                athletes.has_iof_photo,
                events.date,
                events.list,
                events.discipline,
                clubs.club_name,
                clubs.state
            FROM
                results
                INNER JOIN	athletes ON results.full_name = athletes.full_name	AND athletes.eligible = 'Y'
                INNER JOIN	events ON results.race_code = events.short_desc
                LEFT JOIN	clubs ON athletes.club_id = clubs.id
            WHERE
                events.date <= %s
            ORDER BY athletes.id;
                        """
    with connection.cursor() as cursor:
        if age_grade:
            cursor.execute(select_query, (effective_date_str, effective_date_str) )
        else:
            cursor.execute(select_query, effective_date_str )
        result = cursor.fetchall()
        rankings = []
        for row in result:
            # if isinstance(row, dict) and row.get('full_name'):
            #     row['full_name'] = row['full_name'].title()
            rankings.append(row)
        return rankings


def load_ranking_leaders_lists():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        query = """
            SELECT snapshot_date, discipline, list, athlete_id, full_name, ranking, ranking_points FROM ranking_history
            where ranking = 1
            order by list, discipline, snapshot_date desc
        """
        cursor.execute(query)
        athletes = cursor.fetchall()
        return athletes




def load_recent_milestones():
    connection.autocommit(True)
    with connection.cursor() as cursor:
        query = """
            select * from
            (
                SELECT 
                    a.id AS athlete_id, 
                    a.full_name, 
                    e.list, 
                    'All' as discipline, 
                    e.date, 
                    e.long_desc, 
                    a.iof_id,
                    a.has_iof_photo,
                    ROW_NUMBER() OVER (PARTITION BY a.id, e.list ORDER BY e.date) AS race_count
                FROM 
                    athletes a
                INNER JOIN 
                    results r ON a.full_name = r.full_name
                INNER JOIN 
                    events e ON e.short_desc = r.race_code
                WHERE 
                    a.eligible = 'Y'
                UNION ALL
                SELECT 
                    a.id AS athlete_id, 
                    a.full_name, 
                    e.list, 
                    e.discipline, 
                    e.date, 
                    e.long_desc, 
                    a.iof_id,
                    a.has_iof_photo,
                    ROW_NUMBER() OVER (PARTITION BY a.id, e.list, e.discipline ORDER BY e.date) AS race_count
                FROM 
                    athletes a
                INNER JOIN 
                    results r ON a.full_name = r.full_name
                INNER JOIN 
                    events e ON e.short_desc = r.race_code
                WHERE 
                    a.eligible = 'Y'
                ORDER BY 
                    athlete_id, list, discipline, date, race_count
            ) all_races
            where date > DATE_SUB(CURRENT_DATE, INTERVAL 90 DAY)
                and race_count in (10, 25, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500)
            order by race_count desc, discipline, has_iof_photo desc
        """
        cursor.execute(query)
        athletes = cursor.fetchall()
        return athletes


def load_results_by_athlete(full_name, effective_date):
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM results INNER JOIN events ON results.race_code = events.short_desc WHERE results.full_name = %s and events.date <= %s ORDER BY events.date DESC;", (full_name, effective_date))
        result = cursor.fetchall()
        results = []
        for row in result:
            results.append(row)
        return results


def load_results_for_all_athletes(effective_date):
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT events.date, results.race_points, events.list, events.discipline, results.full_name, athletes.yob FROM results INNER JOIN events ON results.race_code = events.short_desc INNER JOIN athletes ON athletes.full_name = results.full_name WHERE athletes.eligible = 'Y' and events.date <= %s ORDER BY events.date DESC;", effective_date)
        result = cursor.fetchall()
        results = []
        for row in result:
            # if isinstance(row, dict) and row.get('full_name'):
            #     row['full_name'] = row['full_name'].title()
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


def reload_age_records():
    with connection.cursor() as cursor:
        # Define the query with a placeholder 
        truncate_query = """
            TRUNCATE TABLE age_records;
            """ 
        #Execute the query with the parameter 
        cursor.execute(truncate_query) 
        connection.commit()

        insert_query = """
            insert into age_records
            select * from
            (
                        WITH RankedData AS (
                            SELECT 
                                ag.age,
                                a.id as athlete_id,
                                a.full_name,
                                a.yob,
                                rh.snapshot_date,
                                rh.discipline,
                                rh.list,
                                rh.ranking_points,
                                ag.age_adjustment,
                                ROW_NUMBER() OVER (
                                    PARTITION BY ag.age, rh.discipline, rh.list 
                                    ORDER BY rh.ranking_points DESC
                                ) AS my_rank
                            FROM ranking_history rh
                            INNER JOIN athletes a 
                                ON a.id = rh.athlete_id AND a.yob IS NOT NULL
                            INNER JOIN age_grades ag 
                                ON ag.gender = a.gender 
                                AND ag.age = YEAR(rh.snapshot_date) - a.yob
                            WHERE rh.ranking_points > (3500 * ag.age_adjustment ) 
                                AND YEAR(rh.snapshot_date) > a.yob
                        )
                        SELECT 
                            age,
                            list,
                            discipline,
                            athlete_id,
                            full_name,
                            ranking_points,
                            age_adjustment,
                            snapshot_date
                        FROM RankedData
                        WHERE my_rank = 1
                        ORDER BY 
                            list, 
                            discipline, 
                            age
            ) age_records_tmp
            """
        #Execute the query with the parameter 
        cursor.execute(insert_query) 
        connection.commit()

        print("Age records updated successfully!")



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
    #print(new_event_data)
    store_events(new_event_data)
    #print("Finished storing new events:", datetime.now())

    new_result_data = [
        (
            result['race_code'],
            convert_place(result['place']),
            result['athlete_name'],
            parse_race_time(result['race_time']),
            result['race_points'],
            result['race_points']  #additional column for race_points_static
        )
        for result in new_results
    ]
    #print(new_result_data)
    store_new_results(new_result_data)
    #print("Finished storing new results:", datetime.now())



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

        #print(modified_data_to_insert)

        # Insert data one row at a time
        for row in modified_data_to_insert:

            cursor.execute(select_query, (row[1], row[6]))
            exists = cursor.fetchone()
            if not exists:
                #print(f"Inserting row: {row}")
                cursor.execute(insert_query, (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]))
                #print(f"Inserted row: {row}")
            else:
                print(f"Row already exists: {row}")

        connection.commit()
        #print("Data inserted successfully! Remember to review Discipline using mySQL Workbench.")



def store_events(data_to_insert):
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
                
                #print(event)

                cursor.execute(insert_query, event) 
        connection.commit() 
        #print("Data inserted successfully!")



def store_race_from_excel(sheetname, data_to_insert):
    #print(f"Storing race from excel worksheet { sheetname }")
    #print(data_to_insert)
    with connection.cursor() as cursor:
        # Set race_points to 0 if it is None
        data_to_insert = [(place, full_name, race_time, 0 if race_points is None else race_points) for place, full_name, race_time, race_points in data_to_insert]

        # Define the select query to check if the row exists
        select_query = "SELECT * FROM results WHERE race_code = %s AND full_name = %s"

        # Define the insert queries
        insert_query_results = """ 
        INSERT INTO results (race_code, place, full_name, race_time, race_points, race_points_static) 
        VALUES (%s, %s, %s, %s, %s, %s) 
        """
        # insert_query_results_static = """ 
        # INSERT INTO results_static (race_code, place, full_name, race_time, race_points) 
        # VALUES (%s, %s, %s, %s, %s) 
        # """

        # Insert data one row at a time if it does not already exist
        for place, full_name, race_time, race_points in data_to_insert:
            cursor.execute(select_query, (sheetname, full_name))
            exists = cursor.fetchone()
            if not exists:
                cursor.execute(insert_query_results, (sheetname, place, full_name, race_time, race_points, race_points))
                # cursor.execute(insert_query_results_static, (sheetname, place, full_name, race_time, race_points))
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
        #print("Data inserted successfully!")


def store_race_tmp_from_excel(sheetname, data_to_insert):
    with connection.cursor() as cursor:
        # Set race_points to 0 if it is None
        data_to_insert = [(place, full_name, race_time, 0 if race_points is None else race_points) for place, full_name, race_time, race_points in data_to_insert]

        # Define the select query to check if the row exists
        select_query = "SELECT * FROM results WHERE race_code = %s AND full_name = %s"

        # Define the insert queries
        insert_query_results = """ 
        INSERT INTO race_tmp (race_code, place, full_name, race_time, race_points) 
        VALUES (%s, %s, %s, %s, %s) 
        """
        # insert_query_results_static = """ 
        # INSERT INTO results_static (race_code, place, full_name, race_time, race_points) 
        # VALUES (%s, %s, %s, %s, %s) 
        # """

        # Insert data one row at a time if it does not already exist
        for place, full_name, race_time, race_points in data_to_insert:
            cursor.execute(select_query, (sheetname, full_name))
            exists = cursor.fetchone()
            if not exists:
                cursor.execute(insert_query_results, (sheetname, place, full_name, race_time, race_points))
                # cursor.execute(insert_query_results_static, (sheetname, place, full_name, race_time, race_points))
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
        #print("Data inserted successfully!")



def store_race_tmp(short_desc, data_to_insert):
    #print(f"store_race_tmp starting for {short_desc}")
    with connection.cursor() as cursor:
        
        # Set race_points to 0 if it is None
        data_to_insert = [(place, full_name, race_time, 0 if race_points is None else race_points) for place, full_name, race_time, race_points in data_to_insert]

        # Define the select query to check if the row exists
        select_query = "SELECT * FROM race_tmp WHERE race_code = %s AND full_name = %s"

        # Define the insert queries
        insert_query_results = """ 
        INSERT INTO race_tmp (race_code, place, full_name, race_time, race_points) 
        VALUES (%s, %s, %s, %s, %s) 
        """
        # insert_query_results_static = """ 
        # INSERT INTO results_static (race_code, place, full_name, race_time, race_points) 
        # VALUES (%s, %s, %s, %s, %s) 
        # """

        # Insert data one row at a time if it does not already exist
        for place, full_name, race_time, race_points in data_to_insert:
            cursor.execute(select_query, (short_desc, full_name))
            exists = cursor.fetchone()
            if not exists:
                cursor.execute(insert_query_results, (short_desc, place, full_name, race_time, race_points))
                #cursor.execute(insert_query_results_static, (sheetname, place, full_name, race_time, race_points))
                #print(f"Inserted row: {(short_desc, place, full_name, race_time, race_points)}")
            else:
                print(f"Row already exists: {(short_desc, place, full_name, race_time, race_points)}")

        # Fetch the event date
        select_query_event_date = "SELECT date FROM events WHERE short_file = %s"
        cursor.execute(select_query_event_date, (short_desc,))
        event_date = cursor.fetchone()
        if event_date:
            #print(f"event date: {event_date}")
            for item in data_to_insert:
                update_query = """
                    UPDATE athletes
                    SET last_event_date = %s
                    WHERE IFNULL(last_event_date, '0000-01-01') < %s
                    AND full_name = %s
                    """
                cursor.execute(update_query, (event_date['date'], event_date['date'], item[1]))
        else:
            print("event date not found for %s" % short_desc)

        connection.commit()
        #print("Data inserted successfully!")

###########################################################################################################

def store_ranking_in_db(final_aggregated_athletes, ranking_date):

    print("store_ranking_in_db starting:", datetime.now())

    for discipline in final_aggregated_athletes:
        ranking_date_str = ranking_date.strftime('%Y-%m-%d')

        # Prepare a set of existing rankings to reduce database calls
        select_query = """
            SELECT athlete_id, lower(discipline) as discipline, lower(list) as list
            FROM ranking_history
            WHERE snapshot_date = %s
        """
        existing_rankings = set()
        with connection.cursor() as cursor:
            cursor.execute(select_query, (ranking_date_str,))
            for row in cursor.fetchall():
                existing_rankings.add((row['athlete_id'], row['discipline'], row['list']))

        # Prepare bulk insert data
        insert_data = []
        for athlete in final_aggregated_athletes[discipline]:
            key = (athlete['athlete_id'], discipline.lower(), athlete['list'].lower())
            if key not in existing_rankings:
                insert_data.append((
                    ranking_date_str,
                    discipline,
                    athlete['list'],
                    athlete['athlete_id'],
                    athlete['full_name'],
                    athlete['race_points_rank'],
                    athlete['sum_top_5_race_points']
                ))

        # Perform bulk insert
        if insert_data:
            insert_query = """
            INSERT INTO ranking_history (
                snapshot_date,
                discipline,
                list,
                athlete_id,
                full_name,
                ranking,
                ranking_points
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            with connection.cursor() as cursor:
                cursor.executemany(insert_query, insert_data)
                connection.commit()
                print(f"Inserted {len(insert_data)} rankings for discipline {discipline} on date {ranking_date_str}")
    print("store_ranking_in_db finished:", datetime.now())


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
            #print("Processing World Ranking Event results")
            wr_flag = True
        else:
            #print("Processing non-World Ranking Event results")
            wr_flag = False

        prev_event = ''
        with connection.cursor() as cursor:
            for result in data_to_insert:

                select_query = "SELECT * FROM `results` WHERE `race_code` = %s and full_name = %s" 
                cursor.execute(select_query, (result[0], result[2]))
                #connection.commit() 
                #print("existing result check, time:", datetime.now())

                exists = cursor.fetchone() 
                if exists:
                    print(f"Result '{result[0]}{result[2]}' already exists in the database.") 
                else:
                    # Insert results data into results
                    insert_query = """ 
                    INSERT INTO results (race_code, place, full_name, race_time, race_points, race_points_static) 
                    VALUES (%s, %s, %s, %s, %s, %s) 
                    """ 
                    cursor.execute(insert_query, result)

                    # Insert results data into results_static
                    # insert_query = """ 
                    # INSERT INTO results_static (race_code, place, full_name, race_time, race_points) 
                    # VALUES (%s, %s, %s, %s, %s) 
                    # """ 
                    # cursor.execute(insert_query, result)

                    #connection.commit() 
                    #print(f"WRE '{result[0]}{result[2]}' resutls inserted")
                    #print("insert result time:", datetime.now())

                    # check if athlete exists.  If not, add them to the athletes table 
                    # Check if the athlete exists 
                    select_query = "SELECT * FROM `athletes` WHERE `full_name` = %s" 
                    cursor.execute(select_query, result[2]) 
                    #connection.commit()
                    #print("check athlete exists time:", datetime.now())
                
                    athlete_exists = cursor.fetchone() 
                    if not athlete_exists:
                        #print(f"Athlete '{result[2]}' does not exist in the database.")
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
                            #print(f"Athlete '{result[0]}{result[2]}' has been added to the database.")
                            #print("insert athlete time:", datetime.now())
                        # else:
                        #     print("Not a WRE and athlete is not verified as AUS, so not adding athlete to database.")
                    else:
                        #print(f"Athlete '{result[2]}' already exists in the database.") 

                        if result[0] != prev_event:
                            # Fetch the event date
                            select_query = "SELECT date FROM events WHERE short_desc = %s"
                            cursor.execute(select_query, result[0])
                            #connection.commit()

                            #print("fetch event date result time:", datetime.now())
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
                            #print(f"Athlete '{result[2]}' last update date has been modified to '{event_date['date']}'.")
                            #print("update athlete time:", datetime.now())

                        else:
                            print(f"event '{result[0]}' not in database")

            connection.commit()

    print("store_results finished!")


def test_race_exist(race_code):
    race_exists = False
    connection.autocommit(True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT * from events where short_desc = %s ", race_code)
        result = cursor.fetchone()
        if result:
            race_exists = True
    return race_exists

def update_athletes_with_iof_ids(athletes):
    with connection.cursor() as cursor:
        for athlete in athletes:
            update_query = "UPDATE athletes SET iof_id = %s WHERE full_name = %s and iof_id is null"
            cursor.execute(update_query, (athlete['iof_id'], athlete['full_name']))
        connection.commit()
        print("Athletes updated successfully!")

# Update athlete record with has_iof_photo flag = 'Y'
def update_athlete_photo(athlete_iof_id):
    with connection.cursor() as cursor:
        update_query = "UPDATE athletes SET has_iof_photo = 'N' WHERE iof_id = %s"
        cursor.execute(update_query, (athlete_iof_id,))
        connection.commit()
        print("Athlete photo updated successfully!")


def update_event_ip(race_code, ip):
    with connection.cursor() as cursor:
        update_query = "UPDATE events SET ip = %s WHERE short_desc = %s"
        cursor.execute(update_query, (ip, race_code))
        connection.commit()
        #print("Event IP updated successfully!")


def update_results_titlecase():
    with connection.cursor() as cursor:

        # Fetch rows with 3 or more consecutive uppercase characters
        cursor.execute("SELECT id, full_name FROM results WHERE full_name COLLATE utf8mb4_bin REGEXP '[A-Z]{3,}';")
        rows = cursor.fetchall()

        # Helper function to convert matched words to Title case
        def convert_to_title_case(full_name):
            return re.sub(r'\b([A-Z]{3,}\w*)\b', lambda match: match.group(0).capitalize(), full_name)

        # Process rows and update the database
        for row in rows:
            print(row)
            # Extract record ID and full name
            record_id = row['id']
            full_name = row['full_name']
            print(f"Updating record ID {record_id} with full name: {full_name}")
            # Convert to Title case
            updated_name = convert_to_title_case(full_name)
            print(f"{full_name} -> {updated_name}")
            # Update the record in the database
            cursor.execute("UPDATE results SET full_name = %s WHERE id = %s", (updated_name, record_id))

        # Commit changes
        connection.commit()

        #print("Results updated to titlecase!")