from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from ..game.growth_routes import GROWTH_FORMS


@dataclass(frozen=True)
class EncounteredForm:
    form_id: str
    first_seen_at: str


class MonsterEncyclopediaStore:
    """Durable set of forms this user has actually encountered."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=5.0)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        con.execute('PRAGMA busy_timeout=5000')
        if self.path != ':memory:':
            con.execute('PRAGMA journal_mode=WAL')
        return con

    def _init_db(self) -> None:
        con = self._connect()
        try:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS monster_encyclopedia (
                    form_id TEXT PRIMARY KEY,
                    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            # Every profile has met the starter form. Future forms unlock only on explicit encounter.
            con.execute(
                "INSERT OR IGNORE INTO monster_encyclopedia(form_id) VALUES('starter')"
            )
            con.commit()
        finally:
            con.close()

    def unlock(self, form_id: str) -> EncounteredForm:
        form_id = str(form_id)
        if form_id not in GROWTH_FORMS:
            raise ValueError(f'unknown monster form: {form_id}')
        con = self._connect()
        try:
            con.execute(
                'INSERT OR IGNORE INTO monster_encyclopedia(form_id) VALUES(?)',
                (form_id,),
            )
            row = con.execute(
                'SELECT form_id,first_seen_at FROM monster_encyclopedia WHERE form_id=?',
                (form_id,),
            ).fetchone()
            con.commit()
            if row is None:
                raise RuntimeError('encyclopedia unlock failed')
            return EncounteredForm(str(row['form_id']), str(row['first_seen_at']))
        finally:
            con.close()

    def encountered(self, form_id: str) -> EncounteredForm | None:
        con = self._connect()
        try:
            row = con.execute(
                'SELECT form_id,first_seen_at FROM monster_encyclopedia WHERE form_id=?',
                (str(form_id),),
            ).fetchone()
            return (
                EncounteredForm(str(row['form_id']), str(row['first_seen_at']))
                if row is not None else None
            )
        finally:
            con.close()

    def encountered_ids(self) -> frozenset[str]:
        con = self._connect()
        try:
            rows = con.execute('SELECT form_id FROM monster_encyclopedia').fetchall()
            return frozenset(str(row['form_id']) for row in rows)
        finally:
            con.close()
