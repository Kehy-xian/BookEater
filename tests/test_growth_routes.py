from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.game.growth_routes import (
    FINAL_GROWTH_FORMS,
    GROWTH_FORMS,
    ROUTE_A,
    ROUTE_B,
    ROUTE_C,
    SECOND_GROWTH_ROUTES,
    STARTER_FORM,
    THIRD_GROWTH_FORMS,
    children_of,
    forms_at_tier,
    lineage_path,
    same_growth_tier,
    valid_direct_transition,
)


def test_route_a_b_c_are_equal_second_growth_siblings():
    assert {ROUTE_A.tier, ROUTE_B.tier, ROUTE_C.tier} == {1}
    assert same_growth_tier('route_a', 'route_b')
    assert same_growth_tier('route_b', 'route_c')
    assert set(SECOND_GROWTH_ROUTES) == {'route_a', 'route_b', 'route_c'}
    assert {ROUTE_A.parent_id, ROUTE_B.parent_id, ROUTE_C.parent_id} == {STARTER_FORM.form_id}


def test_second_growth_has_exactly_three_direct_branches():
    assert {x.form_id for x in children_of('starter')} == {'route_a', 'route_b', 'route_c'}
    for route in SECOND_GROWTH_ROUTES:
        assert valid_direct_transition('starter', route)


def test_every_second_growth_route_splits_into_two_third_growth_forms():
    for route in SECOND_GROWTH_ROUTES:
        children = children_of(route)
        assert len(children) == 2
        assert all(child.tier == 2 for child in children)
        assert all(valid_direct_transition(route, child.form_id) for child in children)


def test_every_third_growth_form_splits_into_two_final_forms():
    for form in THIRD_GROWTH_FORMS:
        children = children_of(form.form_id)
        assert len(children) == 2
        assert all(child.tier == 3 for child in children)
        assert all(valid_direct_transition(form.form_id, child.form_id) for child in children)


def test_full_tree_has_22_forms_and_12_final_forms():
    assert len(GROWTH_FORMS) == 22
    assert len(forms_at_tier(0)) == 1
    assert len(forms_at_tier(1)) == 3
    assert len(forms_at_tier(2)) == 6
    assert len(forms_at_tier(3)) == 12
    assert len(FINAL_GROWTH_FORMS) == 12


def test_siblings_are_never_sequential_evolutions():
    siblings = ('route_a', 'route_b', 'route_c')
    for left in siblings:
        for right in siblings:
            if left != right:
                assert not valid_direct_transition(left, right)


def test_final_lineage_is_four_forms_long_and_never_crosses_branch():
    for final in FINAL_GROWTH_FORMS:
        path = lineage_path(final.form_id)
        assert len(path) == 4
        assert path[0] == 'starter'
        assert path[-1] == final.form_id
        for source, target in zip(path, path[1:]):
            assert valid_direct_transition(source, target)
