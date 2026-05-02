import os
from dotenv import load_dotenv

load_dotenv()

DB_SERVER = os.getenv("DB_SERVER")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

def get_conn_string():
    # Force ODBC Driver 18 with security overrides for local/dev environments
    # Added MultiSubnetFailover=Yes for better networking in some Docker setups
    return (
        f'DRIVER={{ODBC Driver 18 for SQL Server}};'
        f'SERVER={DB_SERVER};'
        f'DATABASE={DB_NAME};'
        f'UID={DB_USER};'
        f'PWD={DB_PASSWORD};'
        'Encrypt=no;'
        'TrustServerCertificate=yes;'
        'Connection Timeout=60;'
        'MultiSubnetFailover=No;'
    )
