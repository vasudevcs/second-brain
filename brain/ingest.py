"""
PEIS ingestion pipeline.

Reads markdown notes from vault/, parses YAML frontmatter,
and upserts records into brain.db.

Idempotent: running this script any number of times produces
the same database state. Duplicate rows are never created.
Source file path is used as the unique key per record.
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import frontmatter

ROOT       = Path(__file__).resolve().parent.parent
DB_PATH    = ROOT / "data" / "brain.db"
VAULT_PATH = ROOT / "vault"


# ── Date normalisation ────────────────────────────────────────────────────────

_DATE_FORMATS = [
    "%Y-%m-%d",      # 2026-06-18  ← canonical, try first
    "%d-%m-%Y",      # 18-06-2026
    "%d/%m/%Y",      # 18/06/2026
    "%m/%d/%Y",      # 06/18/2026
    "%B %d, %Y",     # June 18, 2026
    "%b %d, %Y",     # Jun 18, 2026
    "%d %B %Y",      # 18 June 2026
    "%Y%m%d",        # 20260618
]


def normalize_date(raw) -> str | None:
    """
    Return an ISO 8601 date string (YYYY-MM-DD) or None.

    Accepts a datetime/date object (python-frontmatter may return one)
    or any string format listed in _DATE_FORMATS.
    Returns None when absent or unparseable so the DB stores NULL
    rather than a corrupt string.
    """
    if raw is None:
        return None
    if hasattr(raw, "strftime"):
        return raw.strftime("%Y-%m-%d")
    text = str(raw).strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    print(f"  [warn] unrecognised date format: {text!r} — stored as NULL")
    return None


# ── List-field serialisation ──────────────────────────────────────────────────

def serialize_list(raw) -> str:
    """
    Serialise any frontmatter value that should be stored as a JSON array.

    Used for: tags, warning_signs, prevention_checklist.

    Handles:
      field: [a, b, c]            → '["a", "b", "c"]'
      field:\n  - a\n  - b        → '["a", "b"]'
      field: "single value"       → '["single value"]'
      field: null / missing       → '[]'
    """
    if raw is None:
        return "[]"
    if isinstance(raw, list):
        return json.dumps([str(item).strip() for item in raw if str(item).strip()])
    if isinstance(raw, str):
        stripped = raw.strip()
        return json.dumps([stripped]) if stripped else "[]"
    return "[]"


# ── Database connection ───────────────────────────────────────────────────────

def get_connection():
    if not DB_PATH.exists():
        print(f"[error] Database not found at {DB_PATH}")
        print("        Run:  python brain/init_db.py")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Per-type ingest functions ─────────────────────────────────────────────────

def ingest_sessions(cursor) -> int:
    folder = VAULT_PATH / "sessions"
    if not folder.exists():
        return 0

    count = 0
    for file in sorted(folder.glob("*.md")):
        post   = frontmatter.load(file)
        source = str(file.relative_to(ROOT))

        cursor.execute("""
            INSERT OR IGNORE INTO sessions
                (date, project, summary, blockers, next_steps,
                 duration_mins, mood, tags, source_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            normalize_date(post.get("date")),
            post.get("project"),
            post.content.strip() or None,
            post.get("blockers"),
            post.get("next_steps"),
            post.get("duration_mins"),
            post.get("mood"),
            serialize_list(post.get("tags")),
            source,
        ))

        if cursor.rowcount:
            print(f"  [new]  session   → {file.name}")
            count += 1
        else:
            print(f"  [skip] session   → {file.name}")

    return count


def ingest_mistakes(cursor) -> int:
    folder = VAULT_PATH / "mistakes"
    if not folder.exists():
        return 0

    count = 0
    for file in sorted(folder.glob("*.md")):
        post   = frontmatter.load(file)
        source = str(file.relative_to(ROOT))

        cursor.execute("""
            INSERT OR IGNORE INTO mistakes
                (date, project, title, category, severity,
                 root_cause, fix, lesson, time_lost_mins, recurrence,
                 tags, source_file,
                 engineering_pattern, beginner_explanation,
                 real_world_analogy, warning_signs, prevention_checklist)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            normalize_date(post.get("date")),
            post.get("project"),
            post.get("title") or file.stem,
            post.get("category"),
            post.get("severity"),
            post.get("root_cause"),
            post.get("fix"),
            post.get("lesson"),
            post.get("time_lost_mins"),
            post.get("recurrence", 0),
            serialize_list(post.get("tags")),
            source,
            # Beginner Coach Mode fields
            post.get("engineering_pattern"),
            post.get("beginner_explanation"),
            post.get("real_world_analogy"),
            serialize_list(post.get("warning_signs")),
            serialize_list(post.get("prevention_checklist")),
        ))

        if cursor.rowcount:
            print(f"  [new]  mistake   → {file.name}")
            count += 1
        else:
            print(f"  [skip] mistake   → {file.name}")

    return count


def ingest_decisions(cursor) -> int:
    folder = VAULT_PATH / "decisions"
    if not folder.exists():
        return 0

    count = 0
    for file in sorted(folder.glob("*.md")):
        post   = frontmatter.load(file)
        source = str(file.relative_to(ROOT))

        cursor.execute("""
            INSERT OR IGNORE INTO decisions
                (date, project, title, reason, outcome,
                 status, tags, source_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            normalize_date(post.get("date")),
            post.get("project"),
            post.get("title") or file.stem,
            post.get("reason"),
            post.get("outcome"),
            post.get("status"),
            serialize_list(post.get("tags")),
            source,
        ))

        if cursor.rowcount:
            print(f"  [new]  decision  → {file.name}")
            count += 1
        else:
            print(f"  [skip] decision  → {file.name}")

    return count


def ingest_lessons(cursor) -> int:
    folder = VAULT_PATH / "lessons"
    if not folder.exists():
        return 0

    count = 0
    for file in sorted(folder.glob("*.md")):
        post   = frontmatter.load(file)
        source = str(file.relative_to(ROOT))

        cursor.execute("""
            INSERT OR IGNORE INTO lessons
                (date, project, concept, content, tags, source_file)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            normalize_date(post.get("date")),
            post.get("project"),
            post.get("concept"),
            post.content.strip() or None,
            serialize_list(post.get("tags")),
            source,
        ))

        if cursor.rowcount:
            print(f"  [new]  lesson    → {file.name}")
            count += 1
        else:
            print(f"  [skip] lesson    → {file.name}")

    return count


# ── Entry point ───────────────────────────────────────────────────────────────

def run():
    conn   = get_connection()
    cursor = conn.cursor()

    print("PEIS ingestion pipeline\n")

    totals = {
        "sessions":  ingest_sessions(cursor),
        "mistakes":  ingest_mistakes(cursor),
        "decisions": ingest_decisions(cursor),
        "lessons":   ingest_lessons(cursor),
    }

    conn.commit()
    conn.close()

    total_new = sum(totals.values())
    print(f"\n{'─' * 40}")
    print(f"  {total_new} new record(s) ingested")
    for kind, n in totals.items():
        if n:
            print(f"  {kind:<12} +{n}")
    print(f"{'─' * 40}\n")


if __name__ == "__main__":
    run()
