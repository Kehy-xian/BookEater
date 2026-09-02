from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.game.growth_route_resolver import resolve_growth_route


def test_sparse_signal_does_not_force_second_growth():
    d = resolve_growth_route({'사유': 1.0, '감정': 0.5}, 8)
    assert d.form_id == 'starter'
    assert d.delayed


def test_route_a_for_clear_thinking_inquiry_cluster():
    d = resolve_growth_route({'사유': 7, '탐구': 5, '감정': 1, '감각': 1}, 8)
    assert d.form_id == 'route_a'
    assert d.tier == 1


def test_route_b_for_clear_emotion_sensation_cluster():
    d = resolve_growth_route({'사유': 1, '탐구': 1, '감정': 7, '감각': 5}, 8)
    assert d.form_id == 'route_b'
    assert d.tier == 1


def test_route_c_requires_positive_complexity_not_ambiguity():
    d = resolve_growth_route({'사유': 5, '탐구': 3, '감정': 5, '감각': 3}, 8)
    assert d.form_id == 'route_c'
    assert d.tier == 1


def test_route_c_can_be_driven_by_connected_world_profile():
    d = resolve_growth_route({'사유': 1, '감정': 1, '사회': 5, '어둠': 4, '상상': 3}, 8)
    assert d.form_id == 'route_c'


def test_route_a_splits_third_growth_by_sayou_vs_tamgu():
    d1 = resolve_growth_route({'사유': 11, '탐구': 5, '감정': 1, '감각': 1}, 20)
    d2 = resolve_growth_route({'사유': 4, '탐구': 11, '감정': 1, '감각': 1}, 20)
    assert d1.form_id == 'route_a1'
    assert d2.form_id == 'route_a2'


def test_route_b_splits_third_growth_by_emotion_vs_sensation():
    d1 = resolve_growth_route({'사유': 1, '탐구': 1, '감정': 11, '감각': 5}, 20)
    d2 = resolve_growth_route({'사유': 1, '탐구': 1, '감정': 4, '감각': 11}, 20)
    assert d1.form_id == 'route_b1'
    assert d2.form_id == 'route_b2'


def test_tied_subroute_waits_at_second_growth():
    d = resolve_growth_route({'사유': 7, '탐구': 7, '감정': 1, '감각': 1}, 20)
    assert d.form_id == 'route_a'
    assert d.delayed


def test_final_alpha_deepens_stable_signature():
    cumulative = {'사유': 22, '탐구': 7, '감정': 2, '감각': 1, '사회': 4}
    recent = {'사유': 9, '탐구': 2, '사회': 1}
    d = resolve_growth_route(cumulative, 45, recent_stats=recent)
    assert d.form_id == 'route_a1_alpha'
    assert d.tier == 3


def test_final_beta_broadens_signature():
    cumulative = {'사유': 22, '탐구': 7, '감정': 2, '감각': 1, '사회': 4}
    recent = {'사유': 3, '감정': 4, '감각': 3, '상상': 3, '자연': 2}
    d = resolve_growth_route(cumulative, 45, recent_stats=recent)
    assert d.form_id == 'route_a1_beta'
    assert d.tier == 3


def test_established_route_cannot_flip_to_sibling_route():
    # This later snapshot would normally look like Route B, but an already encountered A remains A.
    d = resolve_growth_route(
        {'사유': 2, '탐구': 2, '감정': 14, '감각': 10},
        12,
        current_form='route_a',
    )
    assert d.form_id == 'route_a'


def test_established_third_growth_only_advances_to_its_own_child():
    d = resolve_growth_route(
        {'사유': 2, '탐구': 15, '감정': 20, '감각': 20, '상상': 4},
        45,
        current_form='route_a1',
        recent_stats={'감정': 5, '감각': 5, '상상': 4},
    )
    assert d.form_id in {'route_a1_alpha', 'route_a1_beta'}


def test_final_form_never_rewrites_after_more_records():
    d = resolve_growth_route(
        {'감정': 100, '감각': 100},
        100,
        current_form='route_a1_alpha',
    )
    assert d.form_id == 'route_a1_alpha'
