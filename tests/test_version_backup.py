from __future__ import annotations

from pathlib import Path
import sqlite3
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.runtime import RuntimeStartupError, bootstrap_runtime
from bookeater.services.version_backup import VERSION_MARKER, read_last_successful_version
from bookeater.version import APP_VERSION


def _upgrade_backups(data: Path):
    folder = data / 'backups' / 'version-upgrades'
    return sorted(folder.glob('*.sqlite3')) if folder.is_dir() else []


def test_fresh_profile_marks_version_without_redundant_backup(tmp_path):
    data = tmp_path / 'profile'
    bootstrap_runtime(data_dir=data, resources=tmp_path / 'resources')
    assert read_last_successful_version(data) == APP_VERSION
    assert _upgrade_backups(data) == []


def test_changed_version_creates_live_sqlite_backup_before_opening_new_runtime(tmp_path):
    data = tmp_path / 'profile'
    runtime = bootstrap_runtime(data_dir=data, resources=tmp_path / 'resources')
    runtime.journal.add_book('keep-me', '업데이트 전에 있던 책', author='작가')
    (data / VERSION_MARKER).write_text('0.0.1-old\n', encoding='utf-8')

    reopened = bootstrap_runtime(data_dir=data, resources=tmp_path / 'resources')
    assert reopened.journal.get_book('keep-me') is not None
    backups = _upgrade_backups(data)
    assert len(backups) == 1
    con = sqlite3.connect(str(backups[0]))
    try:
        row = con.execute("SELECT title FROM books WHERE book_id='keep-me'").fetchone()
        assert row == ('업데이트 전에 있던 책',)
        assert con.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
    finally:
        con.close()
    assert read_last_successful_version(data) == APP_VERSION


def test_legacy_profile_without_version_marker_gets_one_conservative_backup(tmp_path):
    data = tmp_path / 'profile'
    runtime = bootstrap_runtime(data_dir=data, resources=tmp_path / 'resources')
    runtime.journal.add_book('legacy', '예전 기록')
    (data / VERSION_MARKER).unlink()

    bootstrap_runtime(data_dir=data, resources=tmp_path / 'resources')
    assert len(_upgrade_backups(data)) == 1
    assert read_last_successful_version(data) == APP_VERSION


def test_corrupt_existing_database_aborts_before_version_marker_is_advanced(tmp_path):
    data = tmp_path / 'profile'
    data.mkdir(parents=True)
    db = data / 'bookeater.sqlite3'
    original = b'not a sqlite database'
    db.write_bytes(original)
    (data / VERSION_MARKER).write_text('0.0.1-old\n', encoding='utf-8')

    with pytest.raises(RuntimeStartupError):
        bootstrap_runtime(data_dir=data, resources=tmp_path / 'resources')
    assert db.read_bytes() == original
    assert read_last_successful_version(data) == '0.0.1-old'
