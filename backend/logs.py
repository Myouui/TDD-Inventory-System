"""Simple logging for actions into a separate logs.db file.

Functions:
- log_action(actor, action, details)
- view_logs(limit=100)
"""
from typing import List, Tuple
import datetime
import os
import sqlite3

LOG_DB = os.path.join('data', 'logs.db')


def _get_conn():
    os.makedirs(os.path.dirname(LOG_DB), exist_ok=True)
    return sqlite3.connect(LOG_DB)


def _create_logs_table(conn=None):
    close = False
    if conn is None:
        conn = _get_conn()
        close = True
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            when_ts TEXT,
            actor TEXT,
            action TEXT,
            details TEXT
        )
        """
    )
    conn.commit()
    if close:
        conn.close()


def log_action(actor: str, action: str, details: str = None) -> int:
    """Insert a log entry and return the inserted id."""
    _create_logs_table()
    conn = _get_conn()
    cur = conn.cursor()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("INSERT INTO logs (when_ts, actor, action, details) VALUES (?, ?, ?, ?)", (ts, actor, action, details))
    conn.commit()
    lid = cur.lastrowid
    conn.close()
    return lid


def view_logs(limit: int = 200) -> List[Tuple[int, str, str, str, str]]:
    """Return recent log rows (id, when_ts, actor, action, details)."""
    _create_logs_table()
    conn = _get_conn()
    cur = conn.cursor()
    rows = cur.execute("SELECT id, when_ts, actor, action, details FROM logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows
