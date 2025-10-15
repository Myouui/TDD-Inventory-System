import sqlite3
import os
from datetime import datetime

# ----------------------------
# DATABASE CONNECTION
# ----------------------------
def get_connection():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect("data/inventory.db")


# ----------------------------
# INITIAL SETUP (if missing)
# ----------------------------
def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_name TEXT NOT NULL,
        location TEXT,
        start_date TEXT,
        end_date TEXT,
        last_modified TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS collaterals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        quantity INTEGER DEFAULT 0,
        event_id INTEGER,
        last_modified TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (event_id) REFERENCES events(id)
    )
    """)

    # Transactions table to record usages/restocks of items
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER,
        event_id INTEGER,
        delta INTEGER,
        timestamp TEXT
    )
    """)

    conn.commit()
    conn.close()
    # ensure migration for location column
    ensure_location_column()


def ensure_location_column():
    """Add 'location' column to events table if it doesn't exist (safe migration)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cols = [row[1] for row in cursor.execute("PRAGMA table_info(events)").fetchall()]
    except Exception:
        cols = []
    if 'location' not in cols:
        try:
            cursor.execute("ALTER TABLE events ADD COLUMN location TEXT")
            conn.commit()
        except Exception:
            # Older SQLite or unexpected schema: ignore and continue
            pass
    conn.close()


# ----------------------------
# EVENT FUNCTIONS
# ----------------------------
def create_event(name, start_date=None, end_date=None, location=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO events (event_name, location, start_date, end_date, last_modified)
        VALUES (?, ?, ?, ?, ?)
    """, (name, location, start_date, end_date, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def update_event(event_id, name, start_date, end_date, location=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE events
        SET event_name=?, location=?, start_date=?, end_date=?, last_modified=?
        WHERE id=?
    """, (name, location, start_date, end_date, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), event_id))
    conn.commit()
    conn.close()


def delete_event(event_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM events WHERE id=?", (event_id,))
    conn.commit()
    conn.close()


# ----------------------------
# COLLATERAL FUNCTIONS
# ----------------------------
def create_collateral(item_name, quantity, event_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO collaterals (item_name, quantity, event_id, last_modified)
        VALUES (?, ?, ?, ?)
    """, (item_name, quantity, event_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id


def update_collateral(item_id, item_name, quantity, event_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE collaterals
        SET item_name=?, quantity=?, event_id=?, last_modified=?
        WHERE id=?
    """, (item_name, quantity, event_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), item_id))
    conn.commit()
    conn.close()


def delete_collateral(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM collaterals WHERE id=?", (item_id,))
    conn.commit()
    conn.close()


def spend_collateral(item_id, delta, event_id=None):
    """Adjust an item's quantity by delta (negative to spend). Records a transaction."""
    conn = get_connection()
    cursor = conn.cursor()
    # get current qty
    cur = cursor.execute("SELECT quantity FROM collaterals WHERE id=?", (item_id,)).fetchone()
    if not cur:
        conn.close()
        raise ValueError("Item not found")
    new_qty = max((cur[0] or 0) + delta, 0)
    cursor.execute("UPDATE collaterals SET quantity=?, last_modified=? WHERE id=?", (new_qty, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), item_id))
    cursor.execute("INSERT INTO transactions (item_id, event_id, delta, timestamp) VALUES (?, ?, ?, ?)", (item_id, event_id, delta, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return new_qty


def get_item_summary():
    """Return list of items with id, name, quantity, last_modified, last_event_used (if any)."""
    conn = get_connection()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT id, item_name, quantity, last_modified FROM collaterals ORDER BY id DESC").fetchall()
    summary = []
    for r in rows:
        # find last transaction that touched this item where delta < 0 (spent)
        last_tx = cursor.execute("SELECT event_id, timestamp FROM transactions WHERE item_id=? AND delta<0 ORDER BY id DESC LIMIT 1", (r[0],)).fetchone()
        last_event = last_tx[0] if last_tx else None
        last_time = last_tx[1] if last_tx else r[3]
        summary.append((r[0], r[1], r[2], last_event, last_time))
    conn.close()
    return summary


def get_events():
    """Return list of (id, event_name)."""
    conn = get_connection()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT id, event_name FROM events ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def get_transactions(item_id):
    """Return transactions for an item with event names when available."""
    conn = get_connection()
    cursor = conn.cursor()
    rows = cursor.execute(
        "SELECT t.id, t.delta, t.timestamp, e.event_name FROM transactions t LEFT JOIN events e ON t.event_id = e.id WHERE t.item_id=? ORDER BY t.id DESC",
        (item_id,),
    ).fetchall()
    conn.close()
    return rows


# ----------------------------
# RUN SETUP ONCE
# ----------------------------
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")


# ----------------------------
# UI compatibility aliases
# ----------------------------
# Ensure the set of function names expected by `ui.py` are available
# regardless of whether this module defines CLI-style functions (add_/edit_)
# or API-style functions (create_/update_/delete_). This keeps backward
# compatibility between the console UI and the tkinter UI.
globals_map = globals()

# Events
if 'create_event' not in globals_map and 'add_event' in globals_map:
    create_event = globals_map['add_event']
if 'add_event' not in globals_map and 'create_event' in globals_map:
    add_event = globals_map['create_event']

if 'update_event' not in globals_map and 'edit_event' in globals_map:
    update_event = globals_map['edit_event']
if 'edit_event' not in globals_map and 'update_event' in globals_map:
    edit_event = globals_map['update_event']

if 'delete_event' not in globals_map and 'remove_event' in globals_map:
    delete_event = globals_map['remove_event']

# Collaterals
if 'create_collateral' not in globals_map and 'add_collateral' in globals_map:
    create_collateral = globals_map['add_collateral']
if 'add_collateral' not in globals_map and 'create_collateral' in globals_map:
    add_collateral = globals_map['create_collateral']

if 'update_collateral' not in globals_map and 'edit_collateral' in globals_map:
    update_collateral = globals_map['edit_collateral']
if 'edit_collateral' not in globals_map and 'update_collateral' in globals_map:
    edit_collateral = globals_map['update_collateral']

if 'delete_collateral' not in globals_map and 'remove_collateral' in globals_map:
    delete_collateral = globals_map['remove_collateral']

