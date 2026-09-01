from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.game.growth_routes import (
    ROUTE_A,
    ROUTE_B,
    SECOND_GROWTH_ROUTES,
    STARTER_FORM,
    same_growth_tier,
    valid_direct_transition,
)


def test_route_a_and_b_are_same_second_growth_tier():
    assert ROUTE_A.tier == 1
    assert ROUTE_B.tier == 1
    assert same_growth_tier('route_a', 'route_b')
    assert set(SECOND_GROWTH_ROUTES) == {'route_a', 'route_b'}


def test_both_routes_branch_directly_from_starter():
    assert ROUTE_A.parent_id == STARTER_FORM.form_id
    assert ROUTE_B.parent_id == STARTER_FORM.form_id
    assert valid_direct_transition('starter', 'route_a')
    assert valid_direct_transition('starter', 'route_b')


def test_routes_are_not_sequential_evolutions():
    assert not valid_direct_transition('route_a', 'route_b')
    assert not valid_direct_transition('route_b', 'route_a')
