"""
Database — auto-detects SQLite (local dev) vs PostgreSQL (Railway production).
Set DATABASE_URL env var to activate PostgreSQL. Falls back to SQLite if unset.
"""
import os
import re
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

DATABASE_URL = os.environ.get("DATABASE_URL", "")
DB_PATH      = os.environ.get("DB_PATH", "jd_inbox.db")

if DATABASE_URL:
    import psycopg2
    import psycopg2.extras
    USE_PG = True
else:
    import sqlite3
    USE_PG = False


# ── DB wrapper ────────────────────────────────────────────────────────────────

class DB:
    """Thin wrapper normalising SQLite and psycopg2 into one API."""

    def __init__(self):
        if USE_PG:
            url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
            self._conn = psycopg2.connect(url)
            self._cur  = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            self._conn = sqlite3.connect(DB_PATH)
            self._conn.row_factory = sqlite3.Row
            self._cur  = self._conn.cursor()

    # ── SQL helpers ───────────────────────────────────────────────────────────

    def _ph(self, sql: str) -> str:
        """Swap ? → %s for PostgreSQL."""
        return re.sub(r'\?', '%s', sql) if USE_PG else sql

    # ── Query API ─────────────────────────────────────────────────────────────

    def execute(self, sql: str, params: tuple = ()) -> "DB":
        self._cur.execute(self._ph(sql), params)
        return self

    def fetchall(self) -> List[Dict]:
        return [dict(r) for r in (self._cur.fetchall() or [])]

    def fetchone(self) -> Optional[Dict]:
        row = self._cur.fetchone()
        return dict(row) if row else None

    def insert(self, sql: str, params: tuple = ()) -> int:
        """Execute INSERT and return the new row id."""
        if USE_PG:
            self._cur.execute(self._ph(sql) + " RETURNING id", params)
            return self._cur.fetchone()["id"]
        self._cur.execute(self._ph(sql), params)
        return self._cur.lastrowid

    @property
    def rowcount(self) -> int:
        return self._cur.rowcount

    def commit(self):   self._conn.commit()
    def rollback(self): self._conn.rollback()
    def close(self):    self._conn.close()


@contextmanager
def get_db():
    db = DB()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.commit()
        db.close()


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db():
    """Create tables if they don't exist. Runs on startup."""
    if USE_PG:
        pk = "SERIAL PRIMARY KEY"
        ts = "TIMESTAMP DEFAULT NOW()"
    else:
        pk = "INTEGER PRIMARY KEY AUTOINCREMENT"
        ts = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"

    with get_db() as db:
        db.execute(f"""
            CREATE TABLE IF NOT EXISTS jobs (
                id                  {pk},

                -- identity
                filename            TEXT NOT NULL,
                role                TEXT,
                company             TEXT,
                sector              TEXT,
                mode                TEXT,               -- Remote/Hybrid/Onsite
                source              TEXT DEFAULT 'upload',  -- upload | candeo
                source_id           TEXT,               -- job_url or title|company (dedup key)

                -- content
                jd_text             TEXT,
                jd_file_path        TEXT,
                location            TEXT,
                employment_type     TEXT,
                posted_at           TEXT,
                salary_estimate     TEXT,
                job_url             TEXT,
                search_label        TEXT,
                candeo_data         TEXT,               -- JSON blob from Candeo enrichment

                -- rapid output
                status              TEXT DEFAULT 'pending',
                score               INTEGER,
                tier                TEXT,
                archetype           TEXT,
                brief               TEXT,
                why                 TEXT,
                green_flags         TEXT,               -- JSON array
                red_flags           TEXT,               -- JSON array
                rapid_output        TEXT,               -- full JSON from Gemini

                -- tier / cv generation
                tier_output         TEXT,
                cv_text             TEXT,
                cv_file_path        TEXT,
                cover_letter_text   TEXT,

                -- chat
                chat_history        TEXT DEFAULT '[]',  -- JSON array of messages

                created_at          {ts},
                updated_at          {ts}
            )
        """)

        # Stories table — career evidence base
        db.execute(f"""
            CREATE TABLE IF NOT EXISTS stories (
                story_id            TEXT PRIMARY KEY,
                source_file         TEXT,
                company             TEXT,
                initiative          TEXT,
                sub_initiative      TEXT,
                component           TEXT,
                component_summary   TEXT,
                pointer_summary     TEXT,
                work_behind         TEXT,
                outcomes            TEXT,
                year                TEXT,
                story_type          TEXT,
                parent_story_id     TEXT,
                themes              TEXT,
                skills_demonstrated TEXT,
                context_type        TEXT,
                stakeholder_level   TEXT,
                outcome_type        TEXT,
                interview_answer_type TEXT,
                star_story_ready    TEXT,
                role_relevance      TEXT,
                created_at          {ts}
            )
        """)

        # Add any missing columns to existing tables (safe to re-run)
        _migrate(db)

    print(f"✓ Database initialised ({'PostgreSQL' if USE_PG else 'SQLite'})")


def _migrate(db: DB):
    """Add columns that may not exist in older schema versions."""
    new_cols = [
        ("source_id",       "TEXT"),
        ("location",        "TEXT"),
        ("employment_type", "TEXT"),
        ("posted_at",       "TEXT"),
        ("salary_estimate", "TEXT"),
        ("job_url",         "TEXT"),
        ("search_label",    "TEXT"),
        ("candeo_data",     "TEXT"),
    ]
    for col, col_type in new_cols:
        try:
            db.execute(f"ALTER TABLE jobs ADD COLUMN {col} {col_type}")
        except Exception:
            pass  # column already exists — fine


# ── CRUD helpers ──────────────────────────────────────────────────────────────

def get_job(job_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as db:
        return db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()


def update_job(job_id: int, updates: Dict[str, Any]) -> bool:
    if not updates:
        return False
    updates["updated_at"] = datetime.utcnow().isoformat()
    fields = ", ".join(f"{k} = ?" for k in updates)
    values = tuple(updates.values()) + (job_id,)
    with get_db() as db:
        db.execute(f"UPDATE jobs SET {fields} WHERE id = ?", values)
        return db.rowcount > 0


def create_job(data: Dict[str, Any]) -> int:
    fields       = ", ".join(data.keys())
    placeholders = ", ".join("?" * len(data))
    with get_db() as db:
        return db.insert(
            f"INSERT INTO jobs ({fields}) VALUES ({placeholders})",
            tuple(data.values()),
        )


def add_chat_message(job_id: int, role: str, content: str):
    job = get_job(job_id)
    if not job:
        return False
    history = json.loads(job.get("chat_history") or "[]")
    history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
    })
    return update_job(job_id, {"chat_history": json.dumps(history)})
