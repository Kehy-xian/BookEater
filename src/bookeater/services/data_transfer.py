from __future__ import annotations

"""Portable, transactional BookEater profile transfer.

A ``.bookeater-seed`` file carries reading history plus the companion state that was shaped by
that history: aggregate growth nutrition, current lineage, recent trajectory, milestones,
encountered forms and care/bond state. Device preferences (autostart, intro settings) and art
overrides are intentionally not transplanted.

Import and reset are destructive operations, so callers should make a backup first. This module
provides helpers that do that before changing the live database. Seed payloads are fully validated
before a write transaction begins; a malformed or incompatible seed leaves the live profile intact.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

from ..game.growth_routes import GROWTH_FORMS
from ..storage.journal import BOOK_STATUSES

SEED_FORMAT = 'bookeater.reading-seed'
SEED_VERSION = 1
MAX_SEED_BYTES = 100 * 1024 * 1024


class SeedFormatError(ValueError):
    """The selected file is not a valid compatible BookEater seed."""


@dataclass(frozen=True)
class SeedSummary:
    book_count: int
    note_count: int
    fed_count: int
    form_id: str
    exported_at: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _sha(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(payload)).hexdigest()


def _rows(con: sqlite3.Connection, sql: str) -> list[dict[str, Any]]:
    return [dict(row) for row in con.execute(sql).fetchall()]


def _collect_payload(database_path: str | Path) -> dict[str, Any]:
    con = sqlite3.connect(str(database_path), timeout=5.0)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA busy_timeout=5000')
    try:
        con.execute('BEGIN')
        state = con.execute(
            'SELECT revision,entry_count,current_base,stage,species,stats_json,form_id,recent_stats_json '
            'FROM monster_state WHERE singleton=1'
        ).fetchone()
        milestone = con.execute(
            'SELECT met_at FROM monster_milestones WHERE singleton=1'
        ).fetchone()
        care = con.execute(
            'SELECT fullness,mood,cleanliness,bond,updated_at FROM monster_care WHERE singleton=1'
        ).fetchone()
        if state is None or milestone is None or care is None:
            raise RuntimeError('profile singleton missing')
        payload = {
            'monster_state': dict(state),
            'books': _rows(con, 'SELECT book_id,title,author,status,isbn13,publisher,cover_url,source,created_at,updated_at,last_read_at FROM books ORDER BY rowid'),
            'reading_entries': _rows(con, 'SELECT feed_id,note_text,status,public_json,model_version,nutrition_policy,attempts,last_error,created_at,fed_at FROM reading_entries ORDER BY created_at,rowid'),
            'reading_entry_context': _rows(con, 'SELECT feed_id,book_id,progress_text FROM reading_entry_context ORDER BY rowid'),
            'monster_milestones': dict(milestone),
            'monster_encyclopedia': _rows(con, 'SELECT form_id,first_seen_at FROM monster_encyclopedia ORDER BY first_seen_at,form_id'),
            'monster_care': dict(care),
        }
        con.rollback()
        return payload
    finally:
        con.close()


def export_seed(database_path: str | Path, destination: str | Path) -> SeedSummary:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = _collect_payload(database_path)
    exported_at = _utc_now()
    document = {
        'format': SEED_FORMAT,
        'version': SEED_VERSION,
        'exported_at': exported_at,
        'payload_sha256': _sha(payload),
        'payload': payload,
    }
    # Write then replace so an interrupted export never leaves a half-valid requested file.
    temp = destination.with_name(destination.name + '.tmp')
    temp.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(destination)
    entries = payload['reading_entries']
    return SeedSummary(
        book_count=len(payload['books']),
        note_count=len(entries),
        fed_count=sum(1 for row in entries if row.get('status') == 'fed'),
        form_id=str(payload['monster_state'].get('form_id') or 'starter'),
        exported_at=exported_at,
    )


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SeedFormatError(f'{name} must be an object')
    return value


def _require_list(value: Any, name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(x, dict) for x in value):
        raise SeedFormatError(f'{name} must be a list of objects')
    return value


def _nonnegative_int(value: Any, name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise SeedFormatError(f'{name} must be an integer') from exc
    if number < 0:
        raise SeedFormatError(f'{name} must not be negative')
    return number


def _validate_payload(payload: dict[str, Any]) -> SeedSummary:
    state = _require_dict(payload.get('monster_state'), 'monster_state')
    books = _require_list(payload.get('books'), 'books')
    entries = _require_list(payload.get('reading_entries'), 'reading_entries')
    contexts = _require_list(payload.get('reading_entry_context'), 'reading_entry_context')
    milestone = _require_dict(payload.get('monster_milestones'), 'monster_milestones')
    encyclopedia = _require_list(payload.get('monster_encyclopedia'), 'monster_encyclopedia')
    care = _require_dict(payload.get('monster_care'), 'monster_care')

    form_id = str(state.get('form_id') or '')
    if form_id not in GROWTH_FORMS:
        raise SeedFormatError(f'unknown or unsupported form_id: {form_id}')
    _nonnegative_int(state.get('revision', 0), 'revision')
    entry_count = _nonnegative_int(state.get('entry_count', 0), 'entry_count')
    stage = _nonnegative_int(state.get('stage', 0), 'stage')
    if stage > 3:
        raise SeedFormatError('unsupported growth stage')
    for field in ('stats_json', 'recent_stats_json'):
        raw = state.get(field, '{}')
        try:
            decoded = json.loads(raw or '{}')
        except (TypeError, json.JSONDecodeError) as exc:
            raise SeedFormatError(f'invalid {field}') from exc
        if not isinstance(decoded, dict):
            raise SeedFormatError(f'{field} must contain an object')

    book_ids: set[str] = set()
    for book in books:
        bid = str(book.get('book_id') or '').strip()
        if not bid or bid in book_ids:
            raise SeedFormatError('blank or duplicate book_id')
        book_ids.add(bid)
        if not str(book.get('title') or '').strip():
            raise SeedFormatError('book title must not be blank')
        if str(book.get('status') or '') not in BOOK_STATUSES:
            raise SeedFormatError('invalid book status')

    feed_ids: set[str] = set()
    fed_count = 0
    for entry in entries:
        fid = str(entry.get('feed_id') or '').strip()
        if not fid or fid in feed_ids:
            raise SeedFormatError('blank or duplicate feed_id')
        feed_ids.add(fid)
        if not str(entry.get('note_text') or '').strip():
            raise SeedFormatError('note_text must not be blank')
        status = str(entry.get('status') or '')
        if status not in {'pending', 'fed'}:
            raise SeedFormatError('invalid reading entry status')
        fed_count += int(status == 'fed')
        _nonnegative_int(entry.get('attempts', 0), 'attempts')
        raw_public = entry.get('public_json')
        if raw_public:
            try:
                parsed = json.loads(raw_public)
            except (TypeError, json.JSONDecodeError) as exc:
                raise SeedFormatError('invalid public_json') from exc
            if not isinstance(parsed, dict):
                raise SeedFormatError('public_json must contain an object')

    context_ids: set[str] = set()
    for context in contexts:
        fid = str(context.get('feed_id') or '').strip()
        if fid not in feed_ids or fid in context_ids:
            raise SeedFormatError('orphan or duplicate reading context')
        context_ids.add(fid)
        bid = context.get('book_id')
        if bid is not None and str(bid) not in book_ids:
            raise SeedFormatError('reading context references missing book')

    met_at = str(milestone.get('met_at') or '').strip()
    if not met_at:
        raise SeedFormatError('met_at must not be blank')

    seen: set[str] = set()
    for row in encyclopedia:
        seen_id = str(row.get('form_id') or '')
        if seen_id not in GROWTH_FORMS or seen_id in seen:
            raise SeedFormatError('invalid or duplicate encyclopedia form')
        seen.add(seen_id)
    if 'starter' not in seen or form_id not in seen:
        raise SeedFormatError('encyclopedia must contain starter and current lineage form')

    for field in ('fullness', 'mood', 'cleanliness', 'bond'):
        value = _nonnegative_int(care.get(field, 0), field)
        if value > 100:
            raise SeedFormatError(f'{field} must be between 0 and 100')

    # The aggregate meaningful-count may not exceed successfully fed records. It may be lower
    # because administrative notes can be fed without nourishing growth.
    if entry_count > fed_count:
        raise SeedFormatError('entry_count exceeds fed reading records')

    return SeedSummary(len(books), len(entries), fed_count, form_id, '')


def read_seed(path: str | Path) -> tuple[dict[str, Any], SeedSummary]:
    path = Path(path)
    if not path.is_file():
        raise SeedFormatError('seed file does not exist')
    if path.stat().st_size > MAX_SEED_BYTES:
        raise SeedFormatError('seed file is too large')
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SeedFormatError('seed file is unreadable') from exc
    document = _require_dict(document, 'seed')
    if document.get('format') != SEED_FORMAT or document.get('version') != SEED_VERSION:
        raise SeedFormatError('unsupported seed format/version')
    payload = _require_dict(document.get('payload'), 'payload')
    if str(document.get('payload_sha256') or '') != _sha(payload):
        raise SeedFormatError('seed checksum mismatch')
    summary = _validate_payload(payload)
    return payload, SeedSummary(
        summary.book_count, summary.note_count, summary.fed_count, summary.form_id,
        str(document.get('exported_at') or ''),
    )


def _backup_path(data_dir: str | Path, prefix: str) -> Path:
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    folder = Path(data_dir) / 'backups'
    folder.mkdir(parents=True, exist_ok=True)
    candidate = folder / f'{prefix}-{stamp}.bookeater-seed'
    suffix = 1
    while candidate.exists():
        candidate = folder / f'{prefix}-{stamp}-{suffix}.bookeater-seed'
        suffix += 1
    return candidate


def import_seed(database_path: str | Path, seed_path: str | Path, *, data_dir: str | Path) -> tuple[SeedSummary, Path]:
    payload, summary = read_seed(seed_path)  # full validation before backup/write
    backup = _backup_path(data_dir, 'pre-plant')
    export_seed(database_path, backup)

    state = payload['monster_state']
    con = sqlite3.connect(str(database_path), timeout=5.0)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA busy_timeout=5000')
    try:
        con.execute('BEGIN IMMEDIATE')
        con.execute('DELETE FROM reading_entry_context')
        con.execute('DELETE FROM reading_entries')
        con.execute('DELETE FROM books')
        con.execute('DELETE FROM monster_encyclopedia')

        for book in payload['books']:
            con.execute(
                'INSERT INTO books(book_id,title,author,status,isbn13,publisher,cover_url,source,created_at,updated_at,last_read_at) '
                'VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                tuple(book.get(k) for k in ('book_id','title','author','status','isbn13','publisher','cover_url','source','created_at','updated_at','last_read_at')),
            )
        for entry in payload['reading_entries']:
            con.execute(
                'INSERT INTO reading_entries(feed_id,note_text,status,public_json,model_version,nutrition_policy,attempts,last_error,created_at,fed_at) '
                'VALUES(?,?,?,?,?,?,?,?,?,?)',
                tuple(entry.get(k) for k in ('feed_id','note_text','status','public_json','model_version','nutrition_policy','attempts','last_error','created_at','fed_at')),
            )
        for context in payload['reading_entry_context']:
            con.execute(
                'INSERT INTO reading_entry_context(feed_id,book_id,progress_text) VALUES(?,?,?)',
                (context.get('feed_id'), context.get('book_id'), context.get('progress_text')),
            )

        con.execute(
            'UPDATE monster_state SET revision=?,entry_count=?,current_base=?,stage=?,species=?,stats_json=?,form_id=?,recent_stats_json=? WHERE singleton=1',
            tuple(state.get(k) for k in ('revision','entry_count','current_base','stage','species','stats_json','form_id','recent_stats_json')),
        )
        con.execute('DELETE FROM monster_milestones')
        con.execute(
            'INSERT INTO monster_milestones(singleton,met_at) VALUES(1,?)',
            (payload['monster_milestones']['met_at'],),
        )
        for row in payload['monster_encyclopedia']:
            con.execute(
                'INSERT INTO monster_encyclopedia(form_id,first_seen_at) VALUES(?,?)',
                (row.get('form_id'), row.get('first_seen_at')),
            )
        care = payload['monster_care']
        con.execute(
            'UPDATE monster_care SET fullness=?,mood=?,cleanliness=?,bond=?,updated_at=? WHERE singleton=1',
            (care.get('fullness'), care.get('mood'), care.get('cleanliness'), care.get('bond'), care.get('updated_at')),
        )
        con.commit()
    except Exception:
        if con.in_transaction:
            con.rollback()
        raise
    finally:
        con.close()
    return summary, backup


def reset_reading_and_genetics(
    database_path: str | Path,
    *,
    data_dir: str | Path,
    reset_settings: bool = False,
) -> Path:
    """Reset the profile and optionally every SQLite-backed app preference."""
    backup = _backup_path(data_dir, 'pre-reset')
    export_seed(database_path, backup)
    con = sqlite3.connect(str(database_path), timeout=5.0)
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA busy_timeout=5000')
    try:
        con.execute('BEGIN IMMEDIATE')
        con.execute('DELETE FROM reading_entry_context')
        con.execute('DELETE FROM reading_entries')
        con.execute('DELETE FROM books')
        con.execute(
            "UPDATE monster_state SET revision=revision+1,entry_count=0,current_base=NULL,stage=0,species='글씨알',stats_json='{}',form_id='starter',recent_stats_json='{}' WHERE singleton=1"
        )
        con.execute('DELETE FROM monster_milestones')
        con.execute("INSERT INTO monster_milestones(singleton,met_at) VALUES(1,CURRENT_TIMESTAMP)")
        con.execute('DELETE FROM monster_encyclopedia')
        con.execute("INSERT INTO monster_encyclopedia(form_id) VALUES('starter')")
        con.execute(
            'UPDATE monster_care SET fullness=65,mood=65,cleanliness=75,bond=0,updated_at=CURRENT_TIMESTAMP WHERE singleton=1'
        )
        if reset_settings:
            con.execute('DELETE FROM app_settings')
        con.commit()
    except Exception:
        if con.in_transaction:
            con.rollback()
        raise
    finally:
        con.close()
    return backup
