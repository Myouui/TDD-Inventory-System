"""Summary / reports helpers for the inventory system.

Provides simple aggregation functions used by the UI Reports tab.
"""
from typing import Dict, Any
from .database import get_connection


def show_summary() -> Dict[str, Any]:
    """Return a small summary dict with totals used in reports.

    Keys: total_events, total_items, total_quantity
    """
    conn = get_connection()
    cur = conn.cursor()
    total_events = cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    total_items = cur.execute("SELECT COUNT(*) FROM collaterals").fetchone()[0]
    total_quantity = cur.execute("SELECT SUM(quantity) FROM collaterals").fetchone()[0] or 0
    conn.close()
    return {
        'total_events': total_events,
        'total_items': total_items,
        'total_quantity': total_quantity,
    }
