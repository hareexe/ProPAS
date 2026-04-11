import pandas as pd
from sqlalchemy import create_engine, inspect

# --- CONFIGURATION ---
# Local SQLite settings
LOCAL_DB_PATH = 'propas.db' 
TABLES_TO_MIGRATE = ['proposal_messages']

# Railway MySQL settings (Update these with your current Railway credentials)
RAILWAY_USER = 'root'
RAILWAY_PASSWORD = 'AgBgFrnfYiVzaOJJPTXoNeHXBdmGWdLA'
RAILWAY_HOST = 'maglev.proxy.rlwy.net'
RAILWAY_PORT = '19932'
RAILWAY_DB_NAME = 'railway'

def migrate_database():
    try:
        # 1. Create database engines
        local_engine = create_engine(f'sqlite:///{LOCAL_DB_PATH}')
        
        # Railway Connection String (MySQL)
        railway_url = f"mysql+pymysql://{RAILWAY_USER}:{RAILWAY_PASSWORD}@{RAILWAY_HOST}:{RAILWAY_PORT}/{RAILWAY_DB_NAME}"
        railway_engine = create_engine(railway_url)

        # 2. Inspect local DB and migrate only the explicitly selected tables
        inspector = inspect(local_engine)
        available_tables = inspector.get_table_names()
        print(f"Found tables: {available_tables}")

        tables = [table for table in TABLES_TO_MIGRATE if table in available_tables]
        missing_tables = [table for table in TABLES_TO_MIGRATE if table not in available_tables]

        if missing_tables:
            print(f"Skipping missing tables: {missing_tables}")

        if not tables:
            print("No matching tables to migrate.")
            return

        print(f"Tables selected for migration: {tables}")

        # 3. Migrate each table
        for table in tables:
            print(f"Migrating table: {table}...")
            
            # Read data from SQLite
            df = pd.read_sql_table(table, local_engine)
            
            # Write data to Railway. Only the selected table is replaced.
            df.to_sql(table, railway_engine, if_exists='replace', index=False)
            
            print(f"Successfully migrated {len(df)} rows to '{table}'.")

        print("\nDatabase migration completed successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    migrate_database()
