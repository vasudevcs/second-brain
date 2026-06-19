import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

db_path = DATA_DIR / "brain.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Projects
cursor.execute("""
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Sessions
cursor.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    project TEXT,
    summary TEXT,
    blockers TEXT,
    next_steps TEXT,
    duration_mins INTEGER,
    mood TEXT
)
""")

# Mistakes
cursor.execute("""
CREATE TABLE IF NOT EXISTS mistakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    project TEXT,
    title TEXT,
    category TEXT,
    severity TEXT,
    root_cause TEXT,
    fix TEXT,
    lesson TEXT,
    time_lost_mins INTEGER,
    recurrence INTEGER DEFAULT 0
)
""")

# Decisions
cursor.execute("""
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    project TEXT,
    title TEXT,
    reason TEXT,
    outcome TEXT,
    status TEXT
)
""")

# Lessons
cursor.execute("""
CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    project TEXT,
    concept TEXT,
    content TEXT
)
""")

conn.commit()
conn.close()

print("Database created successfully.")
print(f"Database location: {db_path}")