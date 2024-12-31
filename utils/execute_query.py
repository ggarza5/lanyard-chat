import psycopg2
import json
from config.db import get_db_params
from utils.serialize_result import serialize_result

def execute_query(query):

    db_params = get_db_params()
    print(db_params,'par')
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()

    try:
        cursor.execute(query)

        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
        else:
            result = None

    except Exception as e:
        print(f"Error executing query: {e}")
        result = None

    finally:
        cursor.close()
        conn.close()
    
    if result:
        result = serialize_result(result)
    
    return result
