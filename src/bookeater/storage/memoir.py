from __future__ import annotations

"""Durable completed-monster books and per-cycle evolution landmarks."""

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
import uuid


@dataclass(frozen=True)
class MonsterMemoir:
    memoir_id: str
    monster_name: str
    final_form_id: str
    favorite_book: str
    started_at: str
    completed_at: str
    payload: dict


class MonsterMemoirStore:
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
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS monster_cycle (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    start_entry_rowid INTEGER NOT NULL DEFAULT 0
                );
                -- On first migration, the existing active monster owns the historical records.
                INSERT OR IGNORE INTO monster_cycle(singleton,start_entry_rowid) VALUES(1,0);

                CREATE TABLE IF NOT EXISTS monster_evolution_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_form_id TEXT NOT NULL,
                    to_form_id TEXT NOT NULL,
                    entry_count INTEGER NOT NULL,
                    happened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS monster_memoirs (
                    memoir_id TEXT PRIMARY KEY,
                    monster_name TEXT NOT NULL,
                    final_form_id TEXT NOT NULL,
                    favorite_book TEXT NOT NULL DEFAULT '',
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    payload_json TEXT NOT NULL
                );
                """
            )
            con.commit()
        finally:
            con.close()

    def record_evolution(self, from_form_id: str, to_form_id: str, entry_count: int) -> None:
        if str(from_form_id) == str(to_form_id):
            return
        con = self._connect()
        try:
            exists = con.execute(
                'SELECT 1 FROM monster_evolution_events WHERE to_form_id=?', (str(to_form_id),)
            ).fetchone()
            if exists is None:
                con.execute(
                    'INSERT INTO monster_evolution_events(from_form_id,to_form_id,entry_count) VALUES(?,?,?)',
                    (str(from_form_id), str(to_form_id), max(0, int(entry_count))),
                )
            con.commit()
        finally:
            con.close()

    def create_current_book(self, *, monster_name: str, final_form_id: str, favorite_book: str = '') -> MonsterMemoir:
        con = self._connect()
        try:
            con.execute('BEGIN IMMEDIATE')
            cycle = con.execute(
                'SELECT started_at,start_entry_rowid FROM monster_cycle WHERE singleton=1'
            ).fetchone()
            start_rowid = int(cycle['start_entry_rowid']) if cycle else 0
            started_at = str(cycle['started_at']) if cycle else ''
            clean_name = str(monster_name or '').strip() or '내 몬스터'
            existing = con.execute(
                'SELECT * FROM monster_memoirs WHERE started_at=? AND monster_name=? AND final_form_id=? '
                'ORDER BY rowid DESC LIMIT 1',
                (started_at, clean_name, str(final_form_id)),
            ).fetchone()
            if existing is not None:
                con.commit()
                return self._row(existing)
            events = [dict(row) for row in con.execute(
                'SELECT from_form_id,to_form_id,entry_count,happened_at '
                'FROM monster_evolution_events ORDER BY event_id'
            ).fetchall()]
            records = [dict(row) for row in con.execute(
                """
                SELECT r.feed_id,r.note_text,r.created_at,r.fed_at,c.progress_text,
                       b.book_id,b.title,b.author,b.cover_url
                FROM reading_entries r
                LEFT JOIN reading_entry_context c ON c.feed_id=r.feed_id
                LEFT JOIN books b ON b.book_id=c.book_id
                WHERE r.rowid>? AND r.status='fed' AND c.book_id IS NOT NULL
                ORDER BY r.rowid
                """,
                (start_rowid,),
            ).fetchall()]
            payload = {'evolutions': events, 'records': records}
            memoir_id = uuid.uuid4().hex
            con.execute(
                'INSERT INTO monster_memoirs(memoir_id,monster_name,final_form_id,favorite_book,started_at,payload_json) '
                'VALUES(?,?,?,?,?,?)',
                (memoir_id, clean_name, str(final_form_id), str(favorite_book or '').strip(), started_at,
                 json.dumps(payload, ensure_ascii=False, separators=(',', ':'))),
            )
            row = con.execute('SELECT * FROM monster_memoirs WHERE memoir_id=?', (memoir_id,)).fetchone()
            con.commit()
            return self._row(row)
        except Exception:
            if con.in_transaction:
                con.rollback()
            raise
        finally:
            con.close()

    @staticmethod
    def _row(row: sqlite3.Row) -> MonsterMemoir:
        try:
            payload = json.loads(str(row['payload_json']))
        except (json.JSONDecodeError, TypeError):
            payload = {'evolutions': [], 'records': []}
        return MonsterMemoir(
            str(row['memoir_id']), str(row['monster_name']), str(row['final_form_id']),
            str(row['favorite_book']), str(row['started_at']), str(row['completed_at']),
            payload if isinstance(payload, dict) else {'evolutions': [], 'records': []},
        )

    def list_books(self) -> list[MonsterMemoir]:
        con = self._connect()
        try:
            return [self._row(row) for row in con.execute(
                'SELECT * FROM monster_memoirs ORDER BY completed_at DESC,rowid DESC'
            ).fetchall()]
        finally:
            con.close()

    def begin_new_cycle(self) -> None:
        """Keep the library and memoirs, but reset only the active creature."""
        con = self._connect()
        try:
            con.execute('BEGIN IMMEDIATE')
            con.execute(
                "UPDATE monster_state SET revision=revision+1,entry_count=0,current_base=NULL,stage=0,"
                "species='글씨알',stats_json='{}',form_id='starter',recent_stats_json='{}' WHERE singleton=1"
            )
            con.execute('DELETE FROM monster_evolution_events')
            con.execute('DELETE FROM monster_encyclopedia')
            con.execute("INSERT INTO monster_encyclopedia(form_id) VALUES('starter')")
            con.execute('DELETE FROM monster_milestones')
            con.execute('INSERT INTO monster_milestones(singleton,met_at) VALUES(1,CURRENT_TIMESTAMP)')
            con.execute(
                "UPDATE monster_care SET fullness=65,mood=65,cleanliness=75,bond=0,updated_at=CURRENT_TIMESTAMP,"
                "bond_gain_date=date('now'),bond_gain_today=0,last_cared_date=date('now'),last_decay_date=date('now') "
                "WHERE singleton=1"
            )
            marker = con.execute('SELECT COALESCE(MAX(rowid),0) AS n FROM reading_entries').fetchone()
            con.execute(
                'INSERT INTO monster_cycle(singleton,started_at,start_entry_rowid) VALUES(1,CURRENT_TIMESTAMP,?) '
                'ON CONFLICT(singleton) DO UPDATE SET started_at=CURRENT_TIMESTAMP,start_entry_rowid=excluded.start_entry_rowid',
                (int(marker['n']),),
            )
            for key in ('monster_name','favorite_book_title','favorite_book_match','birth_imprint_feed_id',
                        'birth_imprint_status','intro_seen','growth_locked'):
                con.execute('DELETE FROM app_settings WHERE key=?', (key,))
            con.commit()
        except Exception:
            if con.in_transaction:
                con.rollback()
            raise
        finally:
            con.close()
