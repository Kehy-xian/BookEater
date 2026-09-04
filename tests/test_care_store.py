from pathlib import Path
from datetime import date, timedelta
import sqlite3
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


def test_bond_gain_is_limited_to_five_per_day(tmp_path):
    today = [date(2026, 9, 4)]
    care = MonsterCareStore(tmp_path / 'game.sqlite3', today=lambda: today[0])
    for _ in range(10):
        care.apply('minigame')
    assert care.load().bond == 5
    today[0] += timedelta(days=1)
    assert care.apply('minigame').bond == 8


def test_bond_loses_two_per_fully_missed_day_after_grace_day(tmp_path):
    today = [date(2026, 9, 4)]
    care = MonsterCareStore(tmp_path / 'game.sqlite3', today=lambda: today[0])
    care.apply('minigame')
    care.apply('play')
    assert care.load().bond == 5
    today[0] += timedelta(days=1)
    assert care.load().bond == 5
    today[0] += timedelta(days=1)
    assert care.load().bond == 3
    assert care.load().bond == 3


def test_existing_care_table_migrates_without_losing_values(tmp_path):
    db = tmp_path / 'legacy.sqlite3'
    con = sqlite3.connect(db)
    con.executescript(
        """
        CREATE TABLE monster_care (
            singleton INTEGER PRIMARY KEY,
            fullness INTEGER NOT NULL,
            mood INTEGER NOT NULL,
            cleanliness INTEGER NOT NULL,
            bond INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        );
        INSERT INTO monster_care VALUES(1,60,61,62,37,CURRENT_TIMESTAMP);
        """
    )
    con.commit()
    con.close()

    care = MonsterCareStore(db, today=lambda: date(2026, 9, 4))
    assert care.load().bond == 37
    con = sqlite3.connect(db)
    columns = {row[1] for row in con.execute('PRAGMA table_info(monster_care)')}
    con.close()
    assert {'bond_gain_date', 'bond_gain_today', 'last_cared_date', 'last_decay_date'} <= columns
