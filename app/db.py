import hashlib
import json
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import DB_PATH

_lock = threading.RLock()
_conn = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer', password_hash TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS datasets (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, filename TEXT, created_at TEXT NOT NULL,
    is_demo INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 0, health_json TEXT, decisions_json TEXT, uploaded_by TEXT);
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, start TEXT NOT NULL, end TEXT NOT NULL,
    kind TEXT NOT NULL, discount REAL DEFAULT 0, source TEXT DEFAULT 'custom');
CREATE TABLE IF NOT EXISTS scenarios (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, params_json TEXT NOT NULL, summary TEXT,
    created_by TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, month TEXT NOT NULL, title TEXT NOT NULL, html_path TEXT, pdf_path TEXT,
    xlsx_path TEXT, sent_to TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

DEFAULT_SETTINGS = {
    "company_name": "Sahara Mart",
    "accent_color": "#0d9488",
    "logo_url": "",
    "currency": "Rs.",
    "fy_start_month": 7,              # July (Pakistan's financial year)
    "alert_threshold": 15,            # warn if a month's sales fall this % below forecast
    "report_day": 1,
    "report_recipients": ["owner@saharamart.example", "finance@saharamart.example"],
}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def tx():
    global _conn
    with _lock:
        if _conn is None:
            _conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
            _conn.row_factory = sqlite3.Row
            _conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield _conn
            _conn.commit()
        except Exception:
            _conn.rollback()
            raise


def query(sql, params=()):
    with tx() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def one(sql, params=()):
    r = query(sql, params)
    return r[0] if r else None


def execute(sql, params=()):
    with tx() as c:
        return c.execute(sql, params).lastrowid


def hash_password(pw, salt=None):
    salt = salt or secrets.token_hex(8)
    return f"{salt}${hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), 120_000).hex()}"


def check_password(pw, stored):
    if not stored or "$" not in stored:
        return False
    return secrets.compare_digest(hash_password(pw, stored.split("$", 1)[0]), stored)


def get_settings():
    out = json.loads(json.dumps(DEFAULT_SETTINGS))
    for r in query("SELECT key, value FROM settings"):
        out[r["key"]] = json.loads(r["value"])
    return out


def set_settings(values):
    with tx() as c:
        for k, v in values.items():
            if k in DEFAULT_SETTINGS:
                c.execute("INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, json.dumps(v)))


def init_schema():
    with tx() as c:
        c.executescript(SCHEMA)
