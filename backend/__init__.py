"""Backend package for TDD Inventory System.

This module re-exports the public helper functions from the small
backend submodules so callers can write `from backend import <func>`.

Design notes:
- keep imports local and simple to avoid circular imports
- only re-export symbols that actually exist in the underlying modules
"""

# Database helpers (connection and initialization)
from .database import get_connection, create_tables, init_db

# Event-related operations
from .events import (
    create_event,
    update_event,
    delete_event,
    list_events,
    search_events,
)

# Collateral (item) operations
from .collaterals import (
    create_collateral,
    update_collateral,
    delete_collateral,
    spend_collateral,
    get_item_summary,
    get_transactions,
)

# Simple logging helpers (separate logs DB)
from .logs import log_action, view_logs

# Summary / reports helpers
from .summary import show_summary


__all__ = [
    # database
    'get_connection', 'create_tables', 'init_db',
    # events
    'create_event', 'update_event', 'delete_event', 'list_events', 'search_events',
    # collaterals
    'create_collateral', 'update_collateral', 'delete_collateral', 'spend_collateral',
    'get_item_summary', 'get_transactions',
    # logs
    'log_action', 'view_logs',
    # reports
    'show_summary',
]

