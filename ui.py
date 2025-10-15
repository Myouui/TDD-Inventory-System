import os
import sqlite3
import calendar
import datetime
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import messagebox, simpledialog
from app import (
    create_event,
    delete_event,
    update_event,
    create_collateral,
    delete_collateral,
    update_collateral,
    spend_collateral,
    get_item_summary,
    get_events,
    get_transactions,
    init_db,
)

# ----------------------------
# DATABASE CONNECTION HELPERS
# ----------------------------
def get_connection():
    """Connect to the same local database used by the backend."""
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect("data/inventory.db")


# ----------------------------
# MAIN APPLICATION WINDOW
# ----------------------------
class InventoryApp(ttk.Window):
    def __init__(self):
        super().__init__(themename="cosmo")
        self.title("TDD Inventory System")
        self.geometry("950x600")
        # currently selected event for collateral operations
        self.selected_event_id = None
        self.selected_event_name = None

        ttk.Label(
            self,
            text="TDD Collateral Inventory System",
            font=("Segoe UI", 20, "bold"),
        ).pack(pady=15)
        # Tabs (Items first)
        self.tabs = ttk.Notebook(self)
        self.collateral_tab = ttk.Frame(self.tabs)
        self.event_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.collateral_tab, text="Items")
        self.tabs.add(self.event_tab, text="Events")
        self.tabs.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # Build each tab
        self.build_event_tab()
        self.build_collateral_tab()
        # ensure event combobox is populated on startup
        try:
            self.load_events()
        except Exception:
            pass
        # ensure combobox is usable immediately
        try:
            self.setup_event_combo()
        except Exception:
            pass

    def setup_event_combo(self):
        """Ensure event combobox is populated, readonly, has a selection and is focusable on startup."""
        if not hasattr(self, 'event_combo'):
            return
        try:
            vals = list(self.event_combo['values'])
        except Exception:
            vals = []
        if not vals:
            # populate by loading events (safe, idempotent)
            try:
                self.load_events()
                vals = list(self.event_combo.get() and [self.event_combo.get()] or list(self.event_combo['values']))
            except Exception:
                pass
        # ensure user can interact immediately
        try:
            self.event_combo.focus_set()
            self.event_combo.update_idletasks()
        except Exception:
            pass

    # ----------------------------
    # EVENT TAB
    # ----------------------------
    def build_event_tab(self):
        header_frame = ttk.Frame(self.event_tab)
        header_frame.pack(fill=X, padx=20, pady=10)
        ttk.Label(header_frame, text="Event List", font=("Segoe UI", 14, "bold")).pack(side=LEFT)

        btn_frame = ttk.Frame(header_frame)
        btn_frame.pack(side=RIGHT)

        # use simple unicode icons for compact buttons
        ttk.Button(btn_frame, text="➕", bootstyle="success", command=lambda: self.add_event()).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="✎", bootstyle="warning", command=lambda: self.edit_event()).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑", bootstyle="danger", command=lambda: self.delete_event()).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="↻", bootstyle="info", command=lambda: self.load_events()).pack(side=LEFT, padx=5)

        # add Location column and prepare the treeview
        columns = ("ID", "Event Name", "Location", "Start Date", "End Date", "Last Modified")
        # hide ID from displaycolumns so it doesn't affect visual layout
        display_cols = [c for c in columns if c != 'ID']
        self.event_tree = ttk.Treeview(self.event_tab, columns=columns, displaycolumns=display_cols, show="headings", height=12)
        for col in columns:
            # choose heading anchor to match cell anchor for visual alignment
            if col == "ID":
                self.event_tree.heading(col, text=col, anchor=CENTER)
                self.event_tree.column(col, width=0, minwidth=0, anchor=CENTER, stretch=False)
            elif col == "Event Name":
                self.event_tree.heading(col, text=col, anchor=W)
                self.event_tree.column(col, width=320, minwidth=180, anchor=W, stretch=True)
            elif col == "Location":
                self.event_tree.heading(col, text=col, anchor=W)
                self.event_tree.column(col, width=200, minwidth=120, anchor=W, stretch=True)
            else:
                # default date/last-modified columns
                self.event_tree.heading(col, text=col, anchor=CENTER)
                self.event_tree.column(col, width=130, minwidth=80, anchor=CENTER, stretch=False)
        self.event_tree.pack(fill=BOTH, expand=True, padx=20, pady=10)
        # alternating row colors for readability
        self.event_tree.tag_configure('odd', background=(self.style.colors.info_light if hasattr(self, 'style') else '#f8f9fc'))
        self.event_tree.tag_configure('even', background='#ffffff')
        # When an event is selected, load its collaterals. Double-click will switch tabs.
        self.event_tree.bind("<<TreeviewSelect>>", self.on_event_select)
        self.event_tree.bind("<Double-1>", self.on_event_double_click)

        self.load_events()

    def load_events(self):
        """Fetch and display events from the database."""
        for row in self.event_tree.get_children():
            self.event_tree.delete(row)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, event_name, location, start_date, end_date, last_modified FROM events ORDER BY id DESC")
        events = cursor.fetchall()
        for event in events:
            tag = 'odd' if (events.index(event) % 2) == 0 else 'even'
            self.event_tree.insert("", END, values=event, tags=(tag,))
        # populate event combobox on Items tab and set a default selection if none
        try:
            # build id<->name maps for quick lookup
            ev_map_id_to_name = {e[0]: e[1] for e in events}
            ev_map_name_to_id = {e[1]: e[0] for e in events}
            # attach to self for other methods to use
            self.event_id_to_name = ev_map_id_to_name
            self.event_name_to_id = ev_map_name_to_id
            if hasattr(self, 'event_combo'):
                names = [e[1] for e in events]
                self.event_combo['values'] = names
                # if there's a previously selected id, keep it; otherwise pick the first event
                if self.selected_event_id:
                    name = self.event_id_to_name.get(self.selected_event_id)
                    if name:
                        self.event_combo.set(name)
                elif names:
                    # auto-select first event so user can operate immediately
                    try:
                        first_name = names[0]
                        self.event_combo.set(first_name)
                        self.selected_event_id = self.event_name_to_id.get(first_name)
                        self.selected_event_name = first_name
                    except Exception:
                        self.selected_event_id = None
                        self.selected_event_name = None
                    try:
                        self.load_items()
                    except Exception:
                        pass
        except Exception:
            pass
        conn.close()

    def on_event_select(self, _event=None):
        """Handle event selection: store selected event and show its collaterals."""
        selected = self.event_tree.selection()
        if not selected:
            return
        item = self.event_tree.item(selected[0])["values"]
        self.selected_event_id = item[0]
        self.selected_event_name = item[1]
        # keep collateral header static; combobox displays the selected event name
        try:
            if hasattr(self, 'event_combo') and self.selected_event_id:
                # set combobox to the event name
                name = getattr(self, 'event_id_to_name', {}).get(self.selected_event_id)
                if name:
                    self.event_combo.set(name)
        except Exception:
            pass
        self.load_items()

    def on_event_double_click(self, _ev=None):
        """On double-click, behave like selection then switch to the Items tab."""
        # ensure selection state is applied
        self.on_event_select()
        try:
            self.tabs.select(self.collateral_tab)
        except Exception:
            pass

    def add_event(self):
        """Add a new event using a modal dialog with optional calendar date pickers."""
        data = self.open_event_form_dialog()
        if not data:
            return
        name, location, start, end = data
        try:
            try:
                create_event(name, start, end, location)
            except TypeError:
                create_event(name, start, end)
            messagebox.showinfo("Success", "Event added successfully!")
            self.load_events()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def edit_event(self):
        """Edit selected event using a single modal dialog (name/location/start/end)."""
        selected = self.event_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select an event to edit.")
            return
        item = self.event_tree.item(selected[0])['values']
        event_id = item[0]
        # columns: ID, Event Name, Location, Start Date, End Date, Last Modified
        try:
            current_name = item[1]
            current_location = item[2] if len(item) > 2 else None
            current_start = item[3] if len(item) > 3 else None
            current_end = item[4] if len(item) > 4 else None
        except Exception:
            current_name = item[1]
            current_location = None
            current_start = None
            current_end = None

        data = self.open_event_form_dialog(initial=(current_name, current_location, current_start, current_end))
        if not data:
            return
        new_name, new_location, new_start, new_end = data
        try:
            try:
                update_event(event_id, new_name, new_start, new_end, new_location)
            except TypeError:
                update_event(event_id, new_name, new_start, new_end)
            messagebox.showinfo("Success", "Event updated successfully!")
            self.load_events()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def open_event_form_dialog(self, initial=None):
        """Open a modal dialog to collect event name, location, and start/end dates.
        Uses tkcalendar.DateEntry if available, otherwise falls back to simple text entries.
        Returns tuple (name, location, start, end) or None if cancelled.
        """
        dlg = ttk.Toplevel(self)
        dlg.title("Add New Event")
        dlg.transient(self)
        dlg.grab_set()
        # ensure the dialog's second column can expand so widgets are visible
        try:
            dlg.columnconfigure(1, weight=1)
        except Exception:
            pass
        # initial values if editing
        init_name = init_loc = init_start = init_end = None
        if initial and isinstance(initial, (list, tuple)):
            try:
                init_name, init_loc, init_start, init_end = initial
            except Exception:
                pass

        ttk.Label(dlg, text="Event Name:").grid(row=0, column=0, padx=8, pady=6, sticky=W)
        name_var = ttk.StringVar(value=init_name or '')
        name_entry = ttk.Entry(dlg, textvariable=name_var, width=40)
        name_entry.grid(row=0, column=1, padx=8, pady=6)

        ttk.Label(dlg, text="Location:").grid(row=1, column=0, padx=8, pady=6, sticky=W)
        location_var = ttk.StringVar(value=init_loc or '')
        location_entry = ttk.Entry(dlg, textvariable=location_var, width=40)
        location_entry.grid(row=1, column=1, padx=8, pady=6)

        # Date selection via dropdowns: Year / Month / Day to avoid DateEntry issues.
        # Year range: current_year-5 .. current_year+5
        now = datetime.date.today()
        cur_year = now.year
        year_range = list(range(cur_year - 5, cur_year + 6))

        def mk_month_options():
            return [(i, calendar.month_name[i]) for i in range(1, 13)]

        def mk_year_values():
            return [str(y) for y in year_range]

        def days_for(year, month):
            try:
                year = int(year)
                month = int(month)
            except Exception:
                return []
            _, nd = calendar.monthrange(year, month)
            return [f"{d:02d}" for d in range(1, nd + 1)]

        # START date dropdowns - default to today when not provided
        ttk.Label(dlg, text="Start Date:").grid(row=2, column=0, padx=8, pady=6, sticky=W)
        today = now
        if init_start:
            try:
                sy = init_start.split('-')
                start_year_default = sy[0]
                start_month_default = sy[1]
                start_day_default = sy[2]
            except Exception:
                start_year_default = str(today.year)
                start_month_default = f"{today.month:02d}"
                start_day_default = f"{today.day:02d}"
        else:
            start_year_default = str(today.year)
            start_month_default = f"{today.month:02d}"
            start_day_default = f"{today.day:02d}"

        start_year_var = ttk.StringVar(value=start_year_default)
        # ensure month default matches the displayed values like '10 - October'
        if start_month_default and ' - ' not in start_month_default:
            try:
                mnum = int(start_month_default)
                start_month_default = f"{mnum:02d} - {calendar.month_name[mnum]}"
            except Exception:
                pass
        start_month_var = ttk.StringVar(value=start_month_default)
        start_day_var = ttk.StringVar(value=start_day_default)
        # place the start date controls inside their own frame so they stay grouped
        start_frame = ttk.Frame(dlg)
        start_frame.grid(row=2, column=1, sticky=W+E, padx=0)
        # create comboboxes as children of the start_frame so they render correctly
        start_year_cb = ttk.Combobox(start_frame, values=mk_year_values(), textvariable=start_year_var, width=8, state='readonly')
        start_month_cb = ttk.Combobox(start_frame, values=[f"{i:02d} - {m}" for i, m in mk_month_options()], textvariable=start_month_var, width=14, state='readonly')
        start_day_cb = ttk.Combobox(start_frame, values=days_for(start_year_var.get(), start_month_var.get().split()[0]), textvariable=start_day_var, width=6, state='readonly')
        start_year_cb.grid(row=0, column=0, sticky=W, padx=(0,6))
        start_month_cb.grid(row=0, column=1, sticky=W, padx=(0,6))
        start_day_cb.grid(row=0, column=2, sticky=W)

        # END date dropdowns - default to today when not provided
        ttk.Label(dlg, text="End Date:").grid(row=3, column=0, padx=8, pady=6, sticky=W)
        if init_end:
            try:
                ey = init_end.split('-')
                end_year_default = ey[0]
                end_month_default = ey[1]
                end_day_default = ey[2]
            except Exception:
                end_year_default = str(today.year)
                end_month_default = f"{today.month:02d}"
                end_day_default = f"{today.day:02d}"
        else:
            end_year_default = str(today.year)
            end_month_default = f"{today.month:02d}"
            end_day_default = f"{today.day:02d}"

        # ensure end month default matches display format
        if end_month_default and ' - ' not in end_month_default:
            try:
                mnum = int(end_month_default)
                end_month_default = f"{mnum:02d} - {calendar.month_name[mnum]}"
            except Exception:
                pass
        end_year_var = ttk.StringVar(value=end_year_default)
        end_month_var = ttk.StringVar(value=end_month_default)
        end_day_var = ttk.StringVar(value=end_day_default)
        # place the end date controls inside their own frame so they stay grouped
        end_frame = ttk.Frame(dlg)
        end_frame.grid(row=3, column=1, sticky=W+E, padx=0)
        # create comboboxes as children of the end_frame so they render correctly
        end_year_cb = ttk.Combobox(end_frame, values=mk_year_values(), textvariable=end_year_var, width=8, state='readonly')
        end_month_cb = ttk.Combobox(end_frame, values=[f"{i:02d} - {m}" for i, m in mk_month_options()], textvariable=end_month_var, width=14, state='readonly')
        end_day_cb = ttk.Combobox(end_frame, values=days_for(end_year_var.get(), end_month_var.get().split()[0]), textvariable=end_day_var, width=6, state='readonly')
        end_year_cb.grid(row=0, column=0, sticky=W, padx=(0,6))
        end_month_cb.grid(row=0, column=1, sticky=W, padx=(0,6))
        end_day_cb.grid(row=0, column=2, sticky=W)

        # helpers to update day options when year/month change
        def update_start_days(_ev=None):
            mon = start_month_var.get().split()[0] if start_month_var.get() else ''
            vals = days_for(start_year_var.get(), mon)
            start_day_cb['values'] = vals
            if start_day_var.get() not in vals:
                start_day_var.set(vals[-1] if vals else '')

        def update_end_days(_ev=None):
            mon = end_month_var.get().split()[0] if end_month_var.get() else ''
            vals = days_for(end_year_var.get(), mon)
            end_day_cb['values'] = vals
            if end_day_var.get() not in vals:
                end_day_var.set(vals[-1] if vals else '')

        start_year_cb.bind('<<ComboboxSelected>>', update_start_days)
        start_month_cb.bind('<<ComboboxSelected>>', update_start_days)
        end_year_cb.bind('<<ComboboxSelected>>', update_end_days)
        end_month_cb.bind('<<ComboboxSelected>>', update_end_days)

        result = {'ok': False, 'name': None, 'location': None, 'start': None, 'end': None}

        def cleanup():
            """No-op cleanup for dropdown-based date widgets. Kept for compatibility with
            earlier DateEntry defensive cancel logic (left intentionally empty).
            """
            return

        def build_date_str(yvar, mvar, dvar):
            y = (yvar.get() or '').strip()
            m = (mvar.get() or '').strip()
            d = (dvar.get() or '').strip()
            if not y or not m or not d:
                return None
            # month combobox may be like '01 - January' or just '1'
            if ' ' in m:
                m = m.split()[0]
            try:
                yy = int(y)
                mm = int(m)
                dd = int(d)
                return f"{yy:04d}-{mm:02d}-{dd:02d}"
            except Exception:
                return None

        def submit(_ev=None):
            n = name_var.get().strip()
            if not n:
                messagebox.showwarning('Invalid', 'Please enter an event name.', parent=dlg)
                return
            start_s = build_date_str(start_year_var, start_month_var, start_day_var)
            end_s = build_date_str(end_year_var, end_month_var, end_day_var)
            # validate date ordering if both provided
            if start_s and end_s:
                try:
                    ds = datetime.datetime.strptime(start_s, '%Y-%m-%d')
                    de = datetime.datetime.strptime(end_s, '%Y-%m-%d')
                    if de < ds:
                        messagebox.showwarning('Invalid', 'End date must be the same or after Start date.', parent=dlg)
                        return
                except Exception:
                    # parsing failed: show generic warning
                    messagebox.showwarning('Invalid', 'Please provide valid dates (YYYY-MM-DD).', parent=dlg)
                    return

            result['name'] = n
            result['location'] = location_var.get().strip() or None
            result['start'] = start_s
            result['end'] = end_s
            result['ok'] = True
            dlg.grab_release()
            dlg.destroy()

        name_entry.bind('<Return>', lambda e: location_entry.focus_set())
        # focus moves to the start year combobox
        location_entry.bind('<Return>', lambda e: start_year_cb.focus_set())
        # wire Enter on day combobox to move focus or submit
        start_day_cb.bind('<Return>', lambda e: end_year_cb.focus_set())
        end_day_cb.bind('<Return>', submit)

        btn_frame = ttk.Frame(dlg)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text='OK', bootstyle='success', command=submit).pack(side=LEFT, padx=6)

        def on_cancel():
            try:
                cleanup()
            except Exception:
                pass
            try:
                dlg.destroy()
            except Exception:
                pass

        ttk.Button(btn_frame, text='Cancel', bootstyle='secondary', command=on_cancel).pack(side=LEFT, padx=6)

        name_entry.focus_set()
        # ensure widgets render properly before waiting
        try:
            dlg.update_idletasks()
        except Exception:
            pass
        self.wait_window(dlg)

        if not result['ok']:
            return None
        return (result['name'], result['location'], result['start'], result['end'])


    # edit_event handled above with a single unified popup (open_event_form_dialog)

    def delete_event(self):
        header_frame = ttk.Frame(self.collateral_tab)
        header_frame.pack(fill=X, padx=20, pady=10)
        # show which event is currently selected (updated when an event is chosen)
        self.collateral_event_label = ttk.Label(header_frame, text="Current Event Selected:", font=("Segoe UI", 14, "bold"))
        self.collateral_event_label.pack(side=LEFT)

        # Event selector combobox so user can pick an event directly from Items tab
        self.event_combo = ttk.Combobox(header_frame, values=[], state='readonly', width=50)
        self.event_combo.pack(side=LEFT, padx=10)
        self.event_combo.bind('<<ComboboxSelected>>', self.on_event_combo_select)
        # populate immediately so it's usable without visiting Events tab
        try:
            evs = get_events()
            names = [e[1] for e in evs]
            self.event_combo['values'] = names
            if names:
                # set default selection to first if nothing selected
                if not self.event_combo.get():
                    try:
                        self.event_combo.set(names[0])
                        self.selected_event_id = evs[0][0]
                        self.selected_event_name = evs[0][1]
                    except Exception:
                        pass
        except Exception:
            pass

        # Compact button area: show primary buttons and an Actions menu for the rest
        btn_container = ttk.Frame(header_frame)
        btn_container.pack(side=RIGHT, anchor=E)

        # Primary visible buttons
        # compact icon buttons for items tab
        self.btn_add = ttk.Button(btn_container, text="➕", bootstyle="success", command=lambda: self.add_item())
        self.btn_refresh = ttk.Button(btn_container, text="↻", bootstyle="info", command=lambda: self.load_items())
        self.btn_add.pack(side=LEFT, padx=(0,6))
        self.btn_refresh.pack(side=LEFT, padx=(0,6))

        # Actions menu for the rest of the item actions
        def open_actions_menu(event=None):
            try:
                menu = tk.Menu(self, tearoff=0)
                menu.add_command(label='Edit Item', command=lambda: self.edit_item())
                menu.add_command(label='+ Qty', command=lambda: self.increase_qty())
                menu.add_command(label='- Qty', command=lambda: self.decrease_qty())
                menu.add_separator()
                menu.add_command(label='Delete', command=lambda: self.delete_item())
                x = actions_btn.winfo_rootx()
                y = actions_btn.winfo_rooty() + actions_btn.winfo_height()
                menu.tk_popup(x, y)
            except Exception:
                pass

        actions_btn = ttk.Button(btn_container, text='Actions ▾', bootstyle='secondary', command=open_actions_menu)
        actions_btn.pack(side=LEFT)

        # add columns for last event used and last modified timestamp
        columns = ("ID", "Item Name", "Quantity", "Last Event Used", "Last Modified")
        display_cols = [c for c in columns if c != 'ID']
        # ensure ID is present in values but not shown in header layout
        self.item_tree = ttk.Treeview(self.collateral_tab, columns=columns, displaycolumns=display_cols, show="headings", height=12)
        for col in columns:
            # align heading anchor with the cell anchor
            if col == "ID":
                self.item_tree.heading(col, text=col, anchor=CENTER)
                # hide the ID column from view but keep it in row values
                self.item_tree.column(col, width=0, minwidth=0, anchor=CENTER, stretch=False)
            elif col == "Item Name":
                self.item_tree.heading(col, text=col, anchor=W)
                self.item_tree.column(col, width=340, minwidth=200, anchor=W, stretch=True)
            elif col == "Quantity":
                self.item_tree.heading(col, text=col, anchor=CENTER)
                self.item_tree.column(col, width=90, minwidth=60, anchor=CENTER, stretch=False)
            elif col == "Last Event Used":
                self.item_tree.heading(col, text=col, anchor=W)
                self.item_tree.column(col, width=180, minwidth=100, anchor=W, stretch=True)
            else:
                self.item_tree.heading(col, text=col, anchor=CENTER)
                self.item_tree.column(col, width=130, minwidth=80, anchor=CENTER, stretch=False)
        self.item_tree.pack(fill=BOTH, expand=True, padx=20, pady=10)
        # alternating row colors for readability (items)
        self.item_tree.tag_configure('odd', background='#ffffff')
        self.item_tree.tag_configure('even', background='#f8f9fc')

        # Right-side transaction history
        right = ttk.Frame(self.collateral_tab)
        right.pack(side=RIGHT, fill=Y, padx=10, pady=10)
        ttk.Label(right, text="Transactions", font=("Segoe UI", 12, "bold")).pack()
        tx_columns = ("ID", "Delta", "When", "Event")
        tx_display = [c for c in tx_columns if c != 'ID']
        self.tx_tree = ttk.Treeview(right, columns=tx_columns, displaycolumns=tx_display, show="headings", height=12)
        for c,w in [("ID",60),("Delta",60),("When",140),("Event",200)]:
            # align heading and column anchors
            if c == 'ID':
                self.tx_tree.heading(c, text=c, anchor=CENTER)
                self.tx_tree.column(c, width=w, minwidth=40, anchor=CENTER, stretch=False)
            elif c == 'Delta':
                self.tx_tree.heading(c, text=c, anchor=CENTER)
                self.tx_tree.column(c, width=w, minwidth=50, anchor=CENTER, stretch=False)
            elif c == 'When':
                self.tx_tree.heading(c, text=c, anchor=CENTER)
                self.tx_tree.column(c, width=w, minwidth=100, anchor=CENTER, stretch=False)
            else:
                self.tx_tree.heading(c, text=c, anchor=W)
                self.tx_tree.column(c, width=w, minwidth=120, anchor=W, stretch=True)
        self.tx_tree.pack(fill=Y, expand=True)
        # alternating row colors for tx tree
        self.tx_tree.tag_configure('odd', background='#ffffff')
        self.tx_tree.tag_configure('even', background='#f8f9fc')

        # start with item buttons disabled until selection
        self.set_item_buttons_state(False)
        self.item_tree.bind("<<TreeviewSelect>>", self.on_item_select)

        self.load_items()

    def load_items(self, selected_id=None):
        """Fetch and display collateral items from the database."""
        for row in self.item_tree.get_children():
            self.item_tree.delete(row)

        # Use summary API which lists items with last used event/time
        try:
            rows = get_item_summary()
        except Exception:
            # fallback: query collaterals directly
            conn = get_connection()
            rows = conn.cursor().execute("SELECT id, item_name, quantity, last_modified FROM collaterals ORDER BY id DESC").fetchall()
            conn.close()

        for idx, r in enumerate(rows):
            # r is (id, name, qty, last_event, last_time)
            # translate last_event id to name if possible
            last_event = r[3]
            if last_event is not None:
                try:
                    last_event_name = getattr(self, 'event_id_to_name', {}).get(last_event, str(last_event))
                except Exception:
                    last_event_name = str(last_event)
            else:
                last_event_name = "-"
            tag = 'odd' if (idx % 2) == 0 else 'even'
            self.item_tree.insert("", END, values=(r[0], r[1], r[2], last_event_name or "-", r[4] or "-"), tags=(tag,))
        # If caller asked to keep an item selected, find it and re-select/focus it
        if selected_id is not None:
            for iid in self.item_tree.get_children():
                try:
                    vals = self.item_tree.item(iid)["values"]
                except Exception:
                    vals = []
                if vals and vals[0] == selected_id:
                    self.item_tree.selection_set(iid)
                    self.item_tree.focus(iid)
                    self.item_tree.see(iid)
                    break

    def add_item(self):
        """Add a new collateral item using a modal dialog that focuses correctly."""
        # Build a small modal dialog to capture name and qty so Enter works cleanly
        dlg = ttk.Toplevel(self)
        dlg.title("Add New Item")
        dlg.transient(self)
        dlg.grab_set()
        ttk.Label(dlg, text="Item Name:").grid(row=0, column=0, padx=8, pady=8)
        name_var = ttk.StringVar()
        name_entry = ttk.Entry(dlg, textvariable=name_var)
        name_entry.grid(row=0, column=1, padx=8, pady=8)
        ttk.Label(dlg, text="Quantity:").grid(row=1, column=0, padx=8, pady=8)
        qty_var = ttk.IntVar(value=1)
        qty_entry = ttk.Entry(dlg, textvariable=qty_var)
        qty_entry.grid(row=1, column=1, padx=8, pady=8)

        result = {'name': None, 'qty': None}

        def submit_add(_ev=None):
            n = name_var.get().strip()
            try:
                q = int(qty_var.get())
            except Exception:
                q = None
            if not n or q is None:
                messagebox.showwarning("Invalid", "Please provide both name and a numeric quantity.", parent=dlg)
                return
            result['name'] = n
            result['qty'] = q
            dlg.grab_release()
            dlg.destroy()

        # Enter in name moves to qty; Enter in qty submits
        name_entry.bind('<Return>', lambda e: qty_entry.focus_set())
        qty_entry.bind('<Return>', submit_add)

        btn = ttk.Button(dlg, text="Add", bootstyle="success", command=submit_add)
        btn.grid(row=2, column=0, columnspan=2, pady=8)
        # focus name entry initially
        name_entry.focus_set()
        self.wait_window(dlg)

        if not result['name']:
            return
        # Ensure an event is selected so the new item is linked. If none, prompt immediately.
        if not self.selected_event_id:
            # give focus back to main window then open chooser so it's visible and focused
            try:
                self.lift()
                self.focus_force()
            except Exception:
                pass
            chosen = self.choose_event_dialog()
            if not chosen:
                messagebox.showwarning("No event selected", "Please select an event first (choose on Events tab or the dropdown).")
                return
            # store the chosen event id and update combobox display when possible
            try:
                self.selected_event_id = int(chosen)
                evs = get_events()
                if hasattr(self, 'event_combo') and evs:
                    for e in evs:
                        if e[0] == self.selected_event_id:
                            try:
                                self.event_combo.set(f"{e[0]}: {e[1]}")
                            except Exception:
                                pass
                            break
            except Exception:
                pass

        try:
            last_id = create_collateral(result['name'], result['qty'], self.selected_event_id)
            messagebox.showinfo("Success", "Item added successfully!")
            # reload and select the newly created item
            try:
                # create_collateral returns lastrowid from app.py
                self.load_items(selected_id=last_id)
            except Exception:
                self.load_items()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def reduce_item(self):
        """Spend/reduce an item and record which event it was spent at."""
        selected = self.item_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select an item to reduce.")
            return
        vals = self.item_tree.item(selected[0])["values"]
        item_id = vals[0]
        qty = vals[2] or 0
        reduce_by = simpledialog.askinteger("Reduce Quantity", "Quantity to reduce:", minvalue=1, maxvalue=qty, parent=self)
        if not reduce_by:
            return
        # Ask which event it was spent at using a dropdown
        # prefer currently selected event in combobox/tab
        event_id = self.get_current_event_selection() or self.choose_event_dialog()
        try:
            # use spend_collateral which records transactions
            new_qty = spend_collateral(item_id, -abs(reduce_by), event_id)
            messagebox.showinfo("Success", f"Reduced by {reduce_by}. New qty: {new_qty}")
            self.load_items(selected_id=item_id)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def choose_event_dialog(self):
        """Show a simple dialog listing events, return selected event id or None."""
        try:
            events = get_events()
        except Exception:
            events = []
        if not events:
            return None
        # build a mapping and a list for display
        choices = [f"{e[0]}: {e[1]}" for e in events]
        sel = simpledialog.askstring("Choose Event", "Event:\n" + "\n".join(choices) + "\n\nType the ID to select (or Cancel):", parent=self)
        if not sel:
            return None
        try:
            return int(sel)
        except Exception:
            return None

    def on_event_combo_select(self, _ev=None):
        """User selected an event from the combobox in Items tab."""
        val = self.event_combo.get()
        if not val:
            return
        # combobox now shows only the name; map back to id
        try:
            eid = getattr(self, 'event_name_to_id', {}).get(val)
        except Exception:
            eid = None
        if eid:
            self.selected_event_id = eid
            # store selected event name but keep header label static
            try:
                self.selected_event_name = val
            except Exception:
                self.selected_event_name = None

    def get_current_event_selection(self):
        """Return currently selected event id from combobox or event tab selection."""
        # prefer combobox first
        try:
            val = self.event_combo.get()
            if val:
                return int(val.split(":", 1)[0])
        except Exception:
            pass
        return self.selected_event_id

    def edit_quantity(self):
        """Open a dialog to edit quantity (positive or negative) and record under the selected event."""
        selected = self.item_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select an item to edit quantity.")
            return
            dlg = ttk.Toplevel(self)
            dlg.title("Add New Event")
            dlg.transient(self)
            dlg.grab_set()
            try:
                dlg.columnconfigure(1, weight=1)
            except Exception:
                pass

            # initial values if editing
            init_name = init_loc = init_start = init_end = None
            if initial and isinstance(initial, (list, tuple)):
                try:
                    init_name, init_loc, init_start, init_end = initial
                except Exception:
                    pass

            ttk.Label(dlg, text="Event Name:").grid(row=0, column=0, padx=8, pady=6, sticky=W)
            name_var = ttk.StringVar(value=init_name or '')
            name_entry = ttk.Entry(dlg, textvariable=name_var, width=40)
            name_entry.grid(row=0, column=1, padx=8, pady=6)

            ttk.Label(dlg, text="Location:").grid(row=1, column=0, padx=8, pady=6, sticky=W)
            location_var = ttk.StringVar(value=init_loc or '')
            location_entry = ttk.Entry(dlg, textvariable=location_var, width=40)
            location_entry.grid(row=1, column=1, padx=8, pady=6)

            # Date helpers
            now = datetime.date.today()
            cur_year = now.year
            year_range = list(range(cur_year - 5, cur_year + 6))

            def mk_month_options():
                return [(i, calendar.month_name[i]) for i in range(1, 13)]

            def mk_year_values():
                return [str(y) for y in year_range]

            def days_for(year, month):
                try:
                    year = int(year)
                    month = int(month)
                except Exception:
                    return []
                _, nd = calendar.monthrange(year, month)
                return [f"{d:02d}" for d in range(1, nd + 1)]

            # START date dropdowns - default to today when not provided
            ttk.Label(dlg, text="Start Date:").grid(row=2, column=0, padx=8, pady=6, sticky=W)
            if init_start:
                try:
                    sy = init_start.split('-')
                    start_year_default = sy[0]
                    start_month_default = sy[1]
                    start_day_default = sy[2]
                except Exception:
                    start_year_default = str(now.year)
                    start_month_default = f"{now.month:02d}"
                    start_day_default = f"{now.day:02d}"
            else:
                start_year_default = str(now.year)
                start_month_default = f"{now.month:02d}"
                start_day_default = f"{now.day:02d}"

            start_year_var = ttk.StringVar(value=start_year_default)
            # format month defaults like '10 - October'
            if start_month_default and ' - ' not in start_month_default:
                try:
                    mnum = int(start_month_default)
                    start_month_default = f"{mnum:02d} - {calendar.month_name[mnum]}"
                except Exception:
                    pass
            start_month_var = ttk.StringVar(value=start_month_default)
            start_day_var = ttk.StringVar(value=start_day_default)

            # place the start date controls inside their own frame so they stay grouped
            start_frame = ttk.Frame(dlg)
            start_frame.grid(row=2, column=1, sticky=W+E, padx=0)
            start_year_cb = ttk.Combobox(start_frame, values=mk_year_values(), textvariable=start_year_var, width=8, state='readonly')
            start_month_cb = ttk.Combobox(start_frame, values=[f"{i:02d} - {m}" for i, m in mk_month_options()], textvariable=start_month_var, width=14, state='readonly')
            start_day_cb = ttk.Combobox(start_frame, values=days_for(start_year_var.get(), start_month_var.get().split()[0]), textvariable=start_day_var, width=6, state='readonly')
            start_year_cb.grid(row=0, column=0, sticky=W, padx=(0,6))
            start_month_cb.grid(row=0, column=1, sticky=W, padx=(0,6))
            start_day_cb.grid(row=0, column=2, sticky=W)

            # END date dropdowns - default to today when not provided
            ttk.Label(dlg, text="End Date:").grid(row=3, column=0, padx=8, pady=6, sticky=W)
            if init_end:
                try:
                    ey = init_end.split('-')
                    end_year_default = ey[0]
                    end_month_default = ey[1]
                    end_day_default = ey[2]
                except Exception:
                    end_year_default = str(now.year)
                    end_month_default = f"{now.month:02d}"
                    end_day_default = f"{now.day:02d}"
            else:
                end_year_default = str(now.year)
                end_month_default = f"{now.month:02d}"
                end_day_default = f"{now.day:02d}"

            if end_month_default and ' - ' not in end_month_default:
                try:
                    mnum = int(end_month_default)
                    end_month_default = f"{mnum:02d} - {calendar.month_name[mnum]}"
                except Exception:
                    pass
            end_year_var = ttk.StringVar(value=end_year_default)
            end_month_var = ttk.StringVar(value=end_month_default)
            end_day_var = ttk.StringVar(value=end_day_default)

            end_frame = ttk.Frame(dlg)
            end_frame.grid(row=3, column=1, sticky=W+E, padx=0)
            end_year_cb = ttk.Combobox(end_frame, values=mk_year_values(), textvariable=end_year_var, width=8, state='readonly')
            end_month_cb = ttk.Combobox(end_frame, values=[f"{i:02d} - {m}" for i, m in mk_month_options()], textvariable=end_month_var, width=14, state='readonly')
            end_day_cb = ttk.Combobox(end_frame, values=days_for(end_year_var.get(), end_month_var.get().split()[0]), textvariable=end_day_var, width=6, state='readonly')
            end_year_cb.grid(row=0, column=0, sticky=W, padx=(0,6))
            end_month_cb.grid(row=0, column=1, sticky=W, padx=(0,6))
            end_day_cb.grid(row=0, column=2, sticky=W)

            def update_start_days(_ev=None):
                mon = start_month_var.get().split()[0] if start_month_var.get() else ''
                vals = days_for(start_year_var.get(), mon)
                start_day_cb['values'] = vals
                if start_day_var.get() not in vals:
                    start_day_var.set(vals[-1] if vals else '')

            def update_end_days(_ev=None):
                mon = end_month_var.get().split()[0] if end_month_var.get() else ''
                vals = days_for(end_year_var.get(), mon)
                end_day_cb['values'] = vals
                if end_day_var.get() not in vals:
                    end_day_var.set(vals[-1] if vals else '')

            start_year_cb.bind('<<ComboboxSelected>>', update_start_days)
            start_month_cb.bind('<<ComboboxSelected>>', update_start_days)
            end_year_cb.bind('<<ComboboxSelected>>', update_end_days)
            end_month_cb.bind('<<ComboboxSelected>>', update_end_days)

            result = {'ok': False, 'name': None, 'location': None, 'start': None, 'end': None}

            def cleanup():
                return

            def build_date_str(yvar, mvar, dvar):
                y = (yvar.get() or '').strip()
                m = (mvar.get() or '').strip()
                d = (dvar.get() or '').strip()
                if not y or not m or not d:
                    return None
                if ' ' in m:
                    m = m.split()[0]
                try:
                    yy = int(y)
                    mm = int(m)
                    dd = int(d)
                    return f"{yy:04d}-{mm:02d}-{dd:02d}"
                except Exception:
                    return None

            def submit(_ev=None):
                n = name_var.get().strip()
                if not n:
                    messagebox.showwarning('Invalid', 'Please enter an event name.', parent=dlg)
                    return
                start_s = build_date_str(start_year_var, start_month_var, start_day_var)
                end_s = build_date_str(end_year_var, end_month_var, end_day_var)
                if start_s and end_s:
                    try:
                        ds = datetime.datetime.strptime(start_s, '%Y-%m-%d')
                        de = datetime.datetime.strptime(end_s, '%Y-%m-%d')
                        if de < ds:
                            messagebox.showwarning('Invalid', 'End date must be the same or after Start date.', parent=dlg)
                            return
                    except Exception:
                        messagebox.showwarning('Invalid', 'Please provide valid dates (YYYY-MM-DD).', parent=dlg)
                        return

                result['name'] = n
                result['location'] = location_var.get().strip() or None
                result['start'] = start_s
                result['end'] = end_s
                result['ok'] = True
                dlg.grab_release()
                dlg.destroy()

            name_entry.bind('<Return>', lambda e: location_entry.focus_set())
            location_entry.bind('<Return>', lambda e: start_year_cb.focus_set())
            start_day_cb.bind('<Return>', lambda e: end_year_cb.focus_set())
            end_day_cb.bind('<Return>', submit)

            btn_frame = ttk.Frame(dlg)
            btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
            ttk.Button(btn_frame, text='OK', bootstyle='success', command=submit).pack(side=LEFT, padx=6)

            def on_cancel():
                try:
                    cleanup()
                except Exception:
                    pass
                try:
                    dlg.destroy()
                except Exception:
                    pass

            ttk.Button(btn_frame, text='Cancel', bootstyle='secondary', command=on_cancel).pack(side=LEFT, padx=6)

            name_entry.focus_set()
            try:
                dlg.update_idletasks()
            except Exception:
                pass
            self.wait_window(dlg)

            if not result['ok']:
                return None
            return (result['name'], result['location'], result['start'], result['end'])
