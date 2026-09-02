from __future__ import annotations

"""Fresh growth-profile holdout v3.

Authored after the A/B-before-C priority fix and after the new 15/16, 30/31, 54/55 count gates.
It checks boundary behavior plus conservative abstention at every growth tier. Do not tune against
this set and still call a rerun fresh.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.game.growth_route_resolver import resolve_growth_route


BROAD_CASES = [
    ('a301', 'route_a', {'사유': 4.0, '탐구': 2.3, '감정': 1.2, '감각': 0.5, '사회': 2.5, '자연': 2.2}),
    ('a302', 'route_a', {'사유': 2.0, '탐구': 4.1, '감정': 1.0, '감각': 0.4, '상상': 2.2, '모험': 2.0}),
    ('a303', 'route_a', {'사유': 3.6, '탐구': 1.7, '감정': 1.4, '감각': 0.6}),
    ('b301', 'route_b', {'감정': 4.0, '감각': 2.3, '사유': 1.2, '탐구': 0.5, '어둠': 2.5, '사회': 2.2}),
    ('b302', 'route_b', {'감정': 2.0, '감각': 4.1, '사유': 1.0, '탐구': 0.4, '자연': 2.2, '모험': 2.0}),
    ('b303', 'route_b', {'감정': 3.6, '감각': 1.7, '사유': 1.4, '탐구': 0.6}),
    ('c301', 'route_c', {'사유': 2.2, '탐구': 1.5, '감정': 2.3, '감각': 1.4}),
    ('c302', 'route_c', {'사유': 1.6, '탐구': 1.7, '감정': 1.8, '감각': 1.7, '사회': 1.1}),
    ('c303', 'route_c', {'사유': 0.9, '감정': 0.8, '상상': 3.4, '자연': 2.8, '사회': 1.7}),
    ('d301', 'starter', {'사유': 1.6, '탐구': 1.3, '감정': 1.5, '감각': 1.2}),
    ('d302', 'starter', {'사유': 2.3, '탐구': 0.5, '감정': 2.2, '감각': 0.5}),
    ('d303', 'starter', {'사유': 0.6, '감정': 0.6, '상상': 1.7, '사회': 1.6}),
]


def check_broad() -> list[tuple]:
    wrong = []
    for case_id, expected, stats in BROAD_CASES:
        got = resolve_growth_route(stats, 16).form_id
        if got != expected:
            wrong.append((case_id, expected, got, stats))
    return wrong


def check_boundaries() -> list[tuple]:
    wrong = []
    strong_a = {'사유': 12, '탐구': 5, '감정': 1, '감각': 1}
    cases = [
        ('gate15', 'starter', resolve_growth_route(strong_a, 15).form_id),
        ('gate16', 'route_a', resolve_growth_route(strong_a, 16).form_id),
        ('gate30', 'route_a', resolve_growth_route(strong_a, 30).form_id),
        ('gate31', 'route_a1', resolve_growth_route(strong_a, 31, current_form='route_a').form_id),
        ('gate54', 'route_a1', resolve_growth_route(strong_a, 54, current_form='route_a1').form_id),
        ('gate55', 'route_a1_alpha', resolve_growth_route(
            strong_a, 55, current_form='route_a1', recent_stats={'사유': 7, '탐구': 1}
        ).form_id),
    ]
    for case_id, expected, got in cases:
        if got != expected:
            wrong.append((case_id, expected, got))
    return wrong


def check_subroutes_and_holds() -> list[tuple]:
    wrong = []
    cases = [
        ('a1', 'route_a1', resolve_growth_route(
            {'사유': 10, '탐구': 4, '감정': 1}, 31, current_form='route_a'
        ).form_id),
        ('a_hold', 'route_a', resolve_growth_route(
            {'사유': 7, '탐구': 7, '감정': 1}, 31, current_form='route_a'
        ).form_id),
        ('b2', 'route_b2', resolve_growth_route(
            {'감정': 4, '감각': 10, '사유': 1}, 31, current_form='route_b'
        ).form_id),
        ('b_hold', 'route_b', resolve_growth_route(
            {'감정': 7, '감각': 7, '사유': 1}, 31, current_form='route_b'
        ).form_id),
        ('c1', 'route_c1', resolve_growth_route(
            {'사유': 6, '탐구': 5, '감정': 5, '감각': 2, '상상': 1}, 31, current_form='route_c'
        ).form_id),
        ('c2', 'route_c2', resolve_growth_route(
            {'사유': 1.5, '감정': 1.5, '상상': 5, '사회': 4.5, '자연': 4}, 31, current_form='route_c'
        ).form_id),
        ('c_hold', 'route_c', resolve_growth_route(
            {'사유': 2, '감정': 2, '상상': 2, '사회': 2}, 31, current_form='route_c'
        ).form_id),
    ]
    for case_id, expected, got in cases:
        if got != expected:
            wrong.append((case_id, expected, got))
    return wrong


def check_finals_and_holds() -> list[tuple]:
    wrong = []
    cases = [
        ('alpha', 'route_a1_alpha', resolve_growth_route(
            {'사유': 24, '탐구': 7, '감정': 2, '감각': 1, '사회': 3},
            55, current_form='route_a1', recent_stats={'사유': 8, '탐구': 2}
        ).form_id),
        ('beta', 'route_b1_beta', resolve_growth_route(
            {'감정': 23, '감각': 7, '사유': 2, '탐구': 1, '자연': 3},
            55, current_form='route_b1', recent_stats={'사유': 3, '탐구': 3, '상상': 3, '모험': 2}
        ).form_id),
        ('final_hold_sparse', 'route_a2', resolve_growth_route(
            {'탐구': 24, '사유': 7, '감정': 2},
            55, current_form='route_a2', recent_stats={}
        ).form_id),
        ('final_hold_ambiguous', 'route_a1', resolve_growth_route(
            {'사유': 10, '탐구': 8, '감정': 7, '감각': 6, '사회': 3},
            55, current_form='route_a1', recent_stats={'사유': 3, '탐구': 2.5, '감정': 2.4, '감각': 2.2}
        ).form_id),
    ]
    for case_id, expected, got in cases:
        if got != expected:
            wrong.append((case_id, expected, got))
    return wrong


def main() -> int:
    groups = {
        'broad': check_broad(),
        'boundaries': check_boundaries(),
        'subroutes': check_subroutes_and_holds(),
        'finals': check_finals_and_holds(),
    }
    total_cases = len(BROAD_CASES) + 6 + 7 + 4
    wrong = sum((rows for rows in groups.values()), [])
    passed = total_cases - len(wrong)
    print('FRESH_GROWTH_PROFILE_BLIND_V3')
    print(f'accuracy={passed/total_cases:.3f} ({passed}/{total_cases})')
    for name, rows in groups.items():
        print(f'{name}_wrong={len(rows)}')
        for row in rows:
            print(name, row)
    ok = not wrong
    print('PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
