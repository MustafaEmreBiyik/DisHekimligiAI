import sqlite3
import os

paths = ["dentai_app.db", "db/runtime/dentai_app.db"]

for path in paths:
    if os.path.exists(path):
        print(f"--- Database: {path} ---")
        try:
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, display_name, role FROM users LIMIT 10")
            rows = cursor.fetchall()
            for row in rows:
                print(row)
            conn.close()
        except Exception as e:
            print(f"Error reading {path}: {e}")
    else:
        print(f"Path not found: {path}")
