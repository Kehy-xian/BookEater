from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.game.encyclopedia_view import build_encyclopedia_rows


def test_starter_only_reveals_three_immediate_unknown_possibilities():
    rows = build_encyclopedia_rows({'starter'}, current_form='starter')
    assert [row.form_id for row in rows] == ['starter', 'route_a', 'route_b', 'route_c']
    assert [row.name for row in rows[1:]] == ['???', '???', '???']


def test_evolved_route_hides_siblings_and_only_reveals_its_next_children():
    rows = build_encyclopedia_rows({'starter', 'route_a'}, current_form='route_a')
    assert [row.form_id for row in rows] == ['starter', 'route_a', 'route_a1', 'route_a2']
    assert all(row.form_id not in {'route_b', 'route_c'} for row in rows)


def test_deeper_route_shows_lineage_and_only_one_step_ahead():
    rows = build_encyclopedia_rows(
        {'starter', 'route_a', 'route_a2'}, current_form='route_a2',
    )
    assert [row.form_id for row in rows] == [
        'starter', 'route_a', 'route_a2', 'route_a2_alpha', 'route_a2_beta',
    ]
