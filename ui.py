# ui.py
# Modern UI for TDD Inventory System
# Uses ttkbootstrap for a cleaner, modern look
# Connects directly to backend functions in app.py

import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox, simpledialog
from app import (
    create_event, view_events, delete_event,
    add_collateral, view_collaterals, update_collateral, delete_collateral,
    view_logs, get_summary
)
import datetime


# -----------------------------
# Helper Functions
# -----------------------------

def refresh_events():
    """Refresh the Events table"""
    for row in event_table.get_children():
        event_table.delete(row)
    for e in view_events():
        event_table.insert('', 'end', values=e)


def refresh_collaterals():
    """Refresh the Collaterals table"""
    for row in collateral_table.get_children():
        collateral_table.delete(row)
    for c in view_collaterals():
        collateral_table.insert('', 'end', values=c)


def refresh_logs():
    """Refresh the Logs table"""
    for row in logs_table.get_children():
        logs_table.delete(row)
    for l in view_logs():
        logs_table.insert('', 'end', values=l)


def show_summary():
    """Display quick summary in popup"""
    summary = get_summary()
    msg = "\n".join([f"{k}: {v}" for k, v in summary.items()])
    messagebox.showinfo("System Summary", msg)


# -----------------------------
# Event Handlers
# -----------------------------

def handle_add_event():
    """Prompt user to add a new event"""
    name = simpledialog.askstring("Add Event", "Enter Event Name:")
    if name:
        start = simpledialog.askstring("Add Event", "Enter Start Date (YYYY-MM-DD):")
        end = simpledialog.askstring("Add Event", "Enter End Date (YYYY-MM-DD):")
        if start and end:
            create_event(name, start, end)
            refresh_events()
            messagebox.showinfo("Success", "Event added successfully!")
        else:
            messagebox.showwarning("Warning", "Please enter both start and end dates.")


def handle_delete_event():
    """Delete selected event"""
    selected = event_table.selection()
    if not selected:
        messagebox.showwarning("Warning", "No event selected.")
        return

    confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this event?")
    if confirm:
        event_id = event_table.item(selected[0], "values")[0]
        delete_event(event_id)
        refresh_events()
        messagebox.showinfo("Deleted", "Event deleted successfully.")


def handle_add_collateral():
    """Prompt user to add a new collateral item"""
    name = simpledialog.askstring("Add Collateral", "Enter Collateral Name:")
    qty = simpledialog.askinteger("Add Collateral", "Enter Quantity:")
    if name and qty is not None:
        add_collateral(name, qty)
        refresh_collaterals()
        messagebox.showinfo("Success", "Collateral added successfully!")


def handle_update_collateral():
    """Prompt user to update collateral quantity"""
    selected = collateral_table.selection()
    if not selected:
        messagebox.showwarning("Warning", "No collateral selected.")
        return

    item = collateral_table.item(selected[0], "values")
    new_qty = simpledialog.askinteger("Update Collateral", f"Enter new quantity for {item[1]}:", initialvalue=item[2])
    if new_qty is not None:
        update_collateral(item[0], new_qty)
        refresh_collaterals()
        messagebox.showinfo("Updated", f"Quantity for {item[1]} updated.")


def handle_delete_collateral():
    """Delete selected collateral"""
    selected = collateral_table.selection()
    if not selected:
        messagebox.showwarning("Warning", "No collateral selected.")
        return

    confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this collateral?")
    if confirm:
        item_id = collateral_table.item(selected[0], "values")[0]
        delete_collateral(item_id)
        refresh_collaterals()
        messagebox.showinfo("Deleted", "Collateral deleted successfully.")


# -----------------------------
# UI Initialization
# -----------------------------

app = tb.Window(themename="superhero")
app.title("TDD Inventory System")
app.geometry("950x600")

notebook = tb.Notebook(app, bootstyle="primary")
notebook.pack(fill='both', expand=True, padx=10, pady=10)


# --- Events Tab ---
events_frame = tb.Frame(notebook)
notebook.add(events_frame, text="🗓 Events")

event_table = tb.Treeview(events_frame, columns=("ID", "Name", "Start", "End", "Modified"), show='headings', bootstyle="info")
for col in ("ID", "Name", "Start", "End", "Modified"):
    event_table.heading(col, text=col)
    event_table.column(col, width=150)
event_table.pack(fill='both', expand=True, pady=5)

tb.Button(events_frame, text="Add Event", command=handle_add_event, bootstyle="success").pack(side='left', padx=5)
tb.Button(events_frame, text="Delete Event", command=handle_delete_event, bootstyle="danger").pack(side='left', padx=5)
tb.Button(events_frame, text="Refresh", command=refresh_events, bootstyle="info").pack(side='left', padx=5)


# --- Collaterals Tab ---
collateral_frame = tb.Frame(notebook)
notebook.add(collateral_frame, text="📦 Collaterals")

collateral_table = tb.Treeview(collateral_frame, columns=("ID", "Name", "Quantity", "Modified"), show='headings', bootstyle="secondary")
for col in ("ID", "Name", "Quantity", "Modified"):
    collateral_table.heading(col, text=col)
    collateral_table.column(col, width=150)
collateral_table.pack(fill='both', expand=True, pady=5)

tb.Button(collateral_frame, text="Add", command=handle_add_collateral, bootstyle="success").pack(side='left', padx=5)
tb.Button(collateral_frame, text="Update", command=handle_update_collateral, bootstyle="warning").pack(side='left', padx=5)
tb.Button(collateral_frame, text="Delete", command=handle_delete_collateral, bootstyle="danger").pack(side='left', padx=5)
tb.Button(collateral_frame, text="Refresh", command=refresh_collaterals, bootstyle="info").pack(side='left', padx=5)


# --- Logs & Summary Tab ---
logs_frame = tb.Frame(notebook)
notebook.add(logs_frame, text="📊 Logs & Summary")

logs_table = tb.Treeview(logs_frame, columns=("ID", "Action", "Timestamp"), show='headings', bootstyle="dark")
for col in ("ID", "Action", "Timestamp"):
    logs_table.heading(col, text=col)
    logs_table.column(col, width=200)
logs_table.pack(fill='both', expand=True, pady=5)

tb.Button(logs_frame, text="Refresh Logs", command=refresh_logs, bootstyle="info").pack(side='left', padx=5)
tb.Button(logs_frame, text="Show Summary", command=show_summary, bootstyle="primary").pack(side='left', padx=5)


# --- Status Bar ---
status = tb.Label(app, text=f"Last synced: Never | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                  bootstyle="secondary", anchor="e")
status.pack(fill='x', side='bottom')

# Initialize data on startup
refresh_events()
refresh_collaterals()
refresh_logs()

app.mainloop()
