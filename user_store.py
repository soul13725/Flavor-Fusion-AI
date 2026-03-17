from __future__ import annotations

import hashlib
import json
import random
import sqlite3
from pathlib import Path
from typing import Any

from config import BASE_DIR

DB_PATH = BASE_DIR / "data" / "fusion_flavour_users.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _generate_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    names = {row[1] for row in cols}
    if column not in names:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def init_user_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT DEFAULT '',
                bio TEXT DEFAULT '',
                email_verified INTEGER DEFAULT 0,
                verification_code TEXT DEFAULT '',
                reset_code TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _ensure_column(conn, "users", "email_verified", "email_verified INTEGER DEFAULT 0")
        _ensure_column(conn, "users", "verification_code", "verification_code TEXT DEFAULT ''")
        _ensure_column(conn, "users", "reset_code", "reset_code TEXT DEFAULT ''")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                item_name TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, item_type, item_name),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                item_name TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )


def register_user(username: str, email: str, password: str) -> tuple[bool, str, str | None]:
    verification_code = _generate_code()
    try:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO users (username, email, password_hash, email_verified, verification_code)
                VALUES (?, ?, ?, 0, ?)
                """,
                (
                    username.strip(),
                    email.strip().lower(),
                    _hash_password(password),
                    verification_code,
                ),
            )
        return True, "Registration successful. Verify your email to continue.", verification_code
    except sqlite3.IntegrityError:
        return False, "Username or email already exists", None


def authenticate_user(identifier: str, password: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM users
            WHERE lower(email) = lower(?) OR username = ?
            """,
            (identifier.strip(), identifier.strip()),
        ).fetchone()
    if not row:
        return None
    if row["password_hash"] != _hash_password(password):
        return None
    return dict(row)


def request_email_verification(identifier: str) -> tuple[bool, str, str | None]:
    code = _generate_code()
    with _connect() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE lower(email) = lower(?) OR username = ?",
            (identifier.strip(), identifier.strip()),
        ).fetchone()
        if not row:
            return False, "User not found", None
        conn.execute(
            "UPDATE users SET verification_code = ? WHERE id = ?",
            (code, row["id"]),
        )
    return True, "Verification code generated", code


def verify_email(identifier: str, code: str) -> tuple[bool, str]:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, verification_code FROM users
            WHERE lower(email) = lower(?) OR username = ?
            """,
            (identifier.strip(), identifier.strip()),
        ).fetchone()
        if not row:
            return False, "User not found"
        if str(row["verification_code"]).strip() != str(code).strip():
            return False, "Invalid verification code"
        conn.execute(
            "UPDATE users SET email_verified = 1, verification_code = '' WHERE id = ?",
            (row["id"],),
        )
    return True, "Email verified successfully"


def request_password_reset(identifier: str) -> tuple[bool, str, str | None]:
    code = _generate_code()
    with _connect() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE lower(email) = lower(?) OR username = ?",
            (identifier.strip(), identifier.strip()),
        ).fetchone()
        if not row:
            return False, "User not found", None
        conn.execute(
            "UPDATE users SET reset_code = ? WHERE id = ?",
            (code, row["id"]),
        )
    return True, "Password reset code generated", code


def reset_password(identifier: str, code: str, new_password: str) -> tuple[bool, str]:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, reset_code FROM users
            WHERE lower(email) = lower(?) OR username = ?
            """,
            (identifier.strip(), identifier.strip()),
        ).fetchone()
        if not row:
            return False, "User not found"
        if str(row["reset_code"]).strip() != str(code).strip():
            return False, "Invalid reset code"
        conn.execute(
            "UPDATE users SET password_hash = ?, reset_code = '' WHERE id = ?",
            (_hash_password(new_password), row["id"]),
        )
    return True, "Password reset successful"


def update_profile(user_id: int, display_name: str, bio: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET display_name = ?, bio = ? WHERE id = ?",
            (display_name.strip(), bio.strip(), user_id),
        )


def get_user(user_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def add_favorite(user_id: int, item_type: str, item_name: str, payload: dict[str, Any]) -> None:
    payload_json = json.dumps(payload, ensure_ascii=False)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO favorites (user_id, item_type, item_name, payload_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, item_type, item_name)
            DO UPDATE SET payload_json = excluded.payload_json
            """,
            (user_id, item_type, item_name, payload_json),
        )


def add_recent(user_id: int, item_type: str, item_name: str, payload: dict[str, Any]) -> None:
    payload_json = json.dumps(payload, ensure_ascii=False)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO recents (user_id, item_type, item_name, payload_json) VALUES (?, ?, ?, ?)",
            (user_id, item_type, item_name, payload_json),
        )
        conn.execute(
            """
            DELETE FROM recents
            WHERE id NOT IN (
                SELECT id FROM recents
                WHERE user_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 30
            ) AND user_id = ?
            """,
            (user_id, user_id),
        )


def get_favorites(user_id: int, item_type: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM favorites WHERE user_id = ?"
    params: list[Any] = [user_id]
    if item_type:
        query += " AND item_type = ?"
        params.append(item_type)
    query += " ORDER BY created_at DESC, id DESC"

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()

    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        result.append(item)
    return result


def get_recents(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM recents
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        result.append(item)
    return result
