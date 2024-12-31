from dotenv import load_dotenv
import os

load_dotenv()

def get_db_params():
    return {
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT'),
        # 'sslmode':os.getenv('DB_SSL_MODE')
    }
