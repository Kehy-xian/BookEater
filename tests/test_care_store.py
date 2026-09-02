from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.storage.care import MonsterCareStore
from bookeater.storage.sqlite_store import SQLiteGameStore


def test_care_actions_change_only_care_state(tmp_path):
    db = tmp_path / 'game.sqlite3'
    game = SQLiteGameStore(db)
    care = MonsterCareStore(db)
    before_growth = game.load_state()
    before_care = care.load()

    after = care.apply('snack')
    assert after.fullness > before_care.fullness
    assert after.bond >= before_care.bond
    assert game.load_state() == before_growth


def test_play_wash_and_minigame_are_bounded(tmp_path):
    db = tmp_path / 'game.sqlite3'
    care = MonsterCareStore(db)
    for _ in range(20):
        care.apply('play')
        care.apply('wash')
        care.apply('minigame')
    state = care.load()
    assert 0 <= state.mood <= 100
    assert 0 <= state.cleanliness <= 100
    assert 0 <= state.bond <= 100


def test_unknown_care_action_is_rejected():
    store = MonsterCareStore(':memory:')
    try:
        store.apply('evolve')
    except ValueError:
        pass
    else:
        raise AssertionError('care must never accept an evolution action')
