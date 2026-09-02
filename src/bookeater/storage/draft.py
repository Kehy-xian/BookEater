from __future__ import annotations

"""Crash-resistant local draft for the currently edited reading note.

Final reading entries are already committed to SQLite when the user feeds them.  This store protects
only text that has not been submitted yet, so there is no separate manual save state to reconcile
with monster genetics.  Drafts are deliberately excluded from portable seed exports because they
are not reading records yet.
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3


MAX_DRAFT_CHARS = 200_000
MAX_PROGRESS_CHARS = 500
MAX_BOOK_ID_CHARS = 200


@dataclass(frozen=True)
class ReadingDraft:
    book_id: str | None
    progress_text: str
    note_text: str
    updated_at: str


class ReadingDraftStore:
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
                CREATE TABLE IF NOT EXISTS reading_draft (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    book_id TEXT,
                    progress_text TEXT NOT NULL DEFAULT '',
                    note_text TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            con.commit()
        finally:
            con.close()

    def load(self) -> ReadingDraft | None:
        con = self._connect()
        try:
            row = con.execute(
                'SELECT book_id,progress_text,note_text,updated_at FROM reading_draft WHERE singleton=1'
            ).fetchone()
            if row is None:
                return None
            note = str(row['note_text'] or '')
            progress = str(row['progress_text'] or '')
            if not note and not progress:
                return None
            return ReadingDraft(
                book_id=(str(row['book_id']) if row['book_id'] else None),
                progress_text=progress,
                note_text=note,
                updated_at=str(row['updated_at']),
            )
        finally:
            con.close()

    def save(self, *, book_id: str | None, progress_text: str = '', note_text: str = '') -> ReadingDraft | None:
        clean_book = str(book_id or '').strip()[:MAX_BOOK_ID_CHARS] or None
        clean_progress = str(progress_text or '')[:MAX_PROGRESS_CHARS]
        clean_note = str(note_text or '')[:MAX_DRAFT_CHARS]
        if not clean_note and not clean_progress:
            self.clear()
            return None

        con = self._connect()
        try:
            con.execute(
                """
                INSERT INTO reading_draft(singleton,book_id,progress_text,note_text)
                VALUES(1,?,?,?)
                ON CONFLICT(singleton) DO UPDATE SET
                    book_id=excluded.book_id,
                    progress_text=excluded.progress_text,
                    note_text=excluded.note_text,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (clean_book, clean_progress, clean_note),
            )
            con.commit()
        finally:
            con.close()
        return self.load()

    def clear(self) -> None:
        con = self._connect()
        try:
            con.execute('DELETE FROM reading_draft WHERE singleton=1')
            con.commit()
        finally:
            con.close()
