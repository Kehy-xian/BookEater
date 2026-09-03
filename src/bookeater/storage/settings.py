from __future__ import annotations

from pathlib import Path
import sqlite3


class AppSettingsStore:
    """Tiny SQLite-backed settings store kept beside all other local BookEater data."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=5.0)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA busy_timeout=5000')
        if self.path != ':memory:':
            con.execute('PRAGMA journal_mode=WAL')
        return con

    def _init_db(self) -> None:
        con = self._connect()
        try:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            con.commit()
        finally:
            con.close()

    def get(self, key: str, default: str | None = None) -> str | None:
        con = self._connect()
        try:
            row = con.execute('SELECT value FROM app_settings WHERE key=?', (str(key),)).fetchone()
            return str(row['value']) if row is not None else default
        finally:
            con.close()

    def set(self, key: str, value: str) -> None:
        con = self._connect()
        try:
            con.execute(
                """
                INSERT INTO app_settings(key,value) VALUES(?,?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP
                """,
                (str(key), str(value)),
            )
            con.commit()
        finally:
            con.close()

    def get_bool(self, key: str, default: bool = False) -> bool:
        raw = self.get(key)
        if raw is None:
            return bool(default)
        return raw.strip().lower() in {'1','true','yes','on'}

    def set_bool(self, key: str, value: bool) -> None:
        self.set(key, '1' if value else '0')

    def clear(self) -> None:
        """Restore every in-app preference to its built-in default."""
        con = self._connect()
        try:
            con.execute('DELETE FROM app_settings')
            con.commit()
        finally:
            con.close()
