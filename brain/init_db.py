import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "brain.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init():
    conn = get_connection()
    cursor = conn.cursor()

    # ── Projects ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT NOT NULL UNIQUE,
        status     TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ── Sessions ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        date          TEXT,
        project       TEXT,
        summary       TEXT,
        blockers      TEXT,
        next_steps    TEXT,
        duration_mins INTEGER,
        mood          TEXT,
        tags          TEXT DEFAULT '[]',
        source_file   TEXT UNIQUE
    )
    """)

    # ── Mistakes ──────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mistakes (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        date          TEXT,
        project       TEXT,
        title         TEXT,
        category      TEXT,
        severity      TEXT,
        root_cause    TEXT,
        fix           TEXT,
        lesson        TEXT,
        time_lost_mins INTEGER,
        recurrence    INTEGER DEFAULT 0,
        tags          TEXT DEFAULT '[]',
        source_file   TEXT UNIQUE
    )
    """)

    # ── Decisions ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decisions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        date        TEXT,
        project     TEXT,
        title       TEXT,
        reason      TEXT,
        outcome     TEXT,
        status      TEXT,
        tags        TEXT DEFAULT '[]',
        source_file TEXT UNIQUE
    )
    """)

    # ── Lessons ───────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lessons (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        date        TEXT,
        project     TEXT,
        concept     TEXT,
        content     TEXT,
        tags        TEXT DEFAULT '[]',
        source_file TEXT UNIQUE
    )
    """)

    conn.commit()
    conn.close()
    print(f"Database ready: {DB_PATH}")


if __name__ == "__main__":
    init()
