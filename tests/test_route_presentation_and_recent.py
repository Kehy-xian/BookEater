from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.game.growth_route_resolver import GrowthRouteDecision, resolve_growth_route
from bookeater.game.loop import update_recent_signature
from bookeater.game.nutrition import GrowthNutrition
from bookeater.game.route_presentation import route_public_growth_view, world_motifs


def test_world_axes_become_sparse_motifs_not_species():
    stats = {'사유': 8, '탐구': 4, '자연': 6, '사회': 5}
    decision = GrowthRouteDecision('route_a', 1, False, 'test')
    view = route_public_growth_view(decision, stats, previous_form='route_a')
    assert view.species == 'Route A'
    assert set(view.visual_modifiers) == {'잎결', '창문무늬'}
    assert '자연' not in view.species and '사회' not in view.species


def test_weak_world_signal_does_not_force_a_motif():
    assert world_motifs({'상상': 2.9, '사유': 7}, tier=2) == ()


def test_recent_signature_fades_old_axes_and_adds_new_meal():
    previous = {'사유': 5.0, '탐구': 2.0}
    meal = GrowthNutrition(response={'감정': 1.0}, world={'상상': 0.65})
    recent = update_recent_signature(previous, meal, decay=0.5)
    assert recent['사유'] == 2.5
    assert recent['탐구'] == 1.0
    assert recent['감정'] == 1.0
    assert recent['상상'] == 0.65


def test_final_route_can_broaden_when_recent_signature_changes():
    cumulative = {'사유': 24, '탐구': 7, '감정': 3, '감각': 2, '사회': 4}
    recent = {'감정': 4, '감각': 3, '상상': 3, '자연': 2, '사유': 1}
    d = resolve_growth_route(
        cumulative, 45, recent_stats=recent, current_form='route_a1'
    )
    assert d.form_id == 'route_a1_beta'


def test_final_route_deepens_when_recent_signature_stays_focused():
    cumulative = {'사유': 24, '탐구': 7, '감정': 3, '감각': 2, '사회': 4}
    recent = {'사유': 7, '탐구': 2, '사회': 1}
    d = resolve_growth_route(
        cumulative, 45, recent_stats=recent, current_form='route_a1'
    )
    assert d.form_id == 'route_a1_alpha'
