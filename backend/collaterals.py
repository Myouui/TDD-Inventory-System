"""Collateral-related operations.

Provides create, update, delete and summary operations for items.
"""
from typing import List, Tuple, Optional
import datetime
from .database import get_connection


def create_collateral(item_name: str, quantity: int, event_id: Optional[int] = None) -> int:
    """Insert a new collateral and return its id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO collaterals (item_name, quantity, event_id, last_modified)
        VALUES (?, ?, ?, ?)
        """,
        (item_name, quantity, event_id, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id


def update_collateral(item_id: int, item_name: str, quantity: int, event_id: Optional[int] = None) -> None:
    """Update a collateral record."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE collaterals
        SET item_name=?, quantity=?, event_id=?, last_modified=?
        WHERE id=?
        """,
        (item_name, quantity, event_id, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), item_id),
    )
    conn.commit()
    conn.close()


def delete_collateral(item_id: int) -> None:
    """Delete a collateral by id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM collaterals WHERE id=?", (item_id,))
    conn.commit()
    conn.close()


def spend_collateral(item_id: int, delta: int, event_id: Optional[int] = None) -> int:
    """Adjust an item's quantity by delta and record transaction. Returns new quantity."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT quantity FROM collaterals WHERE id=?", (item_id,))
    cur_row = cur.fetchone()
    if not cur_row:
        conn.close()
        raise ValueError("Item not found")
    new_qty = max((cur_row[0] or 0) + delta, 0)
    cur.execute("UPDATE collaterals SET quantity=?, last_modified=? WHERE id=?", (new_qty, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), item_id))
    cur.execute("INSERT INTO transactions (item_id, event_id, delta, timestamp) VALUES (?, ?, ?, ?)", (item_id, event_id, delta, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return new_qty


def get_item_summary() -> List[Tuple[int, str, int, Optional[int], Optional[str]]]:
    """Return summary rows: (id, name, qty, last_event, last_time)."""
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute("SELECT id, item_name, quantity, last_modified FROM collaterals ORDER BY id DESC").fetchall()
    summary = []
    for r in rows:
        last_tx = cur.execute("SELECT event_id, timestamp FROM transactions WHERE item_id=? AND delta<0 ORDER BY id DESC LIMIT 1", (r[0],)).fetchone()
        last_event = last_tx[0] if last_tx else None
        last_time = last_tx[1] if last_tx else r[3]
        summary.append((r[0], r[1], r[2], last_event, last_time))
    conn.close()
    return summary


def get_transactions(item_id: int) -> List[Tuple[int, int, str, Optional[str]]]:
    """Return transactions for an item with optional event name."""
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT t.id, t.delta, t.timestamp, e.event_name FROM transactions t LEFT JOIN events e ON t.event_id = e.id WHERE t.item_id=? ORDER BY t.id DESC",
        (item_id,),
    ).fetchall()
    conn.close()
    return rows
