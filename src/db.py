import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple
import streamlit as st

@contextmanager
def conn_ctx(db_path: str):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db(db_path: str) -> None:
    with conn_ctx(db_path) as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash BLOB NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            city TEXT,
            state TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bar_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            sales_path TEXT NOT NULL,
            purchases_path TEXT,
            recipes_path TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(bar_id) REFERENCES bars(id)
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bar_id INTEGER NOT NULL,
            upload_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            report_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(bar_id) REFERENCES bars(id),
            FOREIGN KEY(upload_id) REFERENCES uploads(id)
        );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bars_user_id ON bars(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_uploads_bar_id ON uploads(bar_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_reports_bar_id ON reports(bar_id);")

def q_one(db_path: str, sql: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
    with conn_ctx(db_path) as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None

def q_all(db_path: str, sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    with conn_ctx(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

def exec_one(db_path: str, sql: str, params: Tuple[Any, ...] = ()) -> int:
    with conn_ctx(db_path) as conn:
        cur = conn.execute(sql, params)
        return int(cur.lastrowid)

def require_user() -> Dict[str, Any]:
    u = st.session_state.get("user")
    if not u:
        raise RuntimeError("Not logged in")
    return u

