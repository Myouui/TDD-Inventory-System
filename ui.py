"""Main GUI for the TDD Inventory System.

This module builds a ttkbootstrap-themed Tkinter app with the following tabs:
- Events: list/add/edit/delete events
- Collaterals: view items, add/edit/delete, spend/restock
- Reports: summary statistics
- Logs: action logs

Run with:
    python ui.py

The UI uses the `backend` package for all DB operations.
"""
from typing import Optional
import datetime
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import messagebox, simpledialog

# backend imports (new modular layout)
from backend import (
    init_db,
    create_event,
    update_event,
    delete_event,
    list_events,
    create_collateral,
    update_collateral,
    delete_collateral,
    spend_collateral,
    get_item_summary,
    get_transactions,
    log_action,
    view_logs,
    show_summary,
)


# ----------------------------
# Helper utilities
# ----------------------------

def safe_call(func, *args, success_msg: Optional[str] = None, error_title: str = 'Error'):
    """Call func and show messagebox on error; return func result or None."""
    try:
        res = func(*args)
        if success_msg:
            messagebox.showinfo('Success', success_msg)
        return res
    except Exception as e:
        messagebox.showerror(error_title, str(e))
        return None


# ----------------------------
# Main Application
# ----------------------------
class InventoryApp(ttk.Window):
    """Main application window using ttkbootstrap.Window (theme 'cosmo')."""

    def __init__(self):
        super().__init__(themename='cosmo')
        self.title('TDD Inventory System')
        self.geometry('1000x650')

        # initialize DB (creates tables if missing)
        try:
            init_db()
        except Exception:
            # init_db uses backend.database.create_tables which already handles dirs.
            pass

        # mapping event id <-> name for quick lookup
        self.event_id_to_name = {}
        self.event_name_to_id = {}
        self.selected_event_id: Optional[int] = None

        # Top label
        ttk.Label(self, text='TDD Collateral Inventory System', font=('Segoe UI', 18, 'bold')).pack(pady=10)

        # Notebook with tabs
        self.tabs = ttk.Notebook(self)
        self.events_tab = ttk.Frame(self.tabs)
        self.collateral_tab = ttk.Frame(self.tabs)
        self.reports_tab = ttk.Frame(self.tabs)
        self.logs_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.events_tab, text='Events')
        self.tabs.add(self.collateral_tab, text='Collaterals')
        self.tabs.add(self.reports_tab, text='Reports')
        self.tabs.add(self.logs_tab, text='Logs')
        self.tabs.pack(fill=BOTH, expand=True, padx=10, pady=8)

        # Build each tab
        self.build_events_tab()
        self.build_collateral_tab()
        self.build_reports_tab()
        self.build_logs_tab()

        # status bar
        self.status_var = ttk.StringVar(value='Ready')
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=X, side=BOTTOM)
        ttk.Label(status_frame, textvariable=self.status_var, font=('Segoe UI', 9)).pack(side=LEFT, padx=6)
        self.update_status('Ready')

        # initial load
        self.load_events()
        self.load_items()
        self.update_reports()
        self.load_logs()

    # ----------------------------
    # Status helpers
    # ----------------------------
    def update_status(self, message: Optional[str] = None):
        """Update bottom status bar with timestamp."""
        ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        msg = f'Last updated: {ts}' if message is None else f'{message} — {ts}'
        self.status_var.set(msg)

    # ----------------------------
    # Events tab
    # ----------------------------
    def build_events_tab(self):
        header = ttk.Frame(self.events_tab)
        header.pack(fill=X, padx=12, pady=8)
        ttk.Label(header, text='Events', font=('Segoe UI', 14, 'bold')).pack(side=LEFT)

        btns = ttk.Frame(header)
        btns.pack(side=RIGHT)
        ttk.Button(btns, text='➕ Add', bootstyle='success', command=self.add_event).pack(side=LEFT, padx=4)
        ttk.Button(btns, text='✎ Edit', bootstyle='warning', command=self.edit_event).pack(side=LEFT, padx=4)
        ttk.Button(btns, text='🗑 Delete', bootstyle='danger', command=self.delete_event).pack(side=LEFT, padx=4)
        ttk.Button(btns, text='↻ Refresh', bootstyle='info', command=self.load_events).pack(side=LEFT, padx=4)

        cols = ('ID', 'Event Name', 'Location', 'Start Date', 'End Date', 'Last Modified')
        display_cols = [c for c in cols if c != 'ID']
        self.event_tree = ttk.Treeview(self.events_tab, columns=cols, displaycolumns=display_cols, show='headings', height=14)
        for c in cols:
            anchor = CENTER if c != 'Event Name' and c != 'Location' else W
            width = 300 if c == 'Event Name' else 120
            if c == 'ID':
                self.event_tree.heading(c, text=c)
                self.event_tree.column(c, width=0, stretch=False)
            else:
                self.event_tree.heading(c, text=c, anchor=anchor)
                self.event_tree.column(c, width=width, anchor=anchor)
        self.event_tree.pack(fill=BOTH, expand=True, padx=12, pady=6)
        self.event_tree.bind('<<TreeviewSelect>>', self.on_event_selected)

    def load_events(self):
        """Load events into the events tree and refresh mappings."""
        for r in self.event_tree.get_children():
            self.event_tree.delete(r)
        rows = list_events()
        self.event_id_to_name = {r[0]: r[1] for r in rows}
        self.event_name_to_id = {r[1]: r[0] for r in rows}
        for i, r in enumerate(rows):
            tag = 'odd' if (i % 2) == 0 else 'even'
            self.event_tree.insert('', END, values=(r[0], r[1], '-', '-', '-', '-'), tags=(tag,))
        self.update_status('Events refreshed')

    def on_event_selected(self, _ev=None):
        sel = self.event_tree.selection()
        if not sel:
            self.selected_event_id = None
            return
        vals = self.event_tree.item(sel[0])['values']
        try:
            self.selected_event_id = int(vals[0])
        except Exception:
            self.selected_event_id = None
        # also switch to Collaterals tab and filter
        try:
            self.tabs.select(self.collateral_tab)
            self.load_items()
        except Exception:
            pass

    def add_event(self):
        data = self.open_event_dialog()
        if not data:
            return
        name, location, start, end = data
        eid = safe_call(create_event, name, start, end, location, success_msg='Event created')
        if eid:
            log_action('ui', 'create_event', f'{name}')
            self.load_events()
            self.update_reports()

    def edit_event(self):
        sel = self.event_tree.selection()
        if not sel:
            messagebox.showwarning('No selection', 'Please select an event to edit.')
            return
        vals = self.event_tree.item(sel[0])['values']
        event_id = vals[0]
        # prompt with existing name only for simplicity
        name = simpledialog.askstring('Edit Event', 'Event Name:', initialvalue=vals[1], parent=self)
        if not name:
            return
        safe_call(update_event, event_id, name, None, None, None, success_msg='Event updated')
        log_action('ui', 'update_event', f'{event_id}:{name}')
        self.load_events()

    def delete_event(self):
        sel = self.event_tree.selection()
        if not sel:
            messagebox.showwarning('No selection', 'Please select an event to delete.')
            return
        vals = self.event_tree.item(sel[0])['values']
        if not messagebox.askyesno('Confirm', f'Delete event {vals[1]}?'):
            return
        safe_call(delete_event, vals[0], success_msg='Event deleted')
        log_action('ui', 'delete_event', f'{vals[0]}:{vals[1]}')
        self.load_events()
        self.load_items()
        self.update_reports()

    def open_event_dialog(self):
        """Modal dialog to add an event (name, optional location, start/end simple inputs)."""
        dlg = ttk.Toplevel(self)
        dlg.title('Add Event')
        dlg.transient(self)
        dlg.grab_set()
        ttk.Label(dlg, text='Event Name:').grid(row=0, column=0, padx=8, pady=6)
        name_var = ttk.StringVar()
        ttk.Entry(dlg, textvariable=name_var, width=40).grid(row=0, column=1, padx=8, pady=6)
        ttk.Label(dlg, text='Location:').grid(row=1, column=0, padx=8, pady=6)
        loc_var = ttk.StringVar()
        ttk.Entry(dlg, textvariable=loc_var, width=40).grid(row=1, column=1, padx=8, pady=6)

        res = {'ok': False}

        def submit():
            n = name_var.get().strip()
            if not n:
                messagebox.showwarning('Invalid', 'Event name required.', parent=dlg)
                return
            res['name'] = n
            res['loc'] = loc_var.get().strip() or None
            res['ok'] = True
            dlg.destroy()

        ttk.Button(dlg, text='Save', bootstyle='success', command=submit).grid(row=2, column=0, columnspan=2, pady=8)
        name_var.set('')
        self.wait_window(dlg)
        if not res.get('ok'):
            return None
        return (res['name'], res['loc'], None, None)

    # ----------------------------
    # Collaterals tab
    # ----------------------------
    def build_collateral_tab(self):
        header = ttk.Frame(self.collateral_tab)
        header.pack(fill=X, padx=12, pady=8)
        ttk.Label(header, text='Collaterals', font=('Segoe UI', 14, 'bold')).pack(side=LEFT)

        # event filter
        self.event_filter_var = ttk.StringVar()
        self.event_filter = ttk.Combobox(header, textvariable=self.event_filter_var, state='readonly', width=40)
        self.event_filter.pack(side=LEFT, padx=8)
        self.event_filter.bind('<<ComboboxSelected>>', lambda e: self.load_items())

        btns = ttk.Frame(header)
        btns.pack(side=RIGHT)
        ttk.Button(btns, text='➕ Add', bootstyle='success', command=self.add_item).pack(side=LEFT, padx=4)
        ttk.Button(btns, text='✎ Edit', bootstyle='warning', command=self.edit_item).pack(side=LEFT, padx=4)
        ttk.Button(btns, text='🗑 Delete', bootstyle='danger', command=self.delete_item).pack(side=LEFT, padx=4)
        ttk.Button(btns, text='+ Qty', bootstyle='info', command=self.increase_qty).pack(side=LEFT, padx=4)
        ttk.Button(btns, text='- Qty', bootstyle='info', command=self.decrease_qty).pack(side=LEFT, padx=4)
        ttk.Button(btns, text='↻ Refresh', bootstyle='secondary', command=self.load_items).pack(side=LEFT, padx=4)

        cols = ('ID', 'Item Name', 'Quantity', 'Last Event Used', 'Last Modified')
        display_cols = [c for c in cols if c != 'ID']
        self.item_tree = ttk.Treeview(self.collateral_tab, columns=cols, displaycolumns=display_cols, show='headings', height=14)
        for c in cols:
            anchor = CENTER if c != 'Item Name' else W
            width = 340 if c == 'Item Name' else 100
            if c == 'ID':
                self.item_tree.heading(c, text=c)
                self.item_tree.column(c, width=0, stretch=False)
            else:
                self.item_tree.heading(c, text=c, anchor=anchor)
                self.item_tree.column(c, width=width, anchor=anchor)
        self.item_tree.pack(fill=BOTH, expand=True, padx=12, pady=6)
        self.item_tree.bind('<<TreeviewSelect>>', self.on_item_select)

    def load_items(self):
        """Load collaterals, optionally filtered by selected event in event_filter."""
        for r in self.item_tree.get_children():
            self.item_tree.delete(r)
        # populate event filter
        events = list_events()
        names = [e[1] for e in events]
        self.event_filter['values'] = names
        # if an event is selected in Events tab, select it here
        if self.selected_event_id:
            name = self.event_id_to_name.get(self.selected_event_id)
            if name:
                try:
                    self.event_filter.set(name)
                except Exception:
                    pass

        rows = get_item_summary()
        # if filter selected, map to id
        f = self.event_filter.get()
        fid = self.event_name_to_id.get(f) if f else None
        for i, r in enumerate(rows):
            # r: id, name, qty, last_event, last_time
            if fid and r[3] and int(r[3]) != int(fid):
                continue
            last_event_name = self.event_id_to_name.get(r[3], '-') if r[3] else '-'
            tag = 'odd' if (i % 2) == 0 else 'even'
            self.item_tree.insert('', END, values=(r[0], r[1], r[2], last_event_name, r[4] or '-'), tags=(tag,))
        self.update_status('Collaterals refreshed')

    def on_item_select(self, _ev=None):
        sel = self.item_tree.selection()
        if not sel:
            return
        vals = self.item_tree.item(sel[0])['values']
        # load transactions to logs area for quick view
        try:
            txs = get_transactions(vals[0])
            # update logs view with transactions (not persisted logs)
            self._populate_logs(txs_only=txs)
        except Exception:
            pass

    def add_item(self):
        dlg = ttk.Toplevel(self)
        dlg.title('Add Item')
        dlg.transient(self)
        dlg.grab_set()
        ttk.Label(dlg, text='Item Name:').grid(row=0, column=0, padx=8, pady=6)
        name_var = ttk.StringVar()
        ttk.Entry(dlg, textvariable=name_var, width=40).grid(row=0, column=1, padx=8, pady=6)
        ttk.Label(dlg, text='Quantity:').grid(row=1, column=0, padx=8, pady=6)
        qty_var = ttk.IntVar(value=1)
        ttk.Entry(dlg, textvariable=qty_var, width=20).grid(row=1, column=1, padx=8, pady=6)

        def submit():
            n = name_var.get().strip()
            try:
                q = int(qty_var.get())
            except Exception:
                messagebox.showwarning('Invalid', 'Quantity must be an integer.', parent=dlg)
                return
            if not n:
                messagebox.showwarning('Invalid', 'Name required.', parent=dlg)
                return
            eid = create_collateral(n, q, self.selected_event_id)
            log_action('ui', 'create_collateral', f'{n}:{q}')
            dlg.destroy()
            self.load_items()
            self.update_reports()

        ttk.Button(dlg, text='Add', bootstyle='success', command=submit).grid(row=2, column=0, columnspan=2, pady=8)
        name_var.set('')
        self.wait_window(dlg)

    def edit_item(self):
        sel = self.item_tree.selection()
        if not sel:
            messagebox.showwarning('No selection', 'Please select an item to edit.')
            return
        vals = self.item_tree.item(sel[0])['values']
        item_id = vals[0]
        dlg = ttk.Toplevel(self)
        dlg.title('Edit Item')
        dlg.transient(self)
        dlg.grab_set()
        ttk.Label(dlg, text='Item Name:').grid(row=0, column=0, padx=8, pady=6)
        name_var = ttk.StringVar(value=vals[1])
        ttk.Entry(dlg, textvariable=name_var, width=40).grid(row=0, column=1, padx=8, pady=6)
        ttk.Label(dlg, text='Quantity:').grid(row=1, column=0, padx=8, pady=6)
        qty_var = ttk.IntVar(value=vals[2])
        ttk.Entry(dlg, textvariable=qty_var, width=20).grid(row=1, column=1, padx=8, pady=6)

        def submit():
            n = name_var.get().strip()
            try:
                q = int(qty_var.get())
            except Exception:
                messagebox.showwarning('Invalid', 'Quantity must be an integer.', parent=dlg)
                return
            update_collateral(item_id, n, q, self.selected_event_id)
            log_action('ui', 'update_collateral', f'{item_id}:{n}:{q}')
            dlg.destroy()
            self.load_items()
            self.update_reports()

        ttk.Button(dlg, text='Save', bootstyle='success', command=submit).grid(row=2, column=0, columnspan=2, pady=8)
        self.wait_window(dlg)

    def delete_item(self):
        sel = self.item_tree.selection()
        if not sel:
            messagebox.showwarning('No selection', 'Please select an item to delete.')
            return
        vals = self.item_tree.item(sel[0])['values']
        if not messagebox.askyesno('Confirm', f'Delete item {vals[1]}?'):
            return
        delete_collateral(vals[0])
        log_action('ui', 'delete_collateral', f'{vals[0]}:{vals[1]}')
        self.load_items()
        self.update_reports()

    def increase_qty(self):
        sel = self.item_tree.selection()
        if not sel:
            messagebox.showwarning('No selection', 'Please select an item.')
            return
        vals = self.item_tree.item(sel[0])['values']
        amt = simpledialog.askinteger('Increase Qty', 'Amount to increase by:', minvalue=1, parent=self)
        if not amt:
            return
        newq = spend_collateral(vals[0], abs(amt), self.selected_event_id)
        log_action('ui', 'spend_collateral', f'{vals[0]}:+{amt}')
        messagebox.showinfo('Success', f'New qty: {newq}')
        self.load_items()
        self.update_reports()

    def decrease_qty(self):
        sel = self.item_tree.selection()
        if not sel:
            messagebox.showwarning('No selection', 'Please select an item.')
            return
        vals = self.item_tree.item(sel[0])['values']
        maxv = vals[2] if len(vals) > 2 else None
        amt = simpledialog.askinteger('Decrease Qty', 'Amount to decrease by:', minvalue=1, maxvalue=maxv, parent=self)
        if not amt:
            return
        newq = spend_collateral(vals[0], -abs(amt), self.selected_event_id)
        log_action('ui', 'spend_collateral', f'{vals[0]}:-{amt}')
        messagebox.showinfo('Success', f'New qty: {newq}')
        self.load_items()
        self.update_reports()

    # ----------------------------
    # Reports tab
    # ----------------------------
    def build_reports_tab(self):
        frame = ttk.Frame(self.reports_tab)
        frame.pack(fill=BOTH, expand=True, padx=12, pady=12)
        ttk.Label(frame, text='Summary', font=('Segoe UI', 14, 'bold')).pack(anchor=W)
        self.summary_text = ttk.Label(frame, text='', font=('Segoe UI', 12), anchor=W, justify=LEFT)
        self.summary_text.pack(fill=BOTH, expand=True, pady=8)

    def update_reports(self):
        s = show_summary()
        txt = f"Total Events: {s['total_events']}\nTotal Item Types: {s['total_items']}\nTotal Quantity: {s['total_quantity']}"
        self.summary_text.config(text=txt)

    # ----------------------------
    # Logs tab
    # ----------------------------
    def build_logs_tab(self):
        header = ttk.Frame(self.logs_tab)
        header.pack(fill=X, padx=12, pady=8)
        ttk.Button(header, text='Refresh', bootstyle='info', command=self.load_logs).pack(side=RIGHT)
        ttk.Label(header, text='Action Logs', font=('Segoe UI', 14, 'bold')).pack(side=LEFT)

        cols = ('ID', 'When', 'Actor', 'Action', 'Details')
        self.logs_tree = ttk.Treeview(self.logs_tab, columns=cols, show='headings', height=18)
        for c in cols:
            self.logs_tree.heading(c, text=c)
            self.logs_tree.column(c, width=120)
        self.logs_tree.pack(fill=BOTH, expand=True, padx=12, pady=6)

    def _populate_logs(self, txs_only=None):
        # txs_only: optional sequence of transaction rows (id, delta, timestamp, event_name)
        for r in self.logs_tree.get_children():
            self.logs_tree.delete(r)
        if txs_only:
            for i, t in enumerate(txs_only):
                self.logs_tree.insert('', END, values=(t[0], t[2], '-', f'delta={t[1]}', t[3] or '-'))
            return
        rows = view_logs(200)
        for r in rows:
            self.logs_tree.insert('', END, values=r)

    def load_logs(self):
        self._populate_logs()
        self.update_status('Logs refreshed')


# ----------------------------
# Entrypoint
# ----------------------------
if __name__ == '__main__':
    app = InventoryApp()
    app.mainloop()
