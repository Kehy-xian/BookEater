from __future__ import annotations

import sqlite3

from bookeater.runtime import bootstrap_runtime
from bookeater.game.loop import ReadingFeedService
from bookeater.services.data_transfer import export_seed, import_seed


def _fed_book(runtime) -> None:
    runtime.journal.add_book('b1', '함께 읽은 책', author='작가')
    runtime.journal.attach_note(runtime.store, 'f1', '마음에 남은 기록', book_id='b1', progress_text='10쪽')
    con = sqlite3.connect(runtime.database_path)
    try:
        con.execute("UPDATE reading_entries SET status='fed',fed_at=CURRENT_TIMESTAMP WHERE feed_id='f1'")
        con.execute(
            "UPDATE monster_state SET entry_count=1,stage=3,species='완성체',form_id='route_a1_alpha',stats_json='{}',recent_stats_json='{}'"
        )
        con.commit()
    finally:
        con.close()


def test_completed_book_keeps_records_and_new_cycle_only_resets_active_monster(tmp_path):
    runtime = bootstrap_runtime(data_dir=tmp_path / 'data', resources=tmp_path / 'resources')
    _fed_book(runtime)
    runtime.memoirs.record_evolution('starter', 'route_a', 10)
    runtime.memoirs.record_evolution('route_a', 'route_a1', 30)
    runtime.settings.set('monster_name', '콩이')
    runtime.settings.set_bool('growth_locked', True)

    memoir = runtime.memoirs.create_current_book(
        monster_name='콩이', final_form_id='route_a1_alpha', favorite_book='어린 왕자',
    )
    assert memoir.payload['records'][0]['title'] == '함께 읽은 책'
    assert len(memoir.payload['evolutions']) == 2

    runtime.memoirs.begin_new_cycle()
    assert runtime.store.load_state().form_id == 'starter'
    assert runtime.store.load_state().entry_count == 0
    assert runtime.journal.get_book('b1').title == '함께 읽은 책'
    assert runtime.journal.notes_for_book('b1')[0].note_text == '마음에 남은 기록'
    assert runtime.memoirs.list_books()[0].monster_name == '콩이'
    assert runtime.settings.get('monster_name') is None
    assert runtime.settings.get('intro_seen') is None
    assert runtime.milestones.load().first_fed_at is None


def test_evolution_landmark_is_not_duplicated(tmp_path):
    runtime = bootstrap_runtime(data_dir=tmp_path / 'data', resources=tmp_path / 'resources')
    runtime.memoirs.record_evolution('starter', 'route_b', 10)
    runtime.memoirs.record_evolution('starter', 'route_b', 10)
    con = sqlite3.connect(runtime.database_path)
    try:
        assert con.execute('SELECT COUNT(*) FROM monster_evolution_events').fetchone()[0] == 1
    finally:
        con.close()


def test_locked_final_monster_accepts_record_without_analyzing_or_changing_genetics(tmp_path):
    runtime = bootstrap_runtime(data_dir=tmp_path / 'data', resources=tmp_path / 'resources')
    con = sqlite3.connect(runtime.database_path)
    try:
        con.execute(
            "UPDATE monster_state SET entry_count=77,stage=3,species='완성체',form_id='route_a1_alpha',"
            "stats_json='{\"사유\":12.0}',recent_stats_json='{\"사유\":3.0}'"
        )
        con.commit()
    finally:
        con.close()

    class MustNotRun:
        def analyze(self, _text):
            raise AssertionError('locked growth must not analyze new records')

    service = ReadingFeedService(runtime.store, MustNotRun(), growth_locked=lambda: True)
    before = runtime.store.load_state()
    outcome = service.submit('locked-note', '계속 쌓는 독서기록')
    after = runtime.store.load_state()
    assert outcome.status == 'fed'
    assert after.entry_count == before.entry_count
    assert after.form_id == before.form_id
    assert after.stats == before.stats


def test_memoir_survives_portable_profile_roundtrip(tmp_path):
    source = bootstrap_runtime(data_dir=tmp_path / 'source', resources=tmp_path / 'resources')
    _fed_book(source)
    for form_id in ('route_a', 'route_a1', 'route_a1_alpha'):
        source.encyclopedia.unlock(form_id)
    source.memoirs.record_evolution('starter', 'route_a', 10)
    source.memoirs.create_current_book(
        monster_name='콩이', final_form_id='route_a1_alpha', favorite_book='어린 왕자',
    )
    seed = tmp_path / 'profile.bookeater-seed'
    export_seed(source.database_path, seed)

    target = bootstrap_runtime(data_dir=tmp_path / 'target', resources=tmp_path / 'resources')
    import_seed(target.database_path, seed, data_dir=target.data_dir)
    restored = target.memoirs.list_books()[0]
    assert restored.monster_name == '콩이'
    assert restored.favorite_book == '어린 왕자'
    assert restored.payload['records'][0]['title'] == '함께 읽은 책'
