from __future__ import annotations
import threading
from datetime import datetime, timezone

from backend.config import (
    USE_POSTGRES, POSTGRES_HOST, POSTGRES_PORT,
    POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB,
    JOBS_DB_PATH,
)

_lock = threading.Lock()


def _conn():
    if USE_POSTGRES:
        import psycopg2
        return psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            dbname=POSTGRES_DB,
        )
    import sqlite3
    JOBS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(JOBS_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock, _conn() as conn:
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id          SERIAL PRIMARY KEY,
                    job_type    VARCHAR(50) NOT NULL,
                    status      VARCHAR(50) NOT NULL,
                    started_at  VARCHAR(50) NOT NULL,
                    finished_at VARCHAR(50),
                    message     TEXT
                )
            """)
        else:
            cur.execute("""
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
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute(
                "INSERT INTO jobs (job_type, status, started_at) VALUES (%s, %s, %s) RETURNING id",
                (job_type, "running", now),
            )
            row_id = cur.fetchone()[0]
        else:
            cur.execute(
                "INSERT INTO jobs (job_type, status, started_at) VALUES (?, ?, ?)",
                (job_type, "running", now),
            )
            row_id = cur.lastrowid
        conn.commit()
        return row_id


def update_job(job_id: int, status: str, message: str = "") -> None:
    now = datetime.now(timezone.utc).isoformat()
    ph = "%s" if USE_POSTGRES else "?"
    with _lock, _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE jobs SET status={ph}, finished_at={ph}, message={ph} WHERE id={ph}",
            (status, now, message, job_id),
        )
        conn.commit()


def get_recent_jobs(n: int = 20) -> list[dict]:
    ph = "%s" if USE_POSTGRES else "?"
    with _lock, _conn() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM jobs ORDER BY id DESC LIMIT {ph}", (n,))
        rows = cur.fetchall()
    if USE_POSTGRES:
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in rows]
    return [dict(r) for r in rows]
