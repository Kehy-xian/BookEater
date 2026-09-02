from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.game.growth_route_resolver import (
    FINAL_MIN_RECORDS,
    TIER1_MIN_RECORDS,
    TIER2_MIN_RECORDS,
    resolve_growth_route,
)


def test_count_gate_boundaries_are_15_16_30_31_54_55():
    strong_a = {'사유': 12, '탐구': 5, '감정': 1, '감각': 1}
    assert resolve_growth_route(strong_a, 15).form_id == 'starter'
    assert resolve_growth_route(strong_a, 16).form_id == 'route_a'
    assert resolve_growth_route(strong_a, 30).form_id == 'route_a'
    assert resolve_growth_route(strong_a, 31).form_id == 'route_a1'
    assert resolve_growth_route(strong_a, 54).form_id == 'route_a1'
    final = resolve_growth_route(
        strong_a,
        55,
        current_form='route_a1',
        recent_stats={'사유': 7, '탐구': 1},
    )
    assert final.form_id == 'route_a1_alpha'
    assert (TIER1_MIN_RECORDS, TIER2_MIN_RECORDS, FINAL_MIN_RECORDS) == (16, 31, 55)


def test_sparse_signal_does_not_force_first_growth_even_after_gate_opens():
    d = resolve_growth_route({'사유': 1.0, '감정': 0.5}, 20)
    assert d.form_id == 'starter'
    assert d.delayed


def test_route_a_for_clear_thinking_inquiry_cluster():
    d = resolve_growth_route({'사유': 7, '탐구': 5, '감정': 1, '감각': 1}, 20)
    assert d.form_id == 'route_a'
    assert d.tier == 1


def test_route_b_for_clear_emotion_sensation_cluster():
    d = resolve_growth_route({'사유': 1, '탐구': 1, '감정': 7, '감각': 5}, 20)
    assert d.form_id == 'route_b'
    assert d.tier == 1


def test_route_c_requires_positive_complexity_not_ambiguity():
    d = resolve_growth_route({'사유': 5, '탐구': 3, '감정': 5, '감각': 3}, 20)
    assert d.form_id == 'route_c'
    assert d.tier == 1


def test_route_c_can_be_driven_by_connected_world_profile():
    d = resolve_growth_route({'사유': 1, '감정': 1, '사회': 5, '어둠': 4, '상상': 3}, 20)
    assert d.form_id == 'route_c'


def test_route_a_splits_second_evolution_by_sayou_vs_tamgu():
    d1 = resolve_growth_route({'사유': 11, '탐구': 5, '감정': 1, '감각': 1}, 40)
    d2 = resolve_growth_route({'사유': 4, '탐구': 11, '감정': 1, '감각': 1}, 40)
    assert d1.form_id == 'route_a1'
    assert d2.form_id == 'route_a2'


def test_route_b_splits_second_evolution_by_emotion_vs_sensation():
    d1 = resolve_growth_route({'사유': 1, '탐구': 1, '감정': 11, '감각': 5}, 40)
    d2 = resolve_growth_route({'사유': 1, '탐구': 1, '감정': 4, '감각': 11}, 40)
    assert d1.form_id == 'route_b1'
    assert d2.form_id == 'route_b2'


def test_tied_subroute_waits_at_first_evolution():
    d = resolve_growth_route({'사유': 7, '탐구': 7, '감정': 1, '감각': 1}, 40)
    assert d.form_id == 'route_a'
    assert d.delayed


def test_final_alpha_deepens_stable_signature():
    cumulative = {'사유': 22, '탐구': 7, '감정': 2, '감각': 1, '사회': 4}
    recent = {'사유': 9, '탐구': 2, '사회': 1}
    d = resolve_growth_route(cumulative, 60, current_form='route_a1', recent_stats=recent)
    assert d.form_id == 'route_a1_alpha'
    assert d.tier == 3


def test_final_beta_broadens_signature():
    cumulative = {'사유': 22, '탐구': 7, '감정': 2, '감각': 1, '사회': 4}
    recent = {'사유': 3, '감정': 4, '감각': 3, '상상': 3, '자연': 2}
    d = resolve_growth_route(cumulative, 60, current_form='route_a1', recent_stats=recent)
    assert d.form_id == 'route_a1_beta'
    assert d.tier == 3


def test_final_does_not_force_alpha_or_beta_when_recent_signal_missing():
    cumulative = {'사유': 22, '탐구': 7, '감정': 2, '감각': 1}
    d = resolve_growth_route(cumulative, 60, current_form='route_a1', recent_stats={})
    assert d.form_id == 'route_a1'
    assert d.delayed


def test_final_does_not_force_alpha_or_beta_when_recent_trajectory_is_ambiguous():
    cumulative = {'사유': 10, '탐구': 8, '감정': 7, '감각': 6, '사회': 3}
    recent = {'사유': 3, '탐구': 2.5, '감정': 2.4, '감각': 2.2}
    d = resolve_growth_route(cumulative, 60, current_form='route_a1', recent_stats=recent)
    assert d.form_id == 'route_a1'
    assert d.delayed


def test_existing_evolved_form_does_not_regress_after_threshold_update():
    # A user who already evolved under an older build keeps that encountered lineage.
    d = resolve_growth_route({'사유': 5, '탐구': 2}, 10, current_form='route_a')
    assert d.form_id == 'route_a'
    assert d.tier == 1


def test_established_route_cannot_flip_to_sibling_route():
    d = resolve_growth_route(
        {'사유': 2, '탐구': 2, '감정': 14, '감각': 10},
        25,
        current_form='route_a',
    )
    assert d.form_id == 'route_a'


def test_established_second_evolution_only_advances_to_its_own_child():
    d = resolve_growth_route(
        {'사유': 2, '탐구': 15, '감정': 20, '감각': 20, '상상': 4},
        60,
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
