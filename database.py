from database_connection import connection

def load_athletes_from_db():
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM athletes")
        result = cursor.fetchall()
        athletes = []
        for row in result:
            athletes.append(row)
        return athletes
