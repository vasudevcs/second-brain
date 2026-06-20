"""
PEIS query interface.

Usage:
    python brain/query.py stats
    python brain/query.py sessions
    python brain/query.py mistakes
    python brain/query.py decisions
    python brain/query.py lessons
    python brain/query.py teach mistakes
"""

import json
import sqlite3
import sys
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "brain.db"

WIDTH = 72
DIV   = "─" * WIDTH
THIN  = "·" * WIDTH


# ── Output helpers ────────────────────────────────────────────────────────────

def header(title: str):
    print(f"\n{DIV}")
    print(f"  {title}")
    print(DIV)


def field(label: str, value, indent: int = 2, label_width: int = 26):
    pad = " " * indent
    print(f"{pad}{label:<{label_width}} {value}")


# ── Database ──────────────────────────────────────────────────────────────────

def get_conn():
    if not DB_PATH.exists():
        print(f"[error] Database not found at {DB_PATH}")
        print("        Run: python brain/init_db.py")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Shared helpers ────────────────────────────────────────────────────────────

def _fmt_tags(raw: str | None) -> str:
    if not raw:
        return ""
    try:
        tags = json.loads(raw)
        return "  ".join(f"#{t}" for t in tags) if tags else ""
    except (json.JSONDecodeError, TypeError):
        return ""


def _load_list(raw: str | None) -> list[str]:
    """Deserialise a JSON array column into a Python list."""
    if not raw:
        return []
    try:
        result = json.loads(raw)
        return [str(item) for item in result] if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _first_line(text: str) -> str:
    """First non-empty, non-heading line, truncated to 100 chars."""
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped[:100] + ("…" if len(stripped) > 100 else "")
    return ""


def _wrap(text: str, indent: int = 4, width: int = 68) -> str:
    """
    Wrap a paragraph of text to fit the terminal width.
    Returns a single string with newlines and leading indent on each line.
    """
    if not text:
        return ""
    pad   = " " * indent
    words = text.split()
    lines = []
    line  = pad
    for word in words:
        if len(line) + len(word) + 1 > width:
            lines.append(line.rstrip())
            line = pad + word + " "
        else:
            line += word + " "
    if line.strip():
        lines.append(line.rstrip())
    return "\n".join(lines)


# ── stats ─────────────────────────────────────────────────────────────────────

def cmd_stats():
    conn = get_conn()
    c    = conn.cursor()

    header("PEIS — system statistics")

    tables = ["sessions", "mistakes", "decisions", "lessons"]
    totals = {}
    for t in tables:
        c.execute(f"SELECT COUNT(*) FROM {t}")
        totals[t] = c.fetchone()[0]

    field("Total entries", sum(totals.values()))
    print()
    for t, n in totals.items():
        field(f"  {t}", n)

    # Last activity
    print()
    dates = []
    for t in tables:
        c.execute(f"SELECT MAX(date) FROM {t}")
        d = c.fetchone()[0]
        if d:
            dates.append(d)
    field("Last activity", max(dates) if dates else "no entries yet")

    # Session time
    c.execute("SELECT SUM(duration_mins) FROM sessions WHERE duration_mins IS NOT NULL")
    mins_total = c.fetchone()[0] or 0
    h, m = divmod(mins_total, 60)
    field("Total session time", f"{h}h {m}m  ({mins_total} mins)")

    # Mood
    c.execute("""
        SELECT mood, COUNT(*) n FROM sessions
        WHERE mood IS NOT NULL
        GROUP BY mood ORDER BY n DESC
    """)
    moods = c.fetchall()
    if moods:
        print()
        field("Session moods", "")
        for row in moods:
            field(f"  {row['mood']}", row['n'])

    # Mistake categories
    c.execute("""
        SELECT category, COUNT(*) n FROM mistakes
        WHERE category IS NOT NULL
        GROUP BY category ORDER BY n DESC LIMIT 5
    """)
    cats = c.fetchall()
    if cats:
        print()
        field("Mistake categories", "")
        for row in cats:
            field(f"  {row['category']}", row['n'])

    # Coach coverage — how many mistakes have beginner explanations
    c.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN beginner_explanation IS NOT NULL AND beginner_explanation != '' THEN 1 ELSE 0 END) as coached
        FROM mistakes
    """)
    row = c.fetchone()
    if row and row['total'] > 0:
        print()
        field("Beginner Coach coverage",
              f"{row['coached']}/{row['total']} mistakes have explanations")

    # Top tags
    all_tags: dict[str, int] = {}
    for t in tables:
        c.execute(f"SELECT tags FROM {t} WHERE tags IS NOT NULL AND tags != '[]'")
        for row in c.fetchall():
            for tag in _load_list(row["tags"]):
                all_tags[tag] = all_tags.get(tag, 0) + 1
    if all_tags:
        print()
        field("Top tags", "")
        for tag, count in sorted(all_tags.items(), key=lambda x: -x[1])[:8]:
            field(f"  #{tag}", count)

    print(f"\n{DIV}\n")
    conn.close()


# ── sessions ──────────────────────────────────────────────────────────────────

def cmd_sessions():
    conn = get_conn()
    c    = conn.cursor()
    header("Sessions")

    c.execute("""
        SELECT date, project, duration_mins, mood, tags, summary
        FROM sessions ORDER BY date DESC
    """)
    rows = c.fetchall()

    if not rows:
        print("  No sessions logged yet.\n")
        conn.close()
        return

    for r in rows:
        dur  = f"{r['duration_mins']} mins" if r["duration_mins"] else "—"
        tags = _fmt_tags(r["tags"])
        prev = _first_line(r["summary"] or "")

        print(f"\n  {r['date'] or '(no date)'}  ·  {r['project'] or '—'}")
        print(f"  Duration: {dur}   Mood: {r['mood'] or '—'}")
        if tags:
            print(f"  Tags: {tags}")
        if prev:
            print(f"  {prev}")

    print(f"\n  {len(rows)} session(s)\n{DIV}\n")
    conn.close()


# ── mistakes ──────────────────────────────────────────────────────────────────

def cmd_mistakes():
    conn = get_conn()
    c    = conn.cursor()
    header("Mistakes")

    c.execute("""
        SELECT date, project, title, category, severity,
               recurrence, tags, root_cause, lesson,
               engineering_pattern, beginner_explanation
        FROM mistakes ORDER BY date DESC
    """)
    rows = c.fetchall()

    if not rows:
        print("  No mistakes logged yet.\n")
        conn.close()
        return

    for r in rows:
        tags    = _fmt_tags(r["tags"])
        pattern = r["engineering_pattern"] or ""
        expl    = _first_line(r["beginner_explanation"] or "")

        print(f"\n  {r['date'] or '(no date)'}  ·  {r['project'] or '—'}")
        print(f"  {r['title'] or '(untitled)'}")
        print(f"  Category: {r['category'] or '—'}   "
              f"Severity: {r['severity'] or '—'}   "
              f"Recurrence: {r['recurrence'] or 0}")
        if tags:
            print(f"  Tags: {tags}")
        if _first_line(r["root_cause"] or ""):
            print(f"  Root cause:  {_first_line(r['root_cause'])}")
        if _first_line(r["lesson"] or ""):
            print(f"  Lesson:      {_first_line(r['lesson'])}")
        if pattern:
            print(f"  Pattern:     {pattern}")
        if expl:
            print(f"  Explanation: {expl}")

    print(f"\n  {len(rows)} mistake(s)\n{DIV}\n")
    conn.close()


# ── decisions ─────────────────────────────────────────────────────────────────

def cmd_decisions():
    conn = get_conn()
    c    = conn.cursor()
    header("Decisions")

    c.execute("""
        SELECT date, project, title, status, reason, outcome, tags
        FROM decisions ORDER BY date DESC
    """)
    rows = c.fetchall()

    if not rows:
        print("  No decisions logged yet.\n")
        conn.close()
        return

    for r in rows:
        tags = _fmt_tags(r["tags"])
        print(f"\n  {r['date'] or '(no date)'}  ·  {r['project'] or '—'}")
        print(f"  {r['title'] or '(untitled)'}")
        print(f"  Status: {r['status'] or '—'}")
        if tags:
            print(f"  Tags: {tags}")
        if _first_line(r["reason"] or ""):
            print(f"  Reason:  {_first_line(r['reason'])}")
        if _first_line(r["outcome"] or ""):
            print(f"  Outcome: {_first_line(r['outcome'])}")

    print(f"\n  {len(rows)} decision(s)\n{DIV}\n")
    conn.close()


# ── lessons ───────────────────────────────────────────────────────────────────

def cmd_lessons():
    conn = get_conn()
    c    = conn.cursor()
    header("Lessons")

    c.execute("""
        SELECT date, project, concept, tags, content
        FROM lessons ORDER BY date DESC
    """)
    rows = c.fetchall()

    if not rows:
        print("  No lessons logged yet.\n")
        conn.close()
        return

    for r in rows:
        tags = _fmt_tags(r["tags"])
        print(f"\n  {r['date'] or '(no date)'}  ·  {r['project'] or '—'}")
        print(f"  Concept: {r['concept'] or '—'}")
        if tags:
            print(f"  Tags: {tags}")
        if _first_line(r["content"] or ""):
            print(f"  {_first_line(r['content'])}")

    print(f"\n  {len(rows)} lesson(s)\n{DIV}\n")
    conn.close()


# ── teach mistakes ────────────────────────────────────────────────────────────

def cmd_teach_mistakes():
    """
    Beginner Coach Mode.

    Displays every mistake that has at least a beginner_explanation,
    formatted as a teaching card rather than a technical log entry.
    The goal is to make past mistakes usable as learning material.
    """
    conn = get_conn()
    c    = conn.cursor()

    c.execute("""
        SELECT date, project, title,
               engineering_pattern,
               beginner_explanation,
               real_world_analogy,
               warning_signs,
               prevention_checklist,
               recurrence, category
        FROM mistakes
        WHERE beginner_explanation IS NOT NULL
          AND beginner_explanation != ''
        ORDER BY date DESC
    """)
    rows = c.fetchall()

    print(f"\n{DIV}")
    print("  PEIS Beginner Coach — Lessons From Past Mistakes")
    print(DIV)

    if not rows:
        print("\n  No coached mistakes yet.")
        print("  When you log a mistake, fill in the beginner_explanation")
        print("  field in the frontmatter to make it appear here.\n")
        conn.close()
        return

    for i, r in enumerate(rows):
        # Card separator — not printed before the first card
        if i > 0:
            print(f"\n  {THIN}")

        # ── Header ────────────────────────────────────────────────────────
        recur = r["recurrence"] or 0
        recur_note = f"  ⚠  You have made this type of mistake {recur} time(s) before." if recur else ""

        print(f"\n  📚  {r['title'] or '(untitled)'}")
        print(f"      {r['date'] or '(no date)'}  ·  {r['project'] or '—'}  ·  {r['category'] or 'uncategorised'}")
        if recur_note:
            print(f"\n{recur_note}")

        # ── Engineering pattern ───────────────────────────────────────────
        pattern = (r["engineering_pattern"] or "").strip()
        if pattern:
            print(f"\n  Pattern")
            print(f"      {pattern}")

        # ── Plain-language explanation ────────────────────────────────────
        explanation = (r["beginner_explanation"] or "").strip()
        if explanation:
            print(f"\n  What happened, in plain language")
            print(_wrap(explanation, indent=6))

        # ── Real-world analogy ────────────────────────────────────────────
        analogy = (r["real_world_analogy"] or "").strip()
        if analogy:
            print(f"\n  Think of it this way")
            print(_wrap(analogy, indent=6))

        # ── Warning signs ─────────────────────────────────────────────────
        signs = _load_list(r["warning_signs"])
        if signs:
            print(f"\n  Warning signs to catch this earlier")
            for sign in signs:
                print(f"      →  {sign}")

        # ── Prevention checklist ──────────────────────────────────────────
        checklist = _load_list(r["prevention_checklist"])
        if checklist:
            print(f"\n  Prevention checklist")
            for item in checklist:
                print(f"      ✓  {item}")

    coached   = len(rows)
    c.execute("SELECT COUNT(*) FROM mistakes")
    total_mis = c.fetchone()[0]
    uncouched = total_mis - coached

    print(f"\n{DIV}")
    print(f"  {coached} coached mistake(s) shown.")
    if uncouched:
        print(f"  {uncouched} mistake(s) have no beginner explanation yet.")
        print(f"  Add beginner_explanation: to their frontmatter to include them here.")
    print(f"{DIV}\n")
    conn.close()


# ── Dispatch ──────────────────────────────────────────────────────────────────

# Top-level commands
COMMANDS: dict[str, callable] = {
    "stats":     cmd_stats,
    "sessions":  cmd_sessions,
    "mistakes":  cmd_mistakes,
    "decisions": cmd_decisions,
    "lessons":   cmd_lessons,
}

# Sub-commands: `python brain/query.py <group> <sub>`
SUBCOMMANDS: dict[tuple[str, str], callable] = {
    ("teach", "mistakes"): cmd_teach_mistakes,
}

def _usage():
    print("Usage: python brain/query.py <command>")
    print(f"  Commands:     {', '.join(COMMANDS)}")
    print(f"  Subcommands:  teach mistakes")


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        _usage()
        sys.exit(1)

    # Two-word subcommand (e.g. "teach mistakes")
    if len(args) >= 2:
        key = (args[0], args[1])
        if key in SUBCOMMANDS:
            SUBCOMMANDS[key]()
            sys.exit(0)
        # First word is a known group but second word is unknown
        groups = {k[0] for k in SUBCOMMANDS}
        if args[0] in groups:
            print(f"[error] Unknown subcommand: '{args[0]} {args[1]}'")
            _usage()
            sys.exit(1)

    # Single-word command
    cmd = args[0]
    if cmd not in COMMANDS:
        print(f"[error] Unknown command: '{cmd}'")
        _usage()
        sys.exit(1)

    COMMANDS[cmd]()
