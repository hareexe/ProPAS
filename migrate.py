import sqlite3
import pymysql
import os
from app import app, db

# --- CONFIGURATION ---
# Path to your local SQLite file
LOCAL_DB_PATH = 'propas.db' 

# Details from your Railway "Public Network" screen
RAILWAY_CONFIG = {
    'host': 'maglev.proxy.rlwy.net',
    'user': 'root',
    'password': 'AgBgFrnfYiVzaOJJPTXoNeHXBdmGWdLA',
    'port': 19932,
    'database': 'railway'
}

def migrate_all():
    # STEP 1: CREATE TABLES
    print("🛠️ Step 1: Creating tables on Railway MySQL...")
    with app.app_context():
        # This uses your models.py to build the tables in the DB 
        # pointed to by your environment variables or config.
        db.create_all()
    print("✅ Tables created (or already existed).")

    # STEP 2: MIGRATE DATA
    if not os.path.exists(LOCAL_DB_PATH):
        print(f"❌ Error: Local file '{LOCAL_DB_PATH}' not found.")
        return

    try:
        print("🔗 Connecting to databases for data transfer...")
        local_conn = sqlite3.connect(LOCAL_DB_PATH)
        railway_conn = pymysql.connect(**RAILWAY_CONFIG)
        
        local_cur = local_conn.cursor()
        railway_cur = railway_conn.cursor()

        local_cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in local_cur.fetchall() if t[0] != 'sqlite_sequence']

        railway_cur.execute("SET FOREIGN_KEY_CHECKS = 0;")

        for table in tables:
            print(f"Moving data for table: {table}...")
            local_cur.execute(f"SELECT * FROM `{table}`")
            rows = local_cur.fetchall()

            if not rows:
                print(f"  - {table} is empty. Skipping.")
                continue

            columns = [desc[0] for desc in local_cur.description]
            placeholders = ", ".join(["%s"] * len(columns))
            sql = f"INSERT INTO `{table}` ({', '.join(['`'+c+'`' for c in columns])}) VALUES ({placeholders})"

            railway_cur.execute(f"TRUNCATE TABLE `{table}`")
            railway_cur.executemany(sql, rows)
            print(f"  - Successfully moved {len(rows)} records.")

        railway_cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
        railway_conn.commit()
        print("\n🎉 All-in-one migration complete! Tables and data are live.")

    except Exception as e:
        print(f"❌ Data Migration Error: {e}")
    finally:
        local_conn.close()
        railway_conn.close()

if __name__ == "__main__":
    migrate_all()