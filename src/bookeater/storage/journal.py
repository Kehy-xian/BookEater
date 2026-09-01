from __future__ import annotations

"""Book-level reading journal layered on top of the local game store.

A book is registered once, then many timestamped reading notes can be linked to it. The journal
never requires network access and does not store classifier internals. Legacy/unassigned notes
remain valid because book context is deliberately optional at the database level.
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .sqlite_store import SQLiteGameStore, StoredNote


BOOK_STATUSES = ('reading', 'completed', 'wishlist', 'paused')


@dataclass(frozen=True)
class StoredBook:
    book_id: str
    title: str
    author: str
    status: str
    isbn13: str | None
    publisher: str | None
    cover_url: str | None
    source: str

    @property
    def display_name(self) -> str:
        return f'{self.title} — {self.author}' if self.author else self.title


@dataclass(frozen=True)
class BookNote:
    feed_id: str
    note_text: str
    status: str
    progress_text: str | None
    created_at: str
    fed_at: str | None


class BookContextCollision(ValueError):
    """A feed id was reused with incompatible book/progress context."""


class ReadingJournalStore:
    """Local book metadata and one-to-many book→reading-entry relationships."""

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
                CREATE TABLE IF NOT EXISTS books (
                    book_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'reading'
                        CHECK (status IN ('reading','completed','wishlist','paused')),
                    isbn13 TEXT,
                    publisher TEXT,
                    cover_url TEXT,
                    source TEXT NOT NULL DEFAULT 'manual',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_read_at TEXT
                );

                CREATE TABLE IF NOT EXISTS reading_entry_context (
                    feed_id TEXT PRIMARY KEY,
                    book_id TEXT,
                    progress_text TEXT,
                    FOREIGN KEY(feed_id) REFERENCES reading_entries(feed_id) ON DELETE CASCADE,
                    FOREIGN KEY(book_id) REFERENCES books(book_id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_books_recent
                    ON books(status,last_read_at,updated_at);
                CREATE INDEX IF NOT EXISTS idx_entry_context_book
                    ON reading_entry_context(book_id);
                """
            )
            con.commit()
        finally:
            con.close()

    @staticmethod
    def _clean_optional(value: str | None) -> str | None:
        text = str(value or '').strip()
        return text or None

    def add_book(
        self,
        book_id: str,
        title: str,
        *,
        author: str = '',
        status: str = 'reading',
        isbn13: str | None = None,
        publisher: str | None = None,
        cover_url: str | None = None,
        source: str = 'manual',
    ) -> StoredBook:
        book_id = str(book_id or '').strip()
        title = str(title or '').strip()
        author = str(author or '').strip()
        status = str(status or 'reading').strip()
        if not book_id:
            raise ValueError('book_id must not be blank')
        if not title:
            raise ValueError('title must not be blank')
        if status not in BOOK_STATUSES:
            raise ValueError('invalid book status')

        con = self._connect()
        try:
            con.execute(
                """
                INSERT INTO books(book_id,title,author,status,isbn13,publisher,cover_url,source)
                VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(book_id) DO UPDATE SET
                    title=excluded.title,
                    author=excluded.author,
                    status=excluded.status,
                    isbn13=COALESCE(books.isbn13,excluded.isbn13),
                    publisher=COALESCE(books.publisher,excluded.publisher),
                    cover_url=COALESCE(books.cover_url,excluded.cover_url),
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    book_id, title, author, status,
                    self._clean_optional(isbn13), self._clean_optional(publisher),
                    self._clean_optional(cover_url), str(source or 'manual'),
                ),
            )
            con.commit()
        finally:
            con.close()
        book = self.get_book(book_id)
        if book is None:
            raise RuntimeError('book insert failed')
        return book

    def get_book(self, book_id: str) -> StoredBook | None:
        con = self._connect()
        try:
            row = con.execute(
                'SELECT book_id,title,author,status,isbn13,publisher,cover_url,source '
                'FROM books WHERE book_id=?',
                (str(book_id),),
            ).fetchone()
            if row is None:
                return None
            return StoredBook(
                str(row['book_id']), str(row['title']), str(row['author']), str(row['status']),
                row['isbn13'], row['publisher'], row['cover_url'], str(row['source']),
            )
        finally:
            con.close()

    def list_books(self, *, status: str | None = None, limit: int = 50) -> list[StoredBook]:
        if limit <= 0:
            return []
        con = self._connect()
        try:
            params: list[object] = []
            where = ''
            if status is not None:
                if status not in BOOK_STATUSES:
                    raise ValueError('invalid book status')
                where = 'WHERE status=?'
                params.append(status)
            params.append(max(1, int(limit)))
            rows = con.execute(
                f'SELECT book_id,title,author,status,isbn13,publisher,cover_url,source '
                f'FROM books {where} '
                'ORDER BY COALESCE(last_read_at,updated_at) DESC, rowid DESC LIMIT ?',
                params,
            ).fetchall()
            return [
                StoredBook(
                    str(r['book_id']), str(r['title']), str(r['author']), str(r['status']),
                    r['isbn13'], r['publisher'], r['cover_url'], str(r['source']),
                )
                for r in rows
            ]
        finally:
            con.close()

    def set_status(self, book_id: str, status: str) -> None:
        status = str(status).strip()
        if status not in BOOK_STATUSES:
            raise ValueError('invalid book status')
        con = self._connect()
        try:
            cur = con.execute(
                'UPDATE books SET status=?,updated_at=CURRENT_TIMESTAMP WHERE book_id=?',
                (status, str(book_id)),
            )
            if cur.rowcount != 1:
                raise KeyError(book_id)
            con.commit()
        finally:
            con.close()

    def attach_note(
        self,
        game_store: 'SQLiteGameStore',
        feed_id: str,
        note_text: str,
        *,
        book_id: str | None = None,
        progress_text: str | None = None,
    ) -> 'StoredNote':
        """Save a note first, then attach stable book/progress context before analysis.

        If attaching context fails, the raw reading note remains safely stored as pending rather
        than being lost. Repeating the same feed id is idempotent only when its context matches.
        """
        note = game_store.record_note(feed_id, note_text)
        clean_book = self._clean_optional(book_id)
        clean_progress = self._clean_optional(progress_text)
        if clean_book is not None and self.get_book(clean_book) is None:
            raise KeyError(clean_book)

        con = self._connect()
        try:
            con.execute('BEGIN IMMEDIATE')
            row = con.execute(
                'SELECT book_id,progress_text FROM reading_entry_context WHERE feed_id=?',
                (str(feed_id),),
            ).fetchone()
            if row is None:
                con.execute(
                    'INSERT INTO reading_entry_context(feed_id,book_id,progress_text) VALUES(?,?,?)',
                    (str(feed_id), clean_book, clean_progress),
                )
            else:
                old_book = self._clean_optional(row['book_id'])
                old_progress = self._clean_optional(row['progress_text'])
                if old_book != clean_book or old_progress != clean_progress:
                    con.rollback()
                    raise BookContextCollision('feed_id already has different reading context')
            if clean_book is not None:
                con.execute(
                    'UPDATE books SET last_read_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP '
                    'WHERE book_id=?',
                    (clean_book,),
                )
            con.commit()
            return note
        except Exception:
            if con.in_transaction:
                con.rollback()
            raise
        finally:
            con.close()

    def notes_for_book(self, book_id: str, *, limit: int = 200) -> list[BookNote]:
        if limit <= 0:
            return []
        con = self._connect()
        try:
            rows = con.execute(
                """
                SELECT e.feed_id,e.note_text,e.status,c.progress_text,e.created_at,e.fed_at
                FROM reading_entry_context c
                JOIN reading_entries e ON e.feed_id=c.feed_id
                WHERE c.book_id=?
                ORDER BY e.created_at ASC,e.rowid ASC
                LIMIT ?
                """,
                (str(book_id), max(1, int(limit))),
            ).fetchall()
            return [
                BookNote(
                    str(r['feed_id']), str(r['note_text']), str(r['status']), r['progress_text'],
                    str(r['created_at']), r['fed_at'],
                )
                for r in rows
            ]
        finally:
            con.close()
