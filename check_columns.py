import pyodbc
import config

conn_string = config.get_conn_string()
try:
    conn = pyodbc.connect(conn_string)
    cursor = conn.cursor()
    cursor.execute("SELECT TOP 1 * FROM dok_Pozycja")
    columns = [col[0] for col in cursor.description]
    print("Columns in dok_Pozycja:")
    print(columns)
    
    cursor.execute("SELECT TOP 1 * FROM dok__Dokument")
    columns_dok = [col[0] for col in cursor.description]
    print("\nColumns in dok__Dokument:")
    print(columns_dok)
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
