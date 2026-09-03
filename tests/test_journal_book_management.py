from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.runtime import bootstrap_runtime


def test_edit_and_delete_book_metadata_preserve_reading_and_growth(tmp_path):
    runtime = bootstrap_runtime(data_dir=tmp_path / 'data', resources=tmp_path / 'resources')
    runtime.journal.add_book('b1', '원제', author='원저자')
    runtime.journal.attach_note(
        runtime.store, 'f1', '오래 남은 문장', book_id='b1', progress_text='42쪽',
    )
    before = runtime.store.load_state()

    edited = runtime.journal.update_book('b1', title='수정된 제목', author='수정 저자')
    assert (edited.title, edited.author) == ('수정된 제목', '수정 저자')
    assert len(runtime.journal.notes_for_book('b1')) == 1

    runtime.journal.delete_book_metadata('b1')
    assert runtime.journal.get_book('b1') is None
    assert runtime.store.count_notes() == 1
    assert runtime.store.load_state() == before
