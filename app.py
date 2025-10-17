"""Compatibility shim for older imports.

This module re-exports the backend package functions so existing imports like
`from app import create_event` continue to work while the implementation
is moved into `backend/`.
"""
from backend.database import get_connection, init_db  # noqa: F401
from backend.events import create_event, update_event, delete_event, list_events, search_events  # noqa: F401
from backend.collaterals import (
    create_collateral,
    update_collateral,
    delete_collateral,
    spend_collateral,
    get_item_summary,
    get_transactions,
)  # noqa: F401
from backend.logs import log_action, view_logs  # noqa: F401
from backend.summary import show_summary  # noqa: F401

__all__ = [
    'get_connection', 'init_db',
    'create_event', 'update_event', 'delete_event', 'list_events', 'search_events',
    'create_collateral', 'update_collateral', 'delete_collateral', 'spend_collateral',
    'get_item_summary', 'get_transactions',
    'log_action', 'view_logs', 'show_summary',
]

