import sqlite3
from dotenv import load_dotenv
from psycopg_pool import ConnectionPool
import os

load_dotenv()

#TODO put these connection pool configurations in app.Config
pool = ConnectionPool(
  os.getenv("DB_DSN"),
  min_size=5,
  max_size=25,
  max_lifetime=3600, 
  max_idle=900,
  timeout=3
)

with pool.connection() as conn:
  with conn.cursor() as cur:
    cur.execute("SELECT 1")
    print(cur.fetchone())

'''
conn = sqlite3.connect('app.db')
cursor = conn.cursor()
cursor.execute("""
  UPDATE task SET complete = TRUE
""")

conn.commit()


cursor.execute("""
  SELECT username FROM user
""")
results = cursor.fetchall()
for result in results:
  print(result)
'''

def print_database_schema(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Get all user tables
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name;
    """)

    tables = cursor.fetchall()

    if not tables:
        print("No tables found.")
        return

    for (table_name,) in tables:
        print(f"\n{'=' * 60}")
        print(f"TABLE: {table_name}")
        print(f"{'=' * 60}")

        # Get column information
        cursor.execute(f"PRAGMA table_info('{table_name}')")
        columns = cursor.fetchall()

        print("\nColumns:")
        print(f"{'CID':<5} {'Name':<20} {'Type':<15} {'Not Null':<10} {'Default':<15} {'PK'}")

        for cid, name, col_type, notnull, default_value, pk in columns:
            print(
                f"{cid:<5} {name:<20} {col_type:<15} "
                f"{notnull:<10} {str(default_value):<15} {pk}"
            )

        # Row count
        cursor.execute(f"SELECT COUNT(*) FROM '{table_name}'")
        row_count = cursor.fetchone()[0]

        print(f"\nRows: {row_count}")

    conn.close()

'''
if __name__ == "__main__":
    database_file = "app.db"  # Change to your database file
    print_database_schema(database_file)
'''

