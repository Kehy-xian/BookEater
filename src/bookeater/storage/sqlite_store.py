from __future__ import annotations

"""Local-first persistence for the reading-to-monster loop.

The store keeps the user's note and aggregate hidden monster state on the local machine.
It deliberately does *not* persist raw classifier scores, keyword hits, rejected labels or
other diagnostics that could later leak into ordinary UI.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping


class FeedIdCollision(ValueError):
    """The same id was reused for different note text."""


class RevisionConflict(RuntimeError):
    """Monster state changed after a caller read it; retry from a fresh snapshot."""


@dataclass(frozen=True)
class StateRow:
    revision: int
    entry_count: int
    current_base: str | None
    stage: int
    species: str
    stats: dict[str, float]
    form_id: str = 'starter'


@dataclass(frozen=True)
class StoredNote:
    feed_id: str
    note_text: str
    status: str
    public_payload: dict[str, Any] | None
    attempts: int
    last_error: str | None


class SQLiteGameStore:
    """Small SQLite store designed for one desktop profile.

    Every state-changing method opens a short-lived connection. This makes reopen/recovery
    behavior easy to test and avoids sharing a sqlite connection across UI/background threads.
    """

    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ':memory:':
            Path(self.path).expanduser().parent.mkdir(parents=True, exist_ok=True)
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
                CREATE TABLE IF NOT EXISTS monster_state (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    revision INTEGER NOT NULL DEFAULT 0,
                    entry_count INTEGER NOT NULL DEFAULT 0,
                    current_base TEXT,
                    stage INTEGER NOT NULL DEFAULT 0,
                    species TEXT NOT NULL DEFAULT '글씨알',
                    stats_json TEXT NOT NULL DEFAULT '{}',
                    form_id TEXT NOT NULL DEFAULT 'starter'
                );

                CREATE TABLE IF NOT EXISTS reading_entries (
                    feed_id TEXT PRIMARY KEY,
                    note_text TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','fed')),
                    public_json TEXT,
                    model_version TEXT,
                    nutrition_policy TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    fed_at TEXT
                );

                INSERT OR IGNORE INTO monster_state(singleton) VALUES(1);
                """
            )
            # Migration for existing playable databases: add the route-form pointer in place.
            # Never rebuild/drop monster_state because that could destroy accumulated reading data.
            columns = {
                str(row['name']) for row in con.execute('PRAGMA table_info(monster_state)').fetchall()
            }
            if 'form_id' not in columns:
                con.execute(
                    "ALTER TABLE monster_state ADD COLUMN form_id TEXT NOT NULL DEFAULT 'starter'"
                )
            con.commit()
        finally:
            con.close()

    @staticmethod
    def _safe_stats(raw: str | None) -> dict[str, float]:
        try:
            data = json.loads(raw or '{}')
        except json.JSONDecodeError:
            return {}
        if not isinstance(data, dict):
            return {}
        out: dict[str, float] = {}
        for key, value in data.items():
            try:
                out[str(key)] = max(0.0, float(value))
            except (TypeError, ValueError):
                continue
        return out

    @staticmethod
    def _safe_payload(raw: str | None) -> dict[str, Any] | None:
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def load_state(self) -> StateRow:
        con = self._connect()
        try:
            row = con.execute(
                'SELECT revision,entry_count,current_base,stage,species,stats_json,form_id '
                'FROM monster_state WHERE singleton=1'
            ).fetchone()
            if row is None:
                raise RuntimeError('monster_state singleton is missing')
            return StateRow(
                revision=int(row['revision']),
                entry_count=max(0, int(row['entry_count'])),
                current_base=row['current_base'],
                stage=max(0, int(row['stage'])),
                species=str(row['species']),
                stats=self._safe_stats(row['stats_json']),
                form_id=str(row['form_id'] or 'starter'),
            )
        finally:
            con.close()

    def record_note(self, feed_id: str, note_text: str) -> StoredNote:
        feed_id = str(feed_id or '').strip()
        note_text = str(note_text or '').strip()
        if not feed_id:
            raise ValueError('feed_id must not be blank')
        if not note_text:
            raise ValueError('note_text must not be blank')

        con = self._connect()
        try:
            con.execute('BEGIN IMMEDIATE')
            row = con.execute(
                'SELECT feed_id,note_text,status,public_json,attempts,last_error '
                'FROM reading_entries WHERE feed_id=?', (feed_id,)
            ).fetchone()
            if row is None:
                con.execute(
                    'INSERT INTO reading_entries(feed_id,note_text) VALUES(?,?)',
                    (feed_id, note_text),
                )
                con.commit()
                return StoredNote(feed_id, note_text, 'pending', None, 0, None)
            if str(row['note_text']) != note_text:
                con.rollback()
                raise FeedIdCollision('feed_id already belongs to a different note')
            con.commit()
            return StoredNote(
                str(row['feed_id']), str(row['note_text']), str(row['status']),
                self._safe_payload(row['public_json']), int(row['attempts']), row['last_error'],
            )
        except Exception:
            if con.in_transaction:
                con.rollback()
            raise
        finally:
            con.close()

    def get_note(self, feed_id: str) -> StoredNote | None:
        con = self._connect()
        try:
            row = con.execute(
                'SELECT feed_id,note_text,status,public_json,attempts,last_error '
                'FROM reading_entries WHERE feed_id=?', (str(feed_id),)
            ).fetchone()
            if row is None:
                return None
            return StoredNote(
                str(row['feed_id']), str(row['note_text']), str(row['status']),
                self._safe_payload(row['public_json']), int(row['attempts']), row['last_error'],
            )
        finally:
            con.close()

    def pending_feed_ids(self, *, limit: int = 50) -> list[str]:
        if limit <= 0:
            return []
        con = self._connect()
        try:
            rows = con.execute(
                "SELECT feed_id FROM reading_entries WHERE status='pending' "
                'ORDER BY created_at, rowid LIMIT ?',
                (max(0, int(limit)),),
            ).fetchall()
            return [str(row['feed_id']) for row in rows]
        finally:
            con.close()

    def mark_pending_error(self, feed_id: str, error_code: str) -> None:
        # Technical details stay local and bounded. Ordinary UI never reads last_error.
        code = str(error_code or 'analysis_error')[:120]
        con = self._connect()
        try:
            con.execute(
                "UPDATE reading_entries SET attempts=attempts+1,last_error=? "
                "WHERE feed_id=? AND status='pending'",
                (code, str(feed_id)),
            )
            con.commit()
        finally:
            con.close()

    def commit_fed(
        self,
        *,
        feed_id: str,
        expected_revision: int,
        entry_count: int,
        current_base: str | None,
        stage: int,
        species: str,
        stats: Mapping[str, float],
        public_payload: Mapping[str, Any],
        model_version: str | None,
        nutrition_policy: str | None,
        form_id: str | None = None,
    ) -> dict[str, Any]:
        """Atomically consume one pending note and advance aggregate monster state.

        If another writer won the race, RevisionConflict is raised before either the note or
        state is changed. If this feed id was already consumed, its original public receipt is
        returned so repeated clicks/retries are idempotent.
        """
        con = self._connect()
        try:
            con.execute('BEGIN IMMEDIATE')
            note = con.execute(
                'SELECT status,public_json FROM reading_entries WHERE feed_id=?',
                (str(feed_id),),
            ).fetchone()
            if note is None:
                con.rollback()
                raise KeyError(feed_id)
            if note['status'] == 'fed':
                payload = self._safe_payload(note['public_json']) or {}
                con.commit()
                return payload

            state = con.execute(
                'SELECT revision,form_id FROM monster_state WHERE singleton=1'
            ).fetchone()
            if state is None:
                con.rollback()
                raise RuntimeError('monster_state singleton is missing')
            if int(state['revision']) != int(expected_revision):
                con.rollback()
                raise RevisionConflict('monster state revision changed')

            clean_stats = {}
            for key, value in stats.items():
                try:
                    clean_stats[str(key)] = max(0.0, float(value))
                except (TypeError, ValueError):
                    continue
            payload_json = json.dumps(dict(public_payload), ensure_ascii=False, separators=(',', ':'))
            stats_json = json.dumps(clean_stats, ensure_ascii=False, separators=(',', ':'))
            next_form = str(form_id or state['form_id'] or 'starter')

            con.execute(
                'UPDATE monster_state SET revision=revision+1,entry_count=?,current_base=?,stage=?,species=?,stats_json=?,form_id=? '
                'WHERE singleton=1',
                (
                    max(0, int(entry_count)), current_base, max(0, int(stage)), str(species),
                    stats_json, next_form,
                ),
            )
            con.execute(
                "UPDATE reading_entries SET status='fed',public_json=?,model_version=?,nutrition_policy=?,"
                "attempts=attempts+1,last_error=NULL,fed_at=CURRENT_TIMESTAMP WHERE feed_id=?",
                (payload_json, model_version, nutrition_policy, str(feed_id)),
            )
            con.commit()
            return dict(public_payload)
        except Exception:
            if con.in_transaction:
                con.rollback()
            raise
        finally:
            con.close()

    def count_notes(self, *, status: str | None = None) -> int:
        con = self._connect()
        try:
            if status is None:
                row = con.execute('SELECT COUNT(*) AS n FROM reading_entries').fetchone()
            else:
                row = con.execute(
                    'SELECT COUNT(*) AS n FROM reading_entries WHERE status=?', (str(status),)
                ).fetchone()
            return int(row['n']) if row else 0
        finally:
            con.close()
