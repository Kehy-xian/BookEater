from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.runtime import bootstrap_runtime
from bookeater.services.data_transfer import import_seed, reset_reading_and_genetics
from bookeater.services.profile_transfer import export_profile_seed, plant_profile_seed, reset_profile
from bookeater.storage.draft import MAX_DRAFT_CHARS, MAX_PROGRESS_CHARS


def test_draft_survives_runtime_restart_and_can_be_cleared(tmp_path):
    data = tmp_path / 'profile'
    first = bootstrap_runtime(data_dir=data, resources=tmp_path / 'resources')
    first.journal.add_book('b1', '초안 책', author='작가')
    first.drafts.save(book_id='b1', progress_text='42쪽', note_text='아직 먹이지 않은 문장')

    second = bootstrap_runtime(data_dir=data, resources=tmp_path / 'resources')
    draft = second.drafts.load()
    assert draft is not None
    assert draft.book_id == 'b1'
    assert draft.progress_text == '42쪽'
    assert draft.note_text == '아직 먹이지 않은 문장'

    second.drafts.clear()
    assert second.drafts.load() is None


def test_draft_limits_untrusted_text_size(tmp_path):
    runtime = bootstrap_runtime(data_dir=tmp_path / 'profile', resources=tmp_path / 'resources')
    runtime.drafts.save(
        book_id='x' * 500,
        progress_text='p' * (MAX_PROGRESS_CHARS + 50),
        note_text='n' * (MAX_DRAFT_CHARS + 50),
    )
    draft = runtime.drafts.load()
    assert draft is not None
    assert len(draft.progress_text) == MAX_PROGRESS_CHARS
    assert len(draft.note_text) == MAX_DRAFT_CHARS
    assert len(draft.book_id or '') <= 200


def _seed_and_target(tmp_path):
    source = bootstrap_runtime(data_dir=tmp_path / 'source', resources=tmp_path / 'resources')
    source.journal.add_book('source-book', '심을 책')
    seed = tmp_path / 'seed.bookeater-seed'
    export_profile_seed(source.database_path, seed)

    target = bootstrap_runtime(data_dir=tmp_path / 'target', resources=tmp_path / 'resources')
    target.journal.add_book('old-book', '기존 책')
    target.drafts.save(book_id='old-book', note_text='기존 프로필의 미제출 초안')
    return seed, target


def test_profile_plant_clears_old_unsubmitted_draft(tmp_path):
    seed, target = _seed_and_target(tmp_path)
    plant_profile_seed(target.database_path, seed, data_dir=target.data_dir)
    assert target.drafts.load() is None


def test_core_import_clears_draft_inside_profile_replacement_transaction(tmp_path):
    seed, target = _seed_and_target(tmp_path)
    # Call the format-level import directly so this assertion cannot be satisfied only by the
    # profile_transfer post-cleanup wrapper. The SQLite trigger must clear the old draft when the
    # milestone singleton is replaced in the same transaction.
    import_seed(target.database_path, seed, data_dir=target.data_dir)
    assert target.drafts.load() is None


def test_profile_reset_clears_draft_but_keeps_device_setting(tmp_path):
    runtime = bootstrap_runtime(data_dir=tmp_path / 'profile', resources=tmp_path / 'resources')
    runtime.journal.add_book('b1', '초안 책')
    runtime.drafts.save(book_id='b1', note_text='초기화 전에 쓰던 초안')
    runtime.settings.set_bool('intro_drop_enabled', False)

    reset_profile(runtime.database_path, data_dir=runtime.data_dir)
    assert runtime.drafts.load() is None
    assert runtime.settings.get_bool('intro_drop_enabled', True) is False


def test_core_reset_clears_draft_inside_reset_transaction(tmp_path):
    runtime = bootstrap_runtime(data_dir=tmp_path / 'profile', resources=tmp_path / 'resources')
    runtime.journal.add_book('b1', '초안 책')
    runtime.drafts.save(book_id='b1', note_text='초기화 직전 초안')

    reset_reading_and_genetics(runtime.database_path, data_dir=runtime.data_dir)
    assert runtime.drafts.load() is None
