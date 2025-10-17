"""Event-related database operations.

Functions:
- create_event
- update_event
- delete_event
- list_events
- search_events
"""
from typing import List, Tuple, Optional
import datetime
from .database import get_connection


def create_event(name: str, start_date: Optional[str] = None, end_date: Optional[str] = None, location: Optional[str] = None) -> int:
    """Create a new event and return its id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO events (event_name, location, start_date, end_date, last_modified)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, location, start_date, end_date, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id


def update_event(event_id: int, name: str, start_date: Optional[str], end_date: Optional[str], location: Optional[str] = None) -> None:
    """Update an event's data."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE events
        SET event_name=?, location=?, start_date=?, end_date=?, last_modified=?
        WHERE id=?
        """,
        (name, location, start_date, end_date, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), event_id),
    )
    conn.commit()
    conn.close()


def delete_event(event_id: int) -> None:
    """Delete an event by id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM events WHERE id=?", (event_id,))
    conn.commit()
    conn.close()


def list_events() -> List[Tuple[int, str]]:
    """Return a list of (id, event_name) tuples."""
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute("SELECT id, event_name FROM events ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def search_events(term: str) -> List[Tuple[int, str]]:
    """Search events by name (simple LIKE search)."""
    conn = get_connection()
    cur = conn.cursor()
    q = f"%{term}%"
    rows = cur.execute("SELECT id, event_name FROM events WHERE event_name LIKE ? ORDER BY id DESC", (q,)).fetchall()
    conn.close()
    return rows
