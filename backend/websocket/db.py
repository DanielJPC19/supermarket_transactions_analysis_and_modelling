from __future__ import annotations
import sqlite3
import threading
from datetime import datetime, timezone

from backend.config import JOBS_DB_PATH

_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    JOBS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(JOBS_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock, _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                job_type     TEXT NOT NULL,
                status       TEXT NOT NULL,
                started_at   TEXT NOT NULL,
                finished_at  TEXT,
                message      TEXT
            )
        """)
        conn.commit()


def insert_job(job_type: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _lock, _conn() as conn:
        cur = conn.execute(
            "INSERT INTO jobs (job_type, status, started_at) VALUES (?, ?, ?)",
            (job_type, "running", now),
        )
        conn.commit()
        return cur.lastrowid


def update_job(job_id: int, status: str, message: str = "") -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _lock, _conn() as conn:
        conn.execute(
            "UPDATE jobs SET status=?, finished_at=?, message=? WHERE id=?",
            (status, now, message, job_id),
        )
        conn.commit()


def get_recent_jobs(n: int = 20) -> list[dict]:
    with _lock, _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY id DESC LIMIT ?", (n,)
        ).fetchall()
    return [dict(r) for r in rows]
