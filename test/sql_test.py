import psycopg2

def execute_query(query):
    print("\n\n", query, "\n\n")
    db_params = {
        'dbname': 'lanyard',
        'user': 'postgres',
        'password': 'password',
        'host': 'localhost',
        'port': '5432',
    }

    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()

    try:
        cursor.execute(query)

        if cursor.description: 
            result = cursor.fetchall()
        else:
            result = None

    except Exception as e:
        print(f"Error executing query: {e}")
        result = None

    finally:
        cursor.close()
        conn.close()

    return result

data = execute_query("SELECT\n  p.name AS product_name,\n  pc.price AS customization_price,\n  ls.name AS lanyard_size,\n  c.name AS color,\n  a.name AS attachment,\n  ss.name AS stitch_style,\n  u.name AS upgrade\nFROM products AS p\nJOIN productcustomizations AS pc\n  ON p.id = pc.product_id\nJOIN lanyardsizes AS ls\n  ON pc.size_id = ls.id\nJOIN colors AS c\n  ON pc.color_id = c.id\nJOIN attachments AS a\n  ON pc.attachment_id = a.id\nJOIN stitchstyles AS ss\n  ON pc.stitch_id = ss.id\nJOIN upgrades AS u\n  ON pc.upgrade_id = u.id\nWHERE\n  p.name LIKE '%Nylon Lanyard%';")
print(data)
