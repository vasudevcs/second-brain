"""
PEIS query interface.

Usage:
    python brain/query.py stats
    python brain/query.py sessions
    python brain/query.py mistakes
    python brain/query.py decisions
    python brain/query.py lessons
"""

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "brain.db"

# ── Terminal width helpers ────────────────────────────────────────────────────

WIDTH = 72
DIV   = "─" * WIDTH


def header(title: str):
    print(f"\n{DIV}")
    print(f"  {title}")
    print(DIV)


def row(label: str, value, width: int = 28):
    print(f"  {label:<{width}} {value}")


# ── Database connection ───────────────────────────────────────────────────────

def get_cursor():
    if not DB_PATH.exists():
        print(f"[error] Database not found at {DB_PATH}")
        print("        Run: python brain/init_db.py")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn, conn.cursor()


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_stats():
    conn, c = get_cursor()

    header("PEIS — system statistics")

    # Entry counts per table
    tables = ["sessions", "mistakes", "decisions", "lessons"]
    totals = {}
    for t in tables:
        c.execute(f"SELECT COUNT(*) FROM {t}")
        totals[t] = c.fetchone()[0]

    row("Total entries", sum(totals.values()))
    print()
    for t, n in totals.items():
        row(f"  {t}", n)

    # Last activity date (most recent date across all tables)
    print()
    dates = []
    for t in tables:
        c.execute(f"SELECT MAX(date) FROM {t}")
        d = c.fetchone()[0]
        if d:
            dates.append(d)

    if dates:
        row("Last activity", max(dates))
    else:
        row("Last activity", "no entries yet")

    # Total tracked time
    c.execute("SELECT SUM(duration_mins) FROM sessions WHERE duration_mins IS NOT NULL")
    total_mins = c.fetchone()[0] or 0
    hours, mins = divmod(total_mins, 60)
    row("Total session time", f"{hours}h {mins}m ({total_mins} mins)")

    # Mood breakdown
    c.execute("""
        SELECT mood, COUNT(*) as n
        FROM sessions
        WHERE mood IS NOT NULL
        GROUP BY mood
        ORDER BY n DESC
    """)
    moods = c.fetchall()
    if moods:
        print()
        row("Session moods", "")
        for m in moods:
            row(f"  {m['mood']}", m['n'])

    # Most common mistake category
    c.execute("""
        SELECT category, COUNT(*) as n
        FROM mistakes
        WHERE category IS NOT NULL
        GROUP BY category
        ORDER BY n DESC
        LIMIT 5
    """)
    cats = c.fetchall()
    if cats:
        print()
        row("Mistake categories", "")
        for cat in cats:
            row(f"  {cat['category']}", cat['n'])

    # Most used tags (across all types)
    all_tags: dict[str, int] = {}
    for t in tables:
        c.execute(f"SELECT tags FROM {t} WHERE tags IS NOT NULL AND tags != '[]'")
        for r in c.fetchall():
            try:
                for tag in json.loads(r["tags"]):
                    all_tags[tag] = all_tags.get(tag, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass

    if all_tags:
        print()
        row("Top tags", "")
        for tag, count in sorted(all_tags.items(), key=lambda x: -x[1])[:8]:
            row(f"  #{tag}", count)

    print(f"\n{DIV}\n")
    conn.close()


def cmd_sessions():
    conn, c = get_cursor()
    header("Sessions")

    c.execute("""
        SELECT date, project, duration_mins, mood, tags, summary
        FROM sessions
        ORDER BY date DESC
    """)
    rows = c.fetchall()

    if not rows:
        print("  No sessions logged yet.\n")
        conn.close()
        return

    for r in rows:
        tags = _fmt_tags(r["tags"])
        duration = f"{r['duration_mins']} mins" if r["duration_mins"] else "—"
        mood     = r["mood"] or "—"
        project  = r["project"] or "—"
        summary  = (r["summary"] or "").strip()
        # Show first non-empty, non-heading line of summary as preview
        preview = _first_line(summary)

        print(f"\n  {r['date'] or '(no date)'}  ·  {project}")
        print(f"  Duration: {duration}   Mood: {mood}")
        if tags:
            print(f"  Tags: {tags}")
        if preview:
            print(f"  {preview}")

    print(f"\n  {len(rows)} session(s)\n{DIV}\n")
    conn.close()


def cmd_mistakes():
    conn, c = get_cursor()
    header("Mistakes")

    c.execute("""
        SELECT date, project, title, category, severity,
               recurrence, tags, root_cause, lesson
        FROM mistakes
        ORDER BY date DESC
    """)
    rows = c.fetchall()

    if not rows:
        print("  No mistakes logged yet.\n")
        conn.close()
        return

    for r in rows:
        tags      = _fmt_tags(r["tags"])
        severity  = r["severity"] or "—"
        category  = r["category"] or "—"
        recur     = r["recurrence"] or 0
        project   = r["project"] or "—"
        rc        = _first_line(r["root_cause"] or "")
        lesson    = _first_line(r["lesson"] or "")

        print(f"\n  {r['date'] or '(no date)'}  ·  {project}")
        print(f"  {r['title'] or '(untitled)'}")
        print(f"  Category: {category}   Severity: {severity}   Recurrence: {recur}")
        if tags:
            print(f"  Tags: {tags}")
        if rc:
            print(f"  Root cause: {rc}")
        if lesson:
            print(f"  Lesson: {lesson}")

    print(f"\n  {len(rows)} mistake(s)\n{DIV}\n")
    conn.close()


def cmd_decisions():
    conn, c = get_cursor()
    header("Decisions")

    c.execute("""
        SELECT date, project, title, status, reason, outcome, tags
        FROM decisions
        ORDER BY date DESC
    """)
    rows = c.fetchall()

    if not rows:
        print("  No decisions logged yet.\n")
        conn.close()
        return

    for r in rows:
        tags    = _fmt_tags(r["tags"])
        status  = r["status"] or "—"
        project = r["project"] or "—"
        reason  = _first_line(r["reason"] or "")
        outcome = _first_line(r["outcome"] or "")

        print(f"\n  {r['date'] or '(no date)'}  ·  {project}")
        print(f"  {r['title'] or '(untitled)'}")
        print(f"  Status: {status}")
        if tags:
            print(f"  Tags: {tags}")
        if reason:
            print(f"  Reason: {reason}")
        if outcome:
            print(f"  Outcome: {outcome}")

    print(f"\n  {len(rows)} decision(s)\n{DIV}\n")
    conn.close()


def cmd_lessons():
    conn, c = get_cursor()
    header("Lessons")

    c.execute("""
        SELECT date, project, concept, tags, content
        FROM lessons
        ORDER BY date DESC
    """)
    rows = c.fetchall()

    if not rows:
        print("  No lessons logged yet.\n")
        conn.close()
        return

    for r in rows:
        tags    = _fmt_tags(r["tags"])
        project = r["project"] or "—"
        concept = r["concept"] or "—"
        content = _first_line(r["content"] or "")

        print(f"\n  {r['date'] or '(no date)'}  ·  {project}")
        print(f"  Concept: {concept}")
        if tags:
            print(f"  Tags: {tags}")
        if content:
            print(f"  {content}")

    print(f"\n  {len(rows)} lesson(s)\n{DIV}\n")
    conn.close()


# ── Formatting helpers ────────────────────────────────────────────────────────

def _fmt_tags(raw: str | None) -> str:
    if not raw:
        return ""
    try:
        tags = json.loads(raw)
        return "  ".join(f"#{t}" for t in tags) if tags else ""
    except (json.JSONDecodeError, TypeError):
        return ""


def _first_line(text: str) -> str:
    """Return the first non-empty, non-heading line of a block of text."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            # Truncate long lines for display
            return stripped[:100] + ("…" if len(stripped) > 100 else "")
    return ""


# ── Dispatch ──────────────────────────────────────────────────────────────────

COMMANDS = {
    "stats":     cmd_stats,
    "sessions":  cmd_sessions,
    "mistakes":  cmd_mistakes,
    "decisions": cmd_decisions,
    "lessons":   cmd_lessons,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage: python brain/query.py <command>")
        print(f"Commands: {', '.join(COMMANDS)}")
        sys.exit(1)

    COMMANDS[sys.argv[1]]()
