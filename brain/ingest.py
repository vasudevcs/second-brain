import sqlite3
from pathlib import Path
import frontmatter

ROOT = Path(__file__).resolve().parent.parent

DB_PATH = ROOT / "data" / "brain.db"
VAULT = ROOT / "vault"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()


def ingest_decisions():
    folder = VAULT / "decisions"

    for file in folder.glob("*.md"):
        post = frontmatter.load(file)

        cursor.execute("""
        INSERT INTO decisions (
            date,
            project,
            title,
            status
        )
        VALUES (?, ?, ?, ?)
        """, (
            post.get("date"),
            post.get("project"),
            file.stem,
            post.get("status")
        ))

        print(f"Decision imported: {file.name}")


def ingest_lessons():
    folder = VAULT / "lessons"

    for file in folder.glob("*.md"):
        post = frontmatter.load(file)

        cursor.execute("""
        INSERT INTO lessons (
            date,
            project,
            concept,
            content
        )
        VALUES (?, ?, ?, ?)
        """, (
            post.get("date"),
            post.get("project"),
            post.get("concept"),
            post.content
        ))

        print(f"Lesson imported: {file.name}")


def ingest_sessions():
    folder = VAULT / "sessions"

    for file in folder.glob("*.md"):
        post = frontmatter.load(file)

        cursor.execute("""
        INSERT INTO sessions (
            date,
            project,
            summary,
            duration_mins,
            mood
        )
        VALUES (?, ?, ?, ?, ?)
        """, (
            post.get("date"),
            post.get("project"),
            post.content,
            post.get("duration_mins"),
            post.get("mood")
        ))

        print(f"Session imported: {file.name}")


ingest_decisions()
ingest_lessons()
ingest_sessions()

conn.commit()
conn.close()

print("\nIngestion complete.")