from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.services.memory import broad_route, choose_memory
from bookeater.storage.journal import ReadingJournalStore
from bookeater.storage.sqlite_store import SQLiteGameStore


def test_memory_returns_none_without_real_fed_records(tmp_path):
    db = tmp_path / 'game.sqlite3'
    game = SQLiteGameStore(db)
    journal = ReadingJournalStore(db)
    journal.add_book('b1', '빈 책')
    journal.attach_note(game, 'n1', '아직 분석 전 기록', book_id='b1')
    assert choose_memory(journal, rng=random.Random(1)) is None


def test_memory_quotes_only_a_real_stored_note(tmp_path):
    db = tmp_path / 'game.sqlite3'
    game = SQLiteGameStore(db)
    journal = ReadingJournalStore(db)
    journal.add_book('b1', '오래된 책', author='작가')
    journal.attach_note(game, 'n1', '첫 장면이 이상하게 오래 마음에 남았다.', book_id='b1', progress_text='42쪽')
    state = game.load_state()
    game.commit_fed(
        feed_id='n1', expected_revision=state.revision, entry_count=1, current_base=None,
        stage=0, species='글씨알', stats={}, public_payload={'feed_id':'n1','status':'fed','message':'','growth':None},
        model_version='test', nutrition_policy='test', form_id='starter',
    )

    moment = choose_memory(journal, current_form='route_b1', rng=random.Random(3))
    assert moment is not None
    assert moment.book_title == '오래된 책'
    assert moment.author == '작가'
    assert moment.note_text == '첫 장면이 이상하게 오래 마음에 남았다.'
    assert moment.progress_text == '42쪽'
    assert '마음' in moment.monster_line or '느낌' in moment.monster_line


def test_descendants_keep_their_broad_personality_route():
    assert broad_route('starter') == 'starter'
    assert broad_route('route_a2') == 'route_a'
    assert broad_route('route_b1_beta') == 'route_b'
    assert broad_route('route_c2_alpha') == 'route_c'
