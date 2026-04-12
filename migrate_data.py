import json

import pandas as pd
from sqlalchemy import create_engine, inspect, text

from app import app
from models import db

# --- CONFIGURATION ---
# Local SQLite settings
LOCAL_DB_PATH = 'propas.db'

# Railway MySQL settings (Update these with your current Railway credentials)
RAILWAY_USER = 'root'
RAILWAY_PASSWORD = 'AgBgFrnfYiVzaOJJPTXoNeHXBdmGWdLA'
RAILWAY_HOST = 'maglev.proxy.rlwy.net'
RAILWAY_PORT = '19932'
RAILWAY_DB_NAME = 'railway'

TABLE_MIGRATION_ORDER = [
    'accounts',
    'approval_steps',
    'proposals',
    'document_approvals',
    'document_versions',
    'document_logs',
    'proposal_messages',
]
def _load_local_tables(local_engine, tables_to_migrate):
    local_data = {}
    for table_name in tables_to_migrate:
        df = pd.read_sql_table(table_name, local_engine)
        for column_name in df.columns:
            df[column_name] = df[column_name].apply(
                lambda value: json.dumps(value)
                if isinstance(value, (dict, list))
                else value
            )
        local_data[table_name] = df
    return local_data


def _sync_destination_tables(railway_engine, local_data, tables_to_migrate):
    with app.app_context():
        db.metadata.create_all(bind=railway_engine)

    with railway_engine.begin() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        try:
            for table_name in reversed(tables_to_migrate):
                connection.execute(text(f"DELETE FROM `{table_name}`"))

            for table_name in tables_to_migrate:
                df = local_data[table_name]
                print(f"Migrating table: {table_name}...")
                df.to_sql(table_name, connection, if_exists='append', index=False)
                print(f"Successfully migrated {len(df)} rows to '{table_name}'.")
        finally:
            connection.execute(text("SET FOREIGN_KEY_CHECKS=1"))


def migrate_database():
    try:
        local_engine = create_engine(f'sqlite:///{LOCAL_DB_PATH}')

        railway_url = (
            f"mysql+pymysql://{RAILWAY_USER}:{RAILWAY_PASSWORD}"
            f"@{RAILWAY_HOST}:{RAILWAY_PORT}/{RAILWAY_DB_NAME}"
        )
        railway_engine = create_engine(railway_url)

        inspector = inspect(local_engine)
        available_tables = inspector.get_table_names()
        print(f"Found tables: {available_tables}")

        ordered_tables = [table for table in TABLE_MIGRATION_ORDER if table in available_tables]
        extra_tables = [table for table in available_tables if table not in TABLE_MIGRATION_ORDER]
        tables_to_migrate = ordered_tables + extra_tables

        if not tables_to_migrate:
            print("No local tables found to migrate.")
            return

        print(f"Tables selected for migration: {tables_to_migrate}")
        print("Reading local data before touching Railway...")
        local_data = _load_local_tables(local_engine, tables_to_migrate)

        print("Syncing Railway tables without dropping the schema...")
        _sync_destination_tables(railway_engine, local_data, tables_to_migrate)

        print("\nDatabase migration completed successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    migrate_database()
