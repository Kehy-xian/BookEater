from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.game.loop import ReadingFeedService
from bookeater.storage.encyclopedia import MonsterEncyclopediaStore
from bookeater.storage.sqlite_store import SQLiteGameStore


class ThoughtAnalyzer:
    def analyze(self, _text):
        return {
            'response': ['사유'],
            'world': [],
            'scores': {'사유': .95},
            'null': {'response': .80, 'world': .80},
            'evidence': {'사유': 2},
            'model_version': 'test',
        }


def test_fed_records_persist_and_unlock_route_lineage(tmp_path):
    db = tmp_path / 'game.sqlite3'
    store = SQLiteGameStore(db)
    encyclopedia = MonsterEncyclopediaStore(db)
    service = ReadingFeedService(store, ThoughtAnalyzer(), encyclopedia=encyclopedia)

    for i in range(16):
        service.submit(f'n{i}', f'이 선택의 의미를 오래 생각했다 {i}')

    state = store.load_state()
    assert state.form_id == 'route_a'
    assert encyclopedia.encountered_ids() >= {'starter', 'route_a'}
    assert 'route_b' not in encyclopedia.encountered_ids()


def test_existing_database_gets_form_id_without_losing_state(tmp_path):
    db = tmp_path / 'legacy.sqlite3'
    con = sqlite3.connect(db)
    con.executescript(
        """
        CREATE TABLE monster_state (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            revision INTEGER NOT NULL DEFAULT 0,
            entry_count INTEGER NOT NULL DEFAULT 0,
            current_base TEXT,
            stage INTEGER NOT NULL DEFAULT 0,
            species TEXT NOT NULL DEFAULT '글씨알',
            stats_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE reading_entries (
            feed_id TEXT PRIMARY KEY,
            note_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            public_json TEXT,
            model_version TEXT,
            nutrition_policy TEXT,
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            fed_at TEXT
        );
        INSERT INTO monster_state(singleton,revision,entry_count,species,stats_json)
        VALUES(1,7,12,'생각콩','{"사유":9}');
        """
    )
    con.commit(); con.close()

    store = SQLiteGameStore(db)
    state = store.load_state()
    assert state.revision == 7
    assert state.entry_count == 12
    assert state.species == '생각콩'
    assert state.stats == {'사유': 9.0}
    assert state.form_id == 'starter'
