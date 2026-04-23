"""
Database models and initialization
SQLite for MVP, PostgreSQL migration path preserved
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

DB_PATH = "jd_inbox.db"

def init_db():
    """Initialize database with schema"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            role TEXT,
            company TEXT,
            sector TEXT,
            mode TEXT,
            source TEXT DEFAULT 'upload',
            jd_text TEXT,
            jd_file_path TEXT,
            
            status TEXT DEFAULT 'pending',
            score INTEGER,
            tier TEXT,
            archetype TEXT,
            brief TEXT,
            why TEXT,
            green_flags TEXT,
            red_flags TEXT,
            
            rapid_output TEXT,
            tier_output TEXT,
            cv_text TEXT,
            cv_file_path TEXT,
            cover_letter_text TEXT,
            
            chat_history TEXT DEFAULT '[]',
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"✓ Database initialized at {DB_PATH}")

@contextmanager
def get_db():
    """Get database connection (context manager)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_job(job_id: int) -> Optional[Dict[str, Any]]:
    """Get single job by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        row = cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None

def update_job(job_id: int, updates: Dict[str, Any]) -> bool:
    """Update job fields"""
    if not updates:
        return False
    
    # Always update updated_at
    updates['updated_at'] = datetime.utcnow().isoformat()
    
    # Build SQL
    fields = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [job_id]
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE jobs SET {fields} WHERE id = ?", values)
        conn.commit()
        return cursor.rowcount > 0

def create_job(data: Dict[str, Any]) -> int:
    """Create new job, return ID"""
    fields = ", ".join(data.keys())
    placeholders = ", ".join("?" * len(data))
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"INSERT INTO jobs ({fields}) VALUES ({placeholders})",
            list(data.values())
        )
        conn.commit()
        return cursor.lastrowid

def add_chat_message(job_id: int, role: str, content: str):
    """Add message to chat history"""
    job = get_job(job_id)
    if not job:
        return False
    
    history = json.loads(job.get('chat_history', '[]'))
    history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return update_job(job_id, {"chat_history": json.dumps(history)})
