"""
SQLite-based order management for PayJS payment integration.
Stores orders, payment status, and AI report results.
"""
import json
import hashlib
import sqlite3
import os
import threading
from datetime import datetime, timezone

DB_PATH = os.environ.get("ORDERS_DB_PATH") or os.path.expanduser("~/.hermes/bazi_orders.db")
_local = threading.local()


def _get_conn():
    """Get thread-local database connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _local.conn = sqlite3.connect(DB_PATH)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
    return _local.conn


def init_db():
    """Create tables if they don't exist. Call once on startup."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id        TEXT UNIQUE NOT NULL,
            payjs_order_id  TEXT,
            status          TEXT NOT NULL DEFAULT 'pending',
            total_fee       INTEGER NOT NULL,
            body            TEXT,
            birth_data      TEXT,
            report_json     TEXT,
            report_ready    INTEGER DEFAULT 0,
            notify_raw      TEXT,
            created_at      TEXT NOT NULL,
            paid_at         TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_order_id ON orders(order_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)
    """)
    conn.commit()


def _generate_order_id() -> str:
    """Generate a unique order ID: BAZI + timestamp + random 4 digits."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    rand = hashlib.md5(os.urandom(8)).hexdigest()[:4].upper()
    return f"FL{ts}{rand}"


def create_order(birth_data: dict, total_fee: int = 1990, body: str = "八字AI深度解读") -> dict:
    """
    Create a new order in the database.
    Returns the order record dict.
    """
    # Check if this birth data already has a paid report
    existing = get_paid_order_for_birth(birth_data)
    if existing:
        return dict(existing)

    conn = _get_conn()
    order_id = _generate_order_id()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """INSERT INTO orders (order_id, status, total_fee, body, birth_data, created_at)
           VALUES (?, 'pending', ?, ?, ?, ?)""",
        (order_id, total_fee, body, json.dumps(birth_data, ensure_ascii=False, sort_keys=True), now),
    )
    conn.commit()
    return get_order(order_id)


def get_order(order_id: str) -> dict | None:
    """Get order by our order_id."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM orders WHERE order_id=?", (order_id,)).fetchone()
    if row is None:
        return None
    return dict(row)


def get_order_by_payjs(payjs_order_id: str) -> dict | None:
    """Get order by PayJS order ID."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM orders WHERE payjs_order_id=?", (payjs_order_id,)
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def get_paid_order_for_birth(birth_data: dict) -> dict | None:
    """Check if the exact same birth data already has a paid order (report ready or generating)."""
    key = json.dumps(birth_data, ensure_ascii=False, sort_keys=True)
    conn = _get_conn()
    row = conn.execute(
        """SELECT * FROM orders
           WHERE birth_data=? AND status='paid'
           ORDER BY id DESC LIMIT 1""",
        (key,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def update_payjs_info(order_id: str, payjs_order_id: str, qrcode_url: str = ""):
    """Store PayJS order info after calling PayJS native API."""
    conn = _get_conn()
    conn.execute(
        "UPDATE orders SET payjs_order_id=? WHERE order_id=?",
        (payjs_order_id, order_id),
    )
    conn.commit()


def mark_paid(order_id: str, notify_raw: str):
    """Mark order as paid after receiving PayJS callback."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn = _get_conn()
    conn.execute(
        """UPDATE orders SET status='paid', paid_at=?, notify_raw=?
           WHERE order_id=? AND status='pending'""",
        (now, notify_raw, order_id),
    )
    conn.commit()


def mark_failed(order_id: str, reason: str = ""):
    """Mark order as failed."""
    conn = _get_conn()
    conn.execute("UPDATE orders SET status='failed', notify_raw=? WHERE order_id=?", (reason, order_id))
    conn.commit()


def save_report(order_id: str, report_json: dict):
    """Store the AI report after successful DeepSeek call."""
    conn = _get_conn()
    conn.execute(
        "UPDATE orders SET report_json=?, report_ready=1 WHERE order_id=?",
        (json.dumps(report_json, ensure_ascii=False), order_id),
    )
    conn.commit()


def get_order_status(order_id: str) -> dict:
    """Get order payment status and optionally the report if ready."""
    order = get_order(order_id)
    if order is None:
        return {"status": "not_found"}

    result = {
        "order_id": order["order_id"],
        "status": order["status"],
        "total_fee": order["total_fee"],
    }

    if order["report_ready"] and order["report_json"]:
        result["report"] = json.loads(order["report_json"])

    return result
