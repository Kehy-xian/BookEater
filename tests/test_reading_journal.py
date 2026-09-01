from __future__ import annotations

import pytest

from bookeater.game.loop import ReadingFeedService
from bookeater.storage.journal import BookContextCollision, ReadingJournalStore
from bookeater.storage.sqlite_store import SQLiteGameStore


class StaticAnalyzer:
    def analyze(self, text):
        return {
            'response':['사유'], 'world':[],
            'scores':{'사유':.91}, 'null':{'response':.84,'world':.84},
            'model_version':'journal-test',
        }


def make(tmp_path):
    db = tmp_path / 'bookeater.sqlite3'
    game = SQLiteGameStore(db)
    journal = ReadingJournalStore(db)
    feed = ReadingFeedService(game, StaticAnalyzer())
    return game, journal, feed


def test_register_book_once_then_attach_many_notes(tmp_path):
    game, journal, feed = make(tmp_path)
    book = journal.add_book('b1', '오디세이아', author='호메로스')
    assert book.display_name == '오디세이아 — 호메로스'

    for i, progress in enumerate(('1권', '5권', '12권')):
        fid = f'n{i}'
        journal.attach_note(
            game, fid, f'{progress}에서 주인공의 선택을 오래 생각했다.',
            book_id='b1', progress_text=progress,
        )
        assert feed.retry(fid).status == 'fed'

    notes = journal.notes_for_book('b1')
    assert [n.progress_text for n in notes] == ['1권', '5권', '12권']
    assert len(notes) == 3
    assert all(n.status == 'fed' for n in notes)


def test_recent_book_order_follows_last_note(tmp_path):
    game, journal, _ = make(tmp_path)
    journal.add_book('a', '첫 책', author='작가 A')
    journal.add_book('b', '둘째 책', author='작가 B')
    journal.attach_note(game, 'na', '첫 책 기록', book_id='a')
    journal.attach_note(game, 'nb', '둘째 책 기록', book_id='b')
    assert journal.list_books()[0].book_id == 'b'


def test_book_title_required_but_author_optional(tmp_path):
    _, journal, _ = make(tmp_path)
    with pytest.raises(ValueError):
        journal.add_book('bad', '   ')
    book = journal.add_book('ok', '작가를 모르는 책')
    assert book.author == ''


def test_same_feed_id_cannot_switch_to_different_book(tmp_path):
    game, journal, _ = make(tmp_path)
    journal.add_book('a', 'A')
    journal.add_book('b', 'B')
    journal.attach_note(game, 'same', '같은 기록', book_id='a', progress_text='10쪽')
    with pytest.raises(BookContextCollision):
        journal.attach_note(game, 'same', '같은 기록', book_id='b', progress_text='10쪽')


def test_pure_bookkeeping_note_is_saved_but_does_not_age_monster(tmp_path):
    game, journal, feed = make(tmp_path)
    journal.add_book('b1', '테스트 책')
    journal.attach_note(
        game, 'meta', 'ISBN을 확인하고 반납일을 달력에 적었다.',
        book_id='b1', progress_text='대출 중',
    )
    out = feed.retry('meta')
    assert out.status == 'fed'
    assert game.count_notes(status='fed') == 1
    state = game.load_state()
    assert state.entry_count == 0
    assert state.stage == 0


def test_genuine_neutral_reading_note_can_age_without_trait_signal(tmp_path):
    class NeutralAnalyzer:
        def analyze(self, text):
            return {}

    db = tmp_path / 'neutral.sqlite3'
    game = SQLiteGameStore(db)
    journal = ReadingJournalStore(db)
    feed = ReadingFeedService(game, NeutralAnalyzer())
    journal.add_book('b1', '중립 책')
    journal.attach_note(game, 'n1', '오늘 읽은 부분을 조용히 다시 떠올려 봤다.', book_id='b1')
    assert feed.retry('n1').status == 'fed'
    assert game.load_state().entry_count == 1
