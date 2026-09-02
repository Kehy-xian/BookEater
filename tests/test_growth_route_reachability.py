from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.game.growth_route_resolver import resolve_growth_route
from bookeater.game.growth_routes import THIRD_GROWTH_FORMS


def test_all_six_second_evolution_forms_are_reachable():
    cases = {
        'route_a1': {'사유': 12, '탐구': 4, '감정': 1, '감각': 1},
        'route_a2': {'사유': 4, '탐구': 12, '감정': 1, '감각': 1},
        'route_b1': {'사유': 1, '탐구': 1, '감정': 12, '감각': 4},
        'route_b2': {'사유': 1, '탐구': 1, '감정': 4, '감각': 12},
        'route_c1': {'사유': 8, '탐구': 7, '감정': 7, '감각': 2, '상상': 1},
        'route_c2': {'사유': 2, '감정': 2, '상상': 7, '사회': 6, '자연': 5},
    }
    reached = set()
    for expected, stats in cases.items():
        parent = expected[:7]
        d = resolve_growth_route(stats, 40, current_form=parent)
        reached.add(d.form_id)
        assert d.form_id == expected
    assert reached == set(cases)


def test_every_second_evolution_form_has_reachable_alpha_and_beta_final():
    for form in THIRD_GROWTH_FORMS:
        cumulative = {
            '사유': 12, '탐구': 5, '감정': 4, '감각': 2,
            '상상': 3, '사회': 2,
        }
        alpha = resolve_growth_route(
            cumulative,
            60,
            current_form=form.form_id,
            recent_stats={'사유': 7, '탐구': 1},
        )
        beta = resolve_growth_route(
            cumulative,
            60,
            current_form=form.form_id,
            recent_stats={'감정': 3, '감각': 3, '상상': 3, '자연': 2, '모험': 2},
        )
        assert alpha.form_id == f'{form.form_id}_alpha'
        assert beta.form_id == f'{form.form_id}_beta'
