from __future__ import annotations

import sqlite3

import pytest

from bookeater.runtime import (
    DB_FILENAME,
    MODEL_RELATIVE_PATH,
    ModelUnavailable,
    RuntimeStartupError,
    LazyLocalAnalyzer,
    bootstrap_runtime,
    default_data_dir,
)


def test_default_windows_data_dir_uses_localappdata(tmp_path):
    p=default_data_dir(platform='win32',environ={'LOCALAPPDATA':str(tmp_path)},home=tmp_path/'home')
    assert p==tmp_path/'BookEater'


def test_default_linux_data_dir_honors_xdg(tmp_path):
    p=default_data_dir(platform='linux',environ={'XDG_DATA_HOME':str(tmp_path/'xdg')},home=tmp_path/'home')
    assert p==tmp_path/'xdg'/'bookeater'


def test_explicit_data_dir_env_wins(tmp_path):
    p=default_data_dir(platform='win32',environ={'BOOKEATER_DATA_DIR':str(tmp_path/'custom'),'LOCALAPPDATA':'ignored'},home=tmp_path)
    assert p==tmp_path/'custom'


def test_bootstrap_creates_local_db_without_loading_model(tmp_path):
    runtime=bootstrap_runtime(data_dir=tmp_path/'data',resources=tmp_path/'resources')
    assert runtime.database_path==tmp_path/'data'/DB_FILENAME
    assert runtime.database_path.is_file()
    assert runtime.model_dir==tmp_path/'resources'/MODEL_RELATIVE_PATH
    assert not runtime.analyzer.loaded


def test_missing_model_does_not_prevent_note_from_being_saved(tmp_path):
    runtime=bootstrap_runtime(data_dir=tmp_path/'data',resources=tmp_path/'resources')
    out=runtime.feed_service.submit('safe-before-model','이 장면이 왜 마음에 남는지 생각해 봤다.')
    assert out.status=='pending'
    assert runtime.store.count_notes(status='pending')==1
    assert runtime.store.load_state().entry_count==0
    saved=runtime.store.get_note('safe-before-model')
    assert saved is not None
    assert saved.last_error=='ModelUnavailable'


def test_lazy_analyzer_missing_resources_raises_specific_error(tmp_path):
    analyzer=LazyLocalAnalyzer(tmp_path/'missing-model')
    with pytest.raises(ModelUnavailable):
        analyzer.analyze('기록')
    assert not analyzer.loaded


def test_missing_model_failure_is_cached_but_can_be_reset(tmp_path):
    analyzer=LazyLocalAnalyzer(tmp_path/'missing-model')
    for _ in range(2):
        with pytest.raises(ModelUnavailable):
            analyzer.analyze('기록')
    analyzer.reset_failure()
    with pytest.raises(ModelUnavailable):
        analyzer.analyze('기록')


def test_existing_file_cannot_be_used_as_data_directory(tmp_path):
    target=tmp_path/'not-a-dir'
    target.write_text('x',encoding='utf-8')
    with pytest.raises(RuntimeStartupError):
        bootstrap_runtime(data_dir=target,resources=tmp_path/'resources')


def test_corrupt_database_is_not_overwritten_silently(tmp_path):
    data=tmp_path/'data';data.mkdir()
    db=data/DB_FILENAME
    original=b'not a sqlite database; preserve me'
    db.write_bytes(original)
    with pytest.raises(RuntimeStartupError):
        bootstrap_runtime(data_dir=data,resources=tmp_path/'resources')
    assert db.read_bytes()==original


def test_runtime_database_contains_no_raw_classifier_diagnostic_columns(tmp_path):
    runtime=bootstrap_runtime(data_dir=tmp_path/'data',resources=tmp_path/'resources')
    con=sqlite3.connect(runtime.database_path)
    try:
        cols={row[1] for row in con.execute('PRAGMA table_info(reading_entries)')}
    finally:
        con.close()
    forbidden={'scores','raw_scores','evidence','counter','null','keyword_hits','trait_reason'}
    assert cols.isdisjoint(forbidden)
