from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.runtime import bootstrap_runtime
from bookeater.services.data_transfer import (
    SeedFormatError,
    export_seed,
    import_seed,
    read_seed,
    reset_reading_and_genetics,
)


def _populate(runtime, *, title='원래 책', form_id='route_a') -> None:
    con = sqlite3.connect(runtime.database_path)
    try:
        con.execute(
            "INSERT INTO books(book_id,title,author,status,source) VALUES('b1',?,?, 'reading','manual')",
            (title, '작가'),
        )
        con.execute(
            "INSERT INTO reading_entries(feed_id,note_text,status,public_json,model_version,nutrition_policy,attempts,fed_at) "
            "VALUES('f1','주인공의 선택을 오래 생각했다.','fed','{}','test','test',1,CURRENT_TIMESTAMP)"
        )
        con.execute(
            "INSERT INTO reading_entry_context(feed_id,book_id,progress_text) VALUES('f1','b1','42쪽')"
        )
        con.execute(
            "UPDATE monster_state SET revision=7,entry_count=1,current_base='사유',stage=1,species='Route A',"
            "stats_json=?,form_id=?,recent_stats_json=? WHERE singleton=1",
            (json.dumps({'사유': 2.5}, ensure_ascii=False), form_id,
             json.dumps({'사유': 1.2}, ensure_ascii=False)),
        )
        con.execute(
            "INSERT OR IGNORE INTO monster_encyclopedia(form_id,first_seen_at) VALUES(?, '2026-01-03 10:00:00')",
            (form_id,),
        )
        con.execute("UPDATE monster_milestones SET met_at='2026-01-01 09:00:00' WHERE singleton=1")
        con.execute(
            "UPDATE monster_care SET fullness=88,mood=77,cleanliness=66,bond=44 WHERE singleton=1"
        )
        con.commit()
    finally:
        con.close()


def test_seed_roundtrip_replaces_profile_but_preserves_device_settings(tmp_path):
    source = bootstrap_runtime(data_dir=tmp_path / 'source', resources=tmp_path / 'resources')
    _populate(source)
    source.settings.set('autostart_enabled', '1')
    seed = tmp_path / 'my-reading.bookeater-seed'

    summary = export_seed(source.database_path, seed)
    assert summary.book_count == 1
    assert summary.note_count == 1
    assert summary.fed_count == 1
    assert summary.form_id == 'route_a'
    payload, checked = read_seed(seed)
    assert checked.form_id == 'route_a'
    assert payload['monster_state']['stats_json']

    target = bootstrap_runtime(data_dir=tmp_path / 'target', resources=tmp_path / 'resources')
    target.settings.set('autostart_enabled', '0')
    target.settings.set('intro_drop_enabled', '0')
    _populate(target, title='지워질 책', form_id='route_b')

    imported, backup = import_seed(target.database_path, seed, data_dir=target.data_dir)
    assert backup.is_file()
    assert imported.form_id == 'route_a'
    assert target.store.load_state().form_id == 'route_a'
    assert target.store.load_state().stats == {'사유': 2.5}
    assert target.store.load_state().recent_stats == {'사유': 1.2}
    assert target.journal.get_book('b1').title == '원래 책'
    assert target.journal.notes_for_book('b1')[0].progress_text == '42쪽'
    assert target.milestones.load().met_at.startswith('2026-01-01')
    assert 'route_a' in target.encyclopedia.encountered_ids()
    care = target.care.load()
    assert (care.fullness, care.mood, care.cleanliness, care.bond) == (88, 77, 66, 44)
    # Machine/app preferences are intentionally local and are not transplanted with the seed.
    assert target.settings.get('autostart_enabled') == '0'
    assert target.settings.get('intro_drop_enabled') == '0'


def test_tampered_seed_is_rejected_before_live_profile_changes_or_backup(tmp_path):
    source = bootstrap_runtime(data_dir=tmp_path / 'source', resources=tmp_path / 'resources')
    _populate(source)
    seed = tmp_path / 'seed.bookeater-seed'
    export_seed(source.database_path, seed)
    document = json.loads(seed.read_text(encoding='utf-8'))
    document['payload']['reading_entries'][0]['note_text'] = '위조된 기록'
    seed.write_text(json.dumps(document, ensure_ascii=False), encoding='utf-8')

    target = bootstrap_runtime(data_dir=tmp_path / 'target', resources=tmp_path / 'resources')
    _populate(target, title='보존되어야 함', form_id='route_b')
    before = target.store.load_state()
    with pytest.raises(SeedFormatError, match='checksum'):
        import_seed(target.database_path, seed, data_dir=target.data_dir)

    after = target.store.load_state()
    assert after == before
    assert target.journal.get_book('b1').title == '보존되어야 함'
    backups = target.data_dir / 'backups'
    assert not backups.exists() or not list(backups.iterdir())


def test_reset_clears_reading_genetics_identity_and_care_but_keeps_settings(tmp_path):
    runtime = bootstrap_runtime(data_dir=tmp_path / 'data', resources=tmp_path / 'resources')
    _populate(runtime)
    runtime.settings.set('autostart_enabled', '1')
    runtime.settings.set('intro_drop_enabled', '0')

    backup = reset_reading_and_genetics(runtime.database_path, data_dir=runtime.data_dir)
    assert backup.is_file()
    state = runtime.store.load_state()
    assert state.entry_count == 0
    assert state.form_id == 'starter'
    assert state.stats == {}
    assert state.recent_stats == {}
    assert runtime.store.count_notes() == 0
    assert runtime.journal.list_books() == []
    assert runtime.encyclopedia.encountered_ids() == frozenset({'starter'})
    assert runtime.milestones.load().first_fed_at is None
    care = runtime.care.load()
    assert (care.fullness, care.mood, care.cleanliness, care.bond) == (65, 65, 75, 0)
    assert runtime.settings.get('autostart_enabled') == '1'
    assert runtime.settings.get('intro_drop_enabled') == '0'

    # The automatic backup can restore the just-reset companion exactly.
    restored, _ = import_seed(runtime.database_path, backup, data_dir=runtime.data_dir)
    assert restored.form_id == 'route_a'
    assert runtime.store.load_state().form_id == 'route_a'
    assert runtime.store.count_notes(status='fed') == 1


def test_seed_extension_is_distinct_from_live_database_extension(tmp_path):
    runtime = bootstrap_runtime(data_dir=tmp_path / 'data', resources=tmp_path / 'resources')
    assert runtime.database_path.suffix == '.sqlite3'
    assert Path('reading-record.bookeater-seed').suffix == '.bookeater-seed'
