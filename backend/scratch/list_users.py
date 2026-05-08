import sqlite3
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
paths = [
    repo_root / "db" / "runtime" / "dentai_app.db",
    repo_root / "backend" / "db" / "runtime" / "dentai_app.db",
]

for path in paths:
    if path.exists():
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
