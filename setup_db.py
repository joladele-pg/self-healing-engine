import sqlite3

conn = sqlite3.connect("healing.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS incident_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_name TEXT,
        error_code TEXT,
        action_taken TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
""")

conn.commit()
conn.close()
print("Database healing.db and table incident_logs created successfully!")
