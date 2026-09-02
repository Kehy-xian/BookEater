from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.runtime import bootstrap_runtime
from bookeater.services.profile_transfer import (
    UnsafeTransferTarget,
    export_profile_seed,
    plant_profile_seed,
)


def _set_profile(runtime, *, revision: int, form_id: str, title: str) -> None:
    con = sqlite3.connect(runtime.database_path)
    try:
        con.execute(
            "INSERT OR REPLACE INTO books(book_id,title,author,status,source) VALUES('book',?,'저자','reading','manual')",
            (title,),
        )
        con.execute(
            "INSERT OR REPLACE INTO reading_entries(feed_id,note_text,status,public_json,model_version,nutrition_policy,attempts,fed_at) "
            "VALUES('feed','읽고 생각한 기록','fed','{}','test','test',1,CURRENT_TIMESTAMP)"
        )
        con.execute(
            "INSERT OR REPLACE INTO reading_entry_context(feed_id,book_id,progress_text) VALUES('feed','book','1장')"
        )
        con.execute(
            "UPDATE monster_state SET revision=?,entry_count=1,current_base='사유',stage=1,species='테스트',"
            "stats_json=?,form_id=?,recent_stats_json=? WHERE singleton=1",
            (revision, json.dumps({'사유': 2.0}, ensure_ascii=False), form_id,
             json.dumps({'사유': 1.0}, ensure_ascii=False)),
        )
        con.execute("INSERT OR IGNORE INTO monster_encyclopedia(form_id) VALUES(?)", (form_id,))
        con.commit()
    finally:
        con.close()


def test_safe_export_refuses_live_sqlite_destination_without_touching_database(tmp_path):
    runtime = bootstrap_runtime(data_dir=tmp_path / 'data', resources=tmp_path / 'resources')
    _set_profile(runtime, revision=9, form_id='route_a', title='보존할 책')
    before = runtime.database_path.read_bytes()

    with pytest.raises(UnsafeTransferTarget):
        export_profile_seed(runtime.database_path, runtime.database_path)

    assert runtime.database_path.read_bytes() == before
    assert runtime.journal.get_book('book').title == '보존할 책'


def test_plant_always_advances_live_revision_when_seed_revision_is_older(tmp_path):
    source = bootstrap_runtime(data_dir=tmp_path / 'source', resources=tmp_path / 'resources')
    _set_profile(source, revision=7, form_id='route_a', title='심을 책')
    seed = tmp_path / 'profile.bookeater-seed'
    export_profile_seed(source.database_path, seed)

    target = bootstrap_runtime(data_dir=tmp_path / 'target', resources=tmp_path / 'resources')
    _set_profile(target, revision=50, form_id='route_b', title='기존 책')
    before_revision = target.store.load_state().revision

    planted, backup = plant_profile_seed(target.database_path, seed, data_dir=target.data_dir)
    after = target.store.load_state()
    assert planted.form_id == 'route_a'
    assert backup.is_file()
    assert after.form_id == 'route_a'
    assert after.revision > before_revision
    assert target.journal.get_book('book').title == '심을 책'


def test_plant_preserves_newer_seed_revision_but_still_moves_forward(tmp_path):
    source = bootstrap_runtime(data_dir=tmp_path / 'source2', resources=tmp_path / 'resources')
    _set_profile(source, revision=80, form_id='route_c', title='미래 기록')
    seed = tmp_path / 'newer.bookeater-seed'
    export_profile_seed(source.database_path, seed)

    target = bootstrap_runtime(data_dir=tmp_path / 'target2', resources=tmp_path / 'resources')
    _set_profile(target, revision=20, form_id='route_a', title='현재 기록')
    plant_profile_seed(target.database_path, seed, data_dir=target.data_dir)
    assert target.store.load_state().revision == 80
    assert target.store.load_state().form_id == 'route_c'


def test_live_database_cannot_be_mistaken_for_seed_input(tmp_path):
    runtime = bootstrap_runtime(data_dir=tmp_path / 'same', resources=tmp_path / 'resources')
    with pytest.raises(UnsafeTransferTarget):
        plant_profile_seed(runtime.database_path, runtime.database_path, data_dir=runtime.data_dir)
