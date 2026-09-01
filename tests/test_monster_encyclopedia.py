from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.storage.sqlite_store import SQLiteGameStore
from bookeater.storage.encyclopedia import MonsterEncyclopediaStore
from bookeater.game.encyclopedia import encyclopedia_form


def test_only_starter_is_unlocked_for_new_profile(tmp_path):
    db = tmp_path / 'bookeater.sqlite3'
    SQLiteGameStore(db)
    dex = MonsterEncyclopediaStore(db)
    assert dex.encountered_ids() == frozenset({'starter'})
    assert dex.encountered('route_a') is None
    assert dex.encountered('route_b') is None


def test_route_unlock_is_idempotent_and_does_not_unlock_sibling(tmp_path):
    db = tmp_path / 'bookeater.sqlite3'
    SQLiteGameStore(db)
    dex = MonsterEncyclopediaStore(db)
    first = dex.unlock('route_a')
    second = dex.unlock('route_a')
    assert first.first_seen_at == second.first_seen_at
    assert dex.encountered_ids() == frozenset({'starter', 'route_a'})
    assert dex.encountered('route_b') is None


def test_player_copy_is_one_line_and_contains_no_debug_recipe_terms():
    forbidden = {'threshold', 'confidence', 'keyword', 'score', '사유', '탐구', '감정', '감각'}
    for form_id in ('starter', 'route_a', 'route_b'):
        item = encyclopedia_form(form_id)
        assert item.hint.strip()
        assert '\n' not in item.hint
        lowered = item.hint.lower()
        assert all(term not in lowered for term in forbidden)
