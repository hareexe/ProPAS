import sqlite3
import pandas as pd
from sqlalchemy import create_engine

# Use your exact MYSQL_PUBLIC_URL from Railway
# Note the '+pymysql' part - it's very important!
PUBLIC_URL = "mysql+pymysql://root:axDhwyloZLpNaHhcigljHcNNyrBxlByf@maglev.proxy.rlwy.net:46514/railway"

def migrate():
    try:
        # 1. Connect to your local SQLite file
        print("Connecting to local SQLite...")
        sl_conn = sqlite3.connect("propas.db")
        
        # 2. Connect to Railway MySQL
        print("Connecting to Railway MySQL...")
        engine = create_engine(PUBLIC_URL)
        
        # 3. Get all table names from SQLite
        tables_query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        tables = pd.read_sql(tables_query, sl_conn)

        print(f"Found {len(tables)} tables. Starting migration...")

        for table_name in tables['name']:
            print(f"Migrating table: {table_name}...")
            
            # Read the data from SQLite
            df = pd.read_sql(f"SELECT * FROM {table_name}", sl_conn)
            
            # Write the data to MySQL
            # if_exists='replace' creates the table for you!
            df.to_sql(table_name, engine, if_exists='replace', index=False)

        print("✅ SUCCESS: All data migrated to Railway MySQL!")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        if 'sl_conn' in locals():
            sl_conn.close()

if __name__ == "__main__":
    migrate()