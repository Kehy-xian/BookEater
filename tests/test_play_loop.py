from __future__ import annotations

import json

import pytest

from bookeater.game.loop import FeedOutcome, ReadingFeedService
from bookeater.storage.sqlite_store import FeedIdCollision, RevisionConflict, SQLiteGameStore


FORBIDDEN_PUBLIC_TOKENS = (
    'scores', 'raw_scores', 'evidence', 'counter', 'null', 'model_version',
    'nutrition_policy', 'current_base', 'stats', 'reason', '사유', '탐구', '감정',
    '감각', '상상', '모험', '자연', '사회', '어둠',
)


def strong_thought():
    return {
        'response':['사유'], 'world':[],
        'scores':{'사유':.91}, 'null':{'response':.84,'world':.84},
        'evidence':{'사유':1}, 'model_version':'fake-v1',
    }


class StaticAnalyzer:
    def __init__(self, payload=None):
        self.payload = strong_thought() if payload is None else payload
        self.calls = 0

    def analyze(self, text):
        self.calls += 1
        return self.payload


class FlakyAnalyzer:
    def __init__(self):
        self.fail = True
        self.calls = 0

    def analyze(self, text):
        self.calls += 1
        if self.fail:
            raise RuntimeError('model temporarily unavailable')
        return strong_thought()


class ConflictOnceStore(SQLiteGameStore):
    def __init__(self, path):
        super().__init__(path)
        self.conflicts_left = 1

    def commit_fed(self, **kwargs):
        if self.conflicts_left:
            self.conflicts_left -= 1
            raise RevisionConflict('synthetic race')
        return super().commit_fed(**kwargs)


def make_service(tmp_path, analyzer=None, store_cls=SQLiteGameStore):
    store = store_cls(tmp_path / 'game.sqlite3')
    analyzer = analyzer or StaticAnalyzer()
    return store, analyzer, ReadingFeedService(store, analyzer)


def test_submit_saves_and_feeds_atomically(tmp_path):
    store, analyzer, service = make_service(tmp_path)
    out = service.submit('n1', '결말의 선택이 옳았는지 오래 생각했다.')
    assert out.status == 'fed'
    assert out.growth is not None
    assert store.count_notes(status='fed') == 1
    state = store.load_state()
    assert state.entry_count == 1
    assert state.stats.get('사유') == 1.0
    assert analyzer.calls == 1


def test_duplicate_submit_is_idempotent(tmp_path):
    store, analyzer, service = make_service(tmp_path)
    first = service.submit('same', '왜 그런 선택을 했는지 오래 생각했다.')
    second = service.submit('same', '왜 그런 선택을 했는지 오래 생각했다.')
    assert first.to_public_dict() == second.to_public_dict()
    assert store.load_state().entry_count == 1
    assert store.count_notes() == 1
    assert analyzer.calls == 1


def test_feed_id_collision_cannot_silently_overwrite_note(tmp_path):
    store, _, service = make_service(tmp_path)
    service.submit('same', '첫 번째 기록')
    with pytest.raises(FeedIdCollision):
        service.submit('same', '완전히 다른 두 번째 기록')
    assert store.count_notes() == 1


def test_analysis_failure_keeps_note_pending_without_growth(tmp_path):
    analyzer = FlakyAnalyzer()
    store, _, service = make_service(tmp_path, analyzer)
    out = service.submit('pending-1', '마음에 남은 장면을 적어 둔다.')
    assert out.status == 'pending'
    assert out.growth is None
    assert store.count_notes(status='pending') == 1
    assert store.load_state().entry_count == 0
    saved = store.get_note('pending-1')
    assert saved is not None and saved.note_text == '마음에 남은 장면을 적어 둔다.'
    assert saved.attempts == 1
    assert saved.last_error == 'RuntimeError'


def test_pending_note_recovers_after_restart(tmp_path):
    db = tmp_path / 'game.sqlite3'
    flaky = FlakyAnalyzer()
    store1 = SQLiteGameStore(db)
    service1 = ReadingFeedService(store1, flaky)
    assert service1.submit('p1', '결말을 다시 생각해 보게 됐다.').status == 'pending'

    flaky.fail = False
    store2 = SQLiteGameStore(db)
    service2 = ReadingFeedService(store2, flaky)
    recovered = service2.retry_pending()
    assert [x.status for x in recovered] == ['fed']
    assert store2.count_notes(status='pending') == 0
    assert store2.load_state().entry_count == 1


def test_revision_conflict_recomputes_without_double_analysis(tmp_path):
    store, analyzer, service = make_service(tmp_path, store_cls=ConflictOnceStore)
    out = service.submit('race', '선택과 책임을 오래 고민했다.')
    assert out.status == 'fed'
    assert store.load_state().entry_count == 1
    assert analyzer.calls == 1


def test_non_mapping_analysis_degrades_to_neutral_meal(tmp_path):
    store, _, service = make_service(tmp_path, StaticAnalyzer(payload=['bad','shape']))
    out = service.submit('odd', '그냥 오늘 읽은 느낌을 남긴다.')
    assert out.status == 'fed'
    state = store.load_state()
    assert state.entry_count == 1
    assert state.stats == {}


def test_bookkeeping_note_cannot_mutate_hidden_traits_even_with_strong_fake_labels(tmp_path):
    payload = {
        'response':['사유'], 'world':['자연'],
        'scores':{'사유':.99,'자연':.99}, 'null':{'response':.80,'world':.80},
        'evidence':{'사유':3,'자연':3}, 'model_version':'fake-v1',
    }
    store, _, service = make_service(tmp_path, StaticAnalyzer(payload))
    service.submit('meta', 'ISBN 978-1-2345-6789-0이고 312쪽까지 읽었다.')
    state = store.load_state()
    assert state.stats == {}
    assert state.recent_stats == {}
    assert state.entry_count == 0


def test_sixteen_consistent_notes_reach_route_a_without_exposing_recipe(tmp_path):
    store, _, service = make_service(tmp_path)
    last = None
    for i in range(16):
        last = service.submit(f't{i}', f'이 선택이 옳은지 의미를 오래 생각했다. {i}')
    assert last is not None and last.growth is not None
    assert last.growth.stage == 1
    assert last.growth.species == 'Route A'
    assert store.load_state().form_id == 'route_a'
    public = json.dumps(last.to_public_dict(), ensure_ascii=False)
    for token in FORBIDDEN_PUBLIC_TOKENS:
        assert token not in public


def test_fifteen_consistent_notes_still_keep_starter(tmp_path):
    store, _, service = make_service(tmp_path)
    last = None
    for i in range(15):
        last = service.submit(f'pre{i}', f'이 선택이 옳은지 의미를 오래 생각했다. {i}')
    assert last is not None and last.growth is not None
    assert last.growth.stage == 0
    assert store.load_state().form_id == 'starter'


def test_public_receipt_has_strict_allow_list(tmp_path):
    _, _, service = make_service(tmp_path)
    out = service.submit('safe', '왜 그런 선택을 했는지 오래 생각했다.')
    payload = out.to_public_dict()
    assert set(payload) == {'feed_id','status','message','growth'}
    assert payload['growth'] is not None
    assert set(payload['growth']) == {
        'stage','species','visual_modifiers','tendency_hint','change_message'
    }
    blob = json.dumps(payload, ensure_ascii=False)
    for token in FORBIDDEN_PUBLIC_TOKENS:
        assert token not in blob


def test_reopen_preserves_state_and_cached_receipt(tmp_path):
    db = tmp_path / 'game.sqlite3'
    analyzer1 = StaticAnalyzer()
    service1 = ReadingFeedService(SQLiteGameStore(db), analyzer1)
    first = service1.submit('persist', '결말의 책임을 오래 생각했다.')

    analyzer2 = StaticAnalyzer()
    store2 = SQLiteGameStore(db)
    service2 = ReadingFeedService(store2, analyzer2)
    second = service2.submit('persist', '결말의 책임을 오래 생각했다.')
    assert first.to_public_dict() == second.to_public_dict()
    assert store2.load_state().entry_count == 1
    assert analyzer2.calls == 0


def test_blank_note_is_rejected_before_any_row_is_created(tmp_path):
    store, _, service = make_service(tmp_path)
    with pytest.raises(ValueError):
        service.submit('blank', '   ')
    assert store.count_notes() == 0


def test_many_neutral_notes_cross_all_count_gates_but_do_not_force_evolution(tmp_path):
    store, _, service = make_service(tmp_path, StaticAnalyzer(payload={}))
    for i in range(60):
        service.submit(f'n{i}', f'오늘 읽은 기록 {i}')
    state = store.load_state()
    assert state.entry_count == 60
    assert state.stats == {}
    assert state.current_base is None
    assert state.stage == 0
    assert state.form_id == 'starter'
    assert state.species == '글씨알'
