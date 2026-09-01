from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.storage.sqlite_store import SQLiteGameStore
from bookeater.storage.milestones import MonsterMilestoneStore


def test_new_profile_has_meeting_date_and_no_first_feed(tmp_path):
    db = tmp_path / 'bookeater.sqlite3'
    SQLiteGameStore(db)
    milestones = MonsterMilestoneStore(db).load()
    assert milestones.met_at
    assert milestones.first_fed_at is None


def test_legacy_profile_backfills_meeting_date_from_earliest_note(tmp_path):
    db = tmp_path / 'legacy.sqlite3'
    SQLiteGameStore(db)
    con = sqlite3.connect(db)
    con.execute(
        "INSERT INTO reading_entries(feed_id,note_text,created_at) VALUES('old','기록','2024-03-04 05:06:07')"
    )
    con.commit(); con.close()

    milestones = MonsterMilestoneStore(db).load()
    assert milestones.met_at == '2024-03-04 05:06:07'


def test_first_fed_date_is_derived_from_actual_consumed_records(tmp_path):
    db = tmp_path / 'fed.sqlite3'
    SQLiteGameStore(db)
    con = sqlite3.connect(db)
    con.execute(
        "INSERT INTO reading_entries(feed_id,note_text,status,created_at,fed_at) "
        "VALUES('a','첫 기록','fed','2025-01-02 00:00:00','2025-01-02 09:10:11')"
    )
    con.execute(
        "INSERT INTO reading_entries(feed_id,note_text,status,created_at,fed_at) "
        "VALUES('b','둘째 기록','fed','2025-01-03 00:00:00','2025-01-03 09:10:11')"
    )
    con.commit(); con.close()

    milestones = MonsterMilestoneStore(db).load()
    assert milestones.first_fed_at == '2025-01-02 09:10:11'


def test_meeting_date_does_not_change_when_store_reopens(tmp_path):
    db = tmp_path / 'stable.sqlite3'
    SQLiteGameStore(db)
    first = MonsterMilestoneStore(db).load().met_at
    second = MonsterMilestoneStore(db).load().met_at
    assert first == second
