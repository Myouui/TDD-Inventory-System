import sqlite3
import os
from datetime import datetime

# === PATHS & SETUP ===
DB_PATH = "data/inventory.db"
LOG_DB_PATH = "data/logs.db"
os.makedirs("data", exist_ok=True)


# === DATABASE INITIALIZATION ===
def create_tables():
    """Create/upgrade main tables and logs DB. Safe to run repeatedly."""
    conn = sqlite3.connect(DB_PATH)
    # events table (includes last_modified)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_name TEXT NOT NULL,
        start_date TEXT,
        end_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_modified TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    # collaterals table (linked to events)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS collaterals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER,
        item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_modified TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (event_id) REFERENCES events (id)
    )
    """)
    conn.commit()
    conn.close()

    # separate logs DB
    conn2 = sqlite3.connect(LOG_DB_PATH)
    conn2.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        action TEXT,
        target TEXT,
        description TEXT
    )
    """)
    conn2.commit()
    conn2.close()


# === LOGGING FUNCTIONS (logs.db) ===
def log_action(action, target, description):
    """Append an activity record to logs.db."""
    conn = sqlite3.connect(LOG_DB_PATH)
    conn.execute(
        "INSERT INTO logs (timestamp, action, target, description) VALUES (?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), action, target, description)
    )
    conn.commit()
    conn.close()


def view_logs():
    """Print activity logs (newest first)."""
    conn = sqlite3.connect(LOG_DB_PATH)
    rows = conn.execute("SELECT timestamp, action, target, description FROM logs ORDER BY id DESC").fetchall()
    conn.close()
    print("\n🧾 ACTIVITY LOG")
    print("-" * 80)
    if not rows:
        print("No logs found.\n")
        return
    for r in rows:
        print(f"[{r[0]}] ({r[1]}) {r[2]} — {r[3]}")
    print("-" * 80 + "\n")


# === UTIL HELPERS ===
def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def input_cancel(prompt):
    """Read input and treat 'cancel' or empty as cancellation (returns None)."""
    v = input(prompt).strip()
    if v.lower() == "cancel" or v == "":
        return None
    return v


def safe_int(s, default=None):
    try:
        return int(s)
    except Exception:
        return default


# === EVENT OPERATIONS ===
def create_event():
    """Create new event with cancellation support."""
    print("\n--- Create Event (type 'cancel' or leave blank to abort) ---")
    name = input_cancel("Event name: ")
    if not name:
        print("Cancelled.\n")
        return
    start = input_cancel("Start date (YYYY-MM-DD): ")
    if start is None:
        print("Cancelled.\n")
        return
    end = input_cancel("End date (YYYY-MM-DD): ")
    if end is None:
        print("Cancelled.\n")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO events (event_name, start_date, end_date, last_modified) VALUES (?, ?, ?, ?)",
        (name, start, end, now_ts())
    )
    conn.commit()
    conn.close()
    log_action("CREATE", "Event", f"Created event '{name}' ({start} to {end})")
    print(f"✅ Event '{name}' created.\n")


def list_events(return_rows=False):
    """Return and print events. If return_rows True, returns rows list."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, event_name, start_date, end_date, last_modified FROM events ORDER BY id DESC"
    ).fetchall()
    conn.close()
    if not rows:
        print("⚠️ No events found.\n")
        return [] if return_rows else None

    print("\n📅 EVENTS")
    print("-" * 80)
    for r in rows:
        print(f"ID: {r[0]} | {r[1]} ({r[2]} → {r[3]}) | Last Modified: {r[4]}")
    print("-" * 80 + "\n")
    return rows if return_rows else None


def delete_event():
    """Delete event and its collaterals after confirmation."""
    rows = list_events(return_rows=True)
    if not rows:
        return
    eid = input_cancel("Enter Event ID to delete: ")
    if not eid:
        print("Cancelled.\n")
        return
    eid_i = safe_int(eid)
    if eid_i is None:
        print("Invalid ID.\n")
        return
    conn = sqlite3.connect(DB_PATH)
    event = conn.execute("SELECT event_name FROM events WHERE id = ?", (eid_i,)).fetchone()
    if not event:
        print("Event not found.\n")
        conn.close()
        return
    confirm = input(f"Are you sure you want to delete '{event[0]}' and all its collaterals? (y/N): ").strip().lower()
    if confirm != "y":
        print("Cancelled.\n")
        conn.close()
        return
    conn.execute("DELETE FROM collaterals WHERE event_id = ?", (eid_i,))
    conn.execute("DELETE FROM events WHERE id = ?", (eid_i,))
    conn.commit()
    conn.close()
    log_action("DELETE", "Event", f"Deleted event '{event[0]}' (ID {eid_i}) and its collaterals")
    print("✅ Deleted event and related collaterals.\n")


# === COLLATERAL OPERATIONS ===
def add_collateral():
    """Add collateral linked to an event."""
    conn = sqlite3.connect(DB_PATH)
    events = conn.execute("SELECT id, event_name FROM events ORDER BY id DESC").fetchall()
    if not events:
        print("⚠️ No events found. Create an event first.\n")
        conn.close()
        return
    print("\nSelect event to add collateral (type cancel to abort):")
    for e in events:
        print(f"{e[0]}. {e[1]}")
    sel = input_cancel("Event ID: ")
    if not sel:
        print("Cancelled.\n")
        conn.close()
        return
    sel_i = safe_int(sel)
    if sel_i is None:
        print("Invalid ID.\n")
        conn.close()
        return
    item = input_cancel("Item name: ")
    if not item:
        print("Cancelled.\n")
        conn.close()
        return
    qty_s = input_cancel("Quantity: ")
    if not qty_s:
        print("Cancelled.\n")
        conn.close()
        return
    qty = safe_int(qty_s)
    if qty is None:
        print("Invalid quantity.\n")
        conn.close()
        return

    conn.execute(
        "INSERT INTO collaterals (event_id, item_name, quantity, last_modified) VALUES (?, ?, ?, ?)",
        (sel_i, item, qty, now_ts())
    )
    conn.commit()
    conn.close()
    log_action("CREATE", "Collateral", f"Added '{item}' Qty:{qty} to Event ID {sel_i}")
    print(f"✅ Collateral '{item}' added to event.\n")


def view_event_inventory():
    """Choose event and view its collaterals."""
    conn = sqlite3.connect(DB_PATH)
    events = conn.execute("SELECT id, event_name FROM events ORDER BY id DESC").fetchall()
    if not events:
        print("⚠️ No events exist.\n")
        conn.close()
        return
    print("\nSelect event to view inventory (type cancel to abort):")
    for e in events:
        print(f"{e[0]}. {e[1]}")
    sel = input_cancel("Event ID: ")
    if not sel:
        print("Cancelled.\n")
        conn.close()
        return
    sel_i = safe_int(sel)
    if sel_i is None:
        print("Invalid ID.\n")
        conn.close()
        return
    rows = conn.execute(
        "SELECT id, item_name, quantity, last_modified FROM collaterals WHERE event_id = ? ORDER BY id",
        (sel_i,)
    ).fetchall()
    event_name_row = conn.execute("SELECT event_name FROM events WHERE id = ?", (sel_i,)).fetchone()
    conn.close()
    if not event_name_row:
        print("Event not found.\n")
        return
    print(f"\n📦 Inventory for event: {event_name_row[0]}")
    print("-" * 80)
    if not rows:
        print("No collaterals for this event.\n")
        return
    for r in rows:
        print(f"ID: {r[0]} | {r[1]} — Qty: {r[2]} | Last Modified: {r[3]}")
    print("-" * 80 + "\n")


def update_quantity():
    """Adjust quantity for a selected collateral."""
    conn = sqlite3.connect(DB_PATH)
    events = conn.execute("SELECT id, event_name FROM events ORDER BY id DESC").fetchall()
    if not events:
        print("⚠️ No events.\n")
        conn.close()
        return
    print("\nSelect event (cancel to abort):")
    for e in events:
        print(f"{e[0]}. {e[1]}")
    sel = input_cancel("Event ID: ")
    if not sel:
        print("Cancelled.\n")
        conn.close()
        return
    sel_i = safe_int(sel)
    if sel_i is None:
        print("Invalid ID.\n")
        conn.close()
        return
    items = conn.execute("SELECT id, item_name, quantity FROM collaterals WHERE event_id = ? ORDER BY id", (sel_i,)).fetchall()
    if not items:
        print("No collaterals for this event.\n")
        conn.close()
        return
    print("\nSelect collateral to update (cancel to abort):")
    for it in items:
        print(f"{it[0]}. {it[1]} (Qty: {it[2]})")
    cid = input_cancel("Collateral ID: ")
    if not cid:
        print("Cancelled.\n")
        conn.close()
        return
    cid_i = safe_int(cid)
    if cid_i is None:
        print("Invalid ID.\n")
        conn.close()
        return
    change_s = input_cancel("Change amount (negative to subtract): ")
    if change_s is None:
        print("Cancelled.\n")
        conn.close()
        return
    change = safe_int(change_s)
    if change is None:
        print("Invalid number.\n")
        conn.close()
        return

    # fetch current value for logging
    current = conn.execute("SELECT item_name, quantity FROM collaterals WHERE id = ?", (cid_i,)).fetchone()
    if not current:
        print("Collateral not found.\n")
        conn.close()
        return
    new_qty = current[1] + change
    conn.execute("UPDATE collaterals SET quantity = ?, last_modified = ? WHERE id = ?", (new_qty, now_ts(), cid_i))
    conn.commit()
    conn.close()
    log_action("UPDATE", "Collateral", f"Changed '{current[0]}' from {current[1]} → {new_qty}")
    print("✅ Quantity updated.\n")


def delete_collateral():
    """Delete a single collateral record."""
    conn = sqlite3.connect(DB_PATH)
    events = conn.execute("SELECT id, event_name FROM events ORDER BY id DESC").fetchall()
    if not events:
        print("⚠️ No events.\n")
        conn.close()
        return
    print("\nSelect event to delete collateral from (cancel to abort):")
    for e in events:
        print(f"{e[0]}. {e[1]}")
    sel = input_cancel("Event ID: ")
    if not sel:
        print("Cancelled.\n")
        conn.close()
        return
    sel_i = safe_int(sel)
    if sel_i is None:
        print("Invalid ID.\n")
        conn.close()
        return
    items = conn.execute("SELECT id, item_name, quantity FROM collaterals WHERE event_id = ?", (sel_i,)).fetchall()
    if not items:
        print("No collaterals for this event.\n")
        conn.close()
        return
    print("\nSelect collateral to delete (cancel to abort):")
    for it in items:
        print(f"{it[0]}. {it[1]} (Qty: {it[2]})")
    cid = input_cancel("Collateral ID: ")
    if not cid:
        print("Cancelled.\n")
        conn.close()
        return
    cid_i = safe_int(cid)
    if cid_i is None:
        print("Invalid ID.\n")
        conn.close()
        return
    # confirm and delete
    item_name_row = conn.execute("SELECT item_name FROM collaterals WHERE id = ?", (cid_i,)).fetchone()
    if not item_name_row:
        print("Collateral not found.\n")
        conn.close()
        return
    confirm = input(f"Confirm delete '{item_name_row[0]}'? (y/N): ").strip().lower()
    if confirm != "y":
        print("Cancelled.\n")
        conn.close()
        return
    conn.execute("DELETE FROM collaterals WHERE id = ?", (cid_i,))
    conn.commit()
    conn.close()
    log_action("DELETE", "Collateral", f"Deleted '{item_name_row[0]}' (ID {cid_i})")
    print("✅ Collateral deleted.\n")


# === SEARCH & FILTER ===
def search_events():
    """Search events by name or date range."""
    print("\n--- Search / Filter Events (leave blank to skip a filter) ---")
    term = input("Event name contains: ").strip()
    start = input("Start date >= (YYYY-MM-DD): ").strip()
    end = input("End date <= (YYYY-MM-DD): ").strip()
    query = "SELECT id, event_name, start_date, end_date, last_modified FROM events WHERE 1=1"
    params = []
    if term:
        query += " AND event_name LIKE ?"
        params.append(f"%{term}%")
    if start:
        query += " AND start_date >= ?"
        params.append(start)
    if end:
        query += " AND end_date <= ?"
        params.append(end)
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    print("\n🔎 Event Search Results")
    print("-" * 80)
    if not rows:
        print("No matching events.\n")
        return
    for r in rows:
        print(f"ID:{r[0]} | {r[1]} ({r[2]} → {r[3]}) | Last Modified: {r[4]}")
    print("-" * 80 + "\n")


def search_collaterals():
    """Search collaterals by name, event, min/max quantity."""
    print("\n--- Search / Filter Collaterals (leave blank to skip) ---")
    name = input("Item name contains: ").strip()
    min_q = input("Minimum quantity: ").strip()
    max_q = input("Maximum quantity: ").strip()
    event_term = input("Event name contains (optional): ").strip()

    query = """
        SELECT c.id, c.item_name, c.quantity, e.event_name, c.last_modified
        FROM collaterals c
        JOIN events e ON c.event_id = e.id
        WHERE 1=1
    """
    params = []
    if name:
        query += " AND c.item_name LIKE ?"
        params.append(f"%{name}%")
    if min_q and min_q.isdigit():
        query += " AND c.quantity >= ?"
        params.append(int(min_q))
    if max_q and max_q.isdigit():
        query += " AND c.quantity <= ?"
        params.append(int(max_q))
    if event_term:
        query += " AND e.event_name LIKE ?"
        params.append(f"%{event_term}%")

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    print("\n🔎 Collateral Search Results")
    print("-" * 80)
    if not rows:
        print("No matching collaterals.\n")
        return
    for r in rows:
        print(f"ID:{r[0]} | {r[1]} — Qty:{r[2]} | Event:{r[3]} | Last Modified:{r[4]}")
    print("-" * 80 + "\n")


# === SUMMARY / REPORTS ===
def show_summary():
    """Display a quick inventory summary."""
    conn = sqlite3.connect(DB_PATH)
    total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    total_collateral_types = conn.execute("SELECT COUNT(*) FROM collaterals").fetchone()[0]
    total_quantity = conn.execute("SELECT IFNULL(SUM(quantity),0) FROM collaterals").fetchone()[0]
    most = conn.execute("SELECT item_name, quantity FROM collaterals ORDER BY quantity DESC LIMIT 1").fetchone()
    least = conn.execute("SELECT item_name, quantity FROM collaterals ORDER BY quantity ASC LIMIT 1").fetchone()
    last_update = conn.execute("SELECT MAX(last_modified) FROM collaterals").fetchone()[0]
    conn.close()

    print("\n📊 SUMMARY & REPORTS")
    print("-" * 80)
    print(f"Total events: {total_events}")
    print(f"Total collateral types: {total_collateral_types}")
    print(f"Total quantity across all events: {total_quantity}")
    if most:
        print(f"Most stocked: {most[0]} ({most[1]})")
    if least:
        print(f"Least stocked: {least[0]} ({least[1]})")
    print(f"Last item modification: {last_update if last_update else 'N/A'}")
    print("-" * 80 + "\n")


# === MENUS (simplified main menu + submenus) ===
def manage_events_menu():
    while True:
        print("=== Manage Events ===")
        print("1. Create Event")
        print("2. View Events")
        print("3. Delete Event")
        print("4. Back")
        c = input("Choose: ").strip()
        if c == "1":
            create_event()
        elif c == "2":
            list_events()
        elif c == "3":
            delete_event()
        elif c == "4":
            return
        else:
            print("Invalid choice.\n")


def manage_collaterals_menu():
    while True:
        print("=== Manage Collaterals ===")
        print("1. Add Collateral")
        print("2. View Event Inventory")
        print("3. Update Quantity")
        print("4. Delete Collateral")
        print("5. Back")
        c = input("Choose: ").strip()
        if c == "1":
            add_collateral()
        elif c == "2":
            view_event_inventory()
        elif c == "3":
            update_quantity()
        elif c == "4":
            delete_collateral()
        elif c == "5":
            return
        else:
            print("Invalid choice.\n")


def reports_menu():
    while True:
        print("=== Search / Reports ===")
        print("1. Search Events")
        print("2. Search Collaterals")
        print("3. View Summary")
        print("4. View Activity Log")
        print("5. Back")
        c = input("Choose: ").strip()
        if c == "1":
            search_events()
        elif c == "2":
            search_collaterals()
        elif c == "3":
            show_summary()
        elif c == "4":
            view_logs()
        elif c == "5":
            return
        else:
            print("Invalid choice.\n")


def main_menu():
    create_tables()
    while True:
        print("=== TDD Inventory System ===")
        print("1. Manage Events")
        print("2. Manage Collaterals")
        print("3. Search / Reports")
        print("4. Exit")
        choice = input("Choose: ").strip()
        if choice == "1":
            manage_events_menu()
        elif choice == "2":
            manage_collaterals_menu()
        elif choice == "3":
            reports_menu()
        elif choice == "4":
            print("Goodbye 👋")
            break
        else:
            print("Invalid choice.\n")

# === UI COMPATIBILITY ALIASES ===
# These map backend functions to names expected by the UI.
add_event = create_event          # add_event → create_event
view_events = list_events         # view_events → list_events
delete_event = delete_event       # same name
update_event = lambda: None       # placeholder for now (UI edit feature later)
add_item = add_collateral         # add_item → add_collateral
view_inventory = view_event_inventory  # view_inventory → view_event_inventory

if __name__ == "__main__":
    main_menu()
