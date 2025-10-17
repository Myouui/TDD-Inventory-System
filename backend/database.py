"""Database helpers for the TDD Inventory System.

Provides a connection factory and the function to create necessary tables.
"""
import os
import sqlite3
from typing import Iterator

DB_PATH = os.path.join('data', 'inventory.db')
LOG_DB_PATH = os.path.join('data', 'logs.db')


def get_connection(path: str = None) -> sqlite3.Connection:
    """Return a sqlite3 connection to the inventory database.

    If path is not provided, uses the default `data/inventory.db`.
    Caller should close the connection when finished.
    """
    p = path or DB_PATH
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return sqlite3.connect(p)


def create_tables(conn: sqlite3.Connection = None):
    """Create the events, collaterals and transactions tables if missing.

    If a connection is provided, use it; otherwise open a temp connection.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_name TEXT NOT NULL,
        location TEXT,
        start_date TEXT,
        end_date TEXT,
        last_modified TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS collaterals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        quantity INTEGER DEFAULT 0,
        event_id INTEGER,
        last_modified TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (event_id) REFERENCES events(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER,
        event_id INTEGER,
        delta INTEGER,
        timestamp TEXT
    )
    """)

    conn.commit()
    if close_conn:
        conn.close()


def init_db():
    """Convenience function to initialize the database files and tables."""
    create_tables()
