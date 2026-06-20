"""
PEIS database initialisation and migration.

Running this file is always safe — it creates tables if they do not
exist and applies any schema migrations needed to bring an older
database up to the current version without destroying data.
"""

import sqlite3
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "brain.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _column_names(cursor, table: str) -> set[str]:
    """Return the set of column names that currently exist in a table."""
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def _add_column_if_missing(cursor, table: str, column: str, definition: str):
    """
    Add a column to a table only if it does not already exist.
    Prevents errors when init_db is run against an existing database.
    """
    if column not in _column_names(cursor, table):
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        print(f"  [migrate] {table}.{column} added")


def init():
    conn   = get_connection()
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
    # Core columns
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mistakes (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        date                 TEXT,
        project              TEXT,
        title                TEXT,
        category             TEXT,
        severity             TEXT,
        root_cause           TEXT,
        fix                  TEXT,
        lesson               TEXT,
        time_lost_mins       INTEGER,
        recurrence           INTEGER DEFAULT 0,
        tags                 TEXT DEFAULT '[]',
        source_file          TEXT UNIQUE,
        -- Beginner Coach Mode fields
        engineering_pattern  TEXT,
        beginner_explanation TEXT,
        real_world_analogy   TEXT,
        warning_signs        TEXT,
        prevention_checklist TEXT
    )
    """)

    # Migration: add coach columns to any pre-existing mistakes table
    # that was created before this version.
    coach_columns = {
        "engineering_pattern":  "TEXT",
        "beginner_explanation": "TEXT",
        "real_world_analogy":   "TEXT",
        "warning_signs":        "TEXT DEFAULT '[]'",
        "prevention_checklist": "TEXT DEFAULT '[]'",
    }
    for col, defn in coach_columns.items():
        _add_column_if_missing(cursor, "mistakes", col, defn)

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
