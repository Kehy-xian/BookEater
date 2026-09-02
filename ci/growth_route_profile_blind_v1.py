from __future__ import annotations

"""Fresh holdout for the A/B/C growth resolver.

Authored after the recent-signature/public-lineage fix was frozen. This validates user-level
aggregate reading profiles, not sentence classification. Do not tune against this file and call a
rerun fresh; after any resolver change, reruns are diagnostic and a new blind set is required.
"""

from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.game.growth_route_resolver import resolve_growth_route


# Broad-route profiles at the first eligible growth window. Values represent only accepted hidden
# nutrition accumulated from several notes; they are intentionally near and far from boundaries.
BROAD = [
    # Expected A: thinking/inquiry cluster leads, including realistic small side reactions.
    ('a01', 'route_a', {'사유': 3.4, '탐구': 1.4, '감정': 0.6}),
    ('a02', 'route_a', {'사유': 2.9, '탐구': 1.5, '감각': 0.8}),
    ('a03', 'route_a', {'사유': 3.0, '탐구': 1.2, '감정': 1.1}),
    ('a04', 'route_a', {'사유': 1.5, '탐구': 3.2, '감각': 0.9}),
    ('a05', 'route_a', {'사유': 1.3, '탐구': 3.0, '감정': 0.8, '감각': 0.4}),
    ('a06', 'route_a', {'사유': 2.7, '탐구': 2.0, '감정': 1.0, '상상': 1.2}),
    ('a07', 'route_a', {'사유': 4.0, '탐구': 0.9, '감정': 1.2, '사회': 1.5}),
    ('a08', 'route_a', {'사유': 1.0, '탐구': 4.1, '감각': 1.15, '자연': 1.3}),

    # Expected B: emotion/sensory cluster leads, also with small cognitive spillover.
    ('b01', 'route_b', {'감정': 3.4, '감각': 1.4, '사유': 0.6}),
    ('b02', 'route_b', {'감정': 2.9, '감각': 1.5, '탐구': 0.8}),
    ('b03', 'route_b', {'감정': 3.0, '감각': 1.2, '사유': 1.1}),
    ('b04', 'route_b', {'감정': 1.5, '감각': 3.2, '사유': 0.9}),
    ('b05', 'route_b', {'감정': 1.3, '감각': 3.0, '탐구': 0.8, '사유': 0.4}),
    ('b06', 'route_b', {'감정': 2.7, '감각': 2.0, '사유': 1.0, '어둠': 1.2}),
    ('b07', 'route_b', {'감정': 4.0, '감각': 0.9, '사유': 1.2, '사회': 1.5}),
    ('b08', 'route_b', {'감정': 1.0, '감각': 4.1, '탐구': 1.15, '자연': 1.3}),

    # Expected C: genuinely mixed response styles or strongly connected multi-world profile.
    ('c01', 'route_c', {'사유': 2.8, '탐구': 1.2, '감정': 2.6, '감각': 1.1}),
    ('c02', 'route_c', {'사유': 2.2, '탐구': 1.4, '감정': 1.9, '감각': 1.5}),
    ('c03', 'route_c', {'사유': 1.8, '탐구': 1.3, '감정': 1.7, '감각': 1.4}),
    ('c04', 'route_c', {'사유': 1.0, '감정': 1.0, '상상': 3.0, '사회': 2.8, '어둠': 1.7}),
    ('c05', 'route_c', {'탐구': 1.2, '감각': 0.9, '자연': 3.2, '사회': 2.7, '모험': 1.4}),
    ('c06', 'route_c', {'사유': 1.5, '감정': 1.4, '상상': 2.7, '모험': 2.6, '사회': 2.4}),
    ('c07', 'route_c', {'사유': 2.4, '탐구': 1.5, '감정': 2.3, '감각': 1.4, '자연': 1.2}),
    ('c08', 'route_c', {'사유': 1.6, '탐구': 1.5, '감정': 1.6, '감각': 1.5, '상상': 1.4}),

    # Expected delay: enough notes but evidence is sparse or a narrow two-cluster tie without a
    # genuinely developed mixed profile.
    ('d01', 'starter', {'사유': 1.2, '감정': 0.7}),
    ('d02', 'starter', {'탐구': 1.4, '감각': 0.9}),
    ('d03', 'starter', {'사유': 2.0, '감정': 1.9}),
    ('d04', 'starter', {'탐구': 2.1, '감각': 2.0}),
    ('d05', 'starter', {'사유': 1.4, '탐구': 0.6, '감정': 1.3, '감각': 0.6}),
    ('d06', 'starter', {'사유': 0.8, '감정': 0.8, '상상': 1.2, '사회': 1.0}),
    ('d07', 'starter', {'사유': 2.2, '탐구': 0.4, '감정': 2.1, '감각': 0.4}),
    ('d08', 'starter', {'사유': 1.0, '탐구': 1.0, '감정': 1.0, '감각': 0.9}),
]

# Tier-2 checks use an already established broad lineage so later records cannot rewrite siblings.
SUB = [
    ('a1-1', 'route_a1', 'route_a', {'사유': 8.0, '탐구': 4.0, '감정': 2.0}),
    ('a1-2', 'route_a1', 'route_a', {'사유': 6.2, '탐구': 3.9, '감각': 2.0}),
    ('a2-1', 'route_a2', 'route_a', {'사유': 3.8, '탐구': 7.5, '감정': 2.1}),
    ('a2-2', 'route_a2', 'route_a', {'사유': 4.0, '탐구': 6.4, '감각': 2.2}),
    ('b1-1', 'route_b1', 'route_b', {'감정': 8.0, '감각': 4.0, '사유': 2.0}),
    ('b1-2', 'route_b1', 'route_b', {'감정': 6.2, '감각': 3.9, '탐구': 2.0}),
    ('b2-1', 'route_b2', 'route_b', {'감정': 3.8, '감각': 7.5, '사유': 2.1}),
    ('b2-2', 'route_b2', 'route_b', {'감정': 4.0, '감각': 6.4, '탐구': 2.2}),
    ('c1-1', 'route_c1', 'route_c', {'사유': 6, '탐구': 5, '감정': 5, '감각': 2, '상상': 1}),
    ('c1-2', 'route_c1', 'route_c', {'사유': 5, '탐구': 4, '감정': 5, '감각': 3, '사회': 1}),
    ('c2-1', 'route_c2', 'route_c', {'사유': 2, '감정': 2, '상상': 6, '사회': 5, '자연': 4}),
    ('c2-2', 'route_c2', 'route_c', {'탐구': 2, '감각': 2, '모험': 6, '자연': 5, '어둠': 4}),
]

# Final trajectory checks: each established tier-2 parent gets a focused and broad recent profile.
FINAL_PARENTS = ('route_a1', 'route_a2', 'route_b1', 'route_b2', 'route_c1', 'route_c2')


def main() -> int:
    wrong = []
    confusion = Counter()
    by_expected = defaultdict(lambda: [0, 0])

    for case_id, expected, stats in BROAD:
        got = resolve_growth_route(stats, 8).form_id
        by_expected[expected][1] += 1
        if got == expected:
            by_expected[expected][0] += 1
        else:
            wrong.append((case_id, expected, got, stats))
        confusion[(expected, got)] += 1

    broad_correct = sum(v[0] for v in by_expected.values())
    broad_total = sum(v[1] for v in by_expected.values())
    broad_acc = broad_correct / broad_total

    sub_wrong = []
    for case_id, expected, current, stats in SUB:
        got = resolve_growth_route(stats, 20, current_form=current).form_id
        if got != expected:
            sub_wrong.append((case_id, expected, got))

    final_wrong = []
    cumulative = {'사유': 12, '탐구': 8, '감정': 6, '감각': 4, '상상': 3, '사회': 2}
    for parent in FINAL_PARENTS:
        alpha = resolve_growth_route(
            cumulative, 45, current_form=parent,
            recent_stats={'사유': 7, '탐구': 2},
        ).form_id
        beta = resolve_growth_route(
            cumulative, 45, current_form=parent,
            recent_stats={'감정': 3, '감각': 3, '상상': 3, '자연': 2, '모험': 2},
        ).form_id
        if alpha != f'{parent}_alpha':
            final_wrong.append((parent, 'alpha', alpha))
        if beta != f'{parent}_beta':
            final_wrong.append((parent, 'beta', beta))

    c_expected = by_expected['route_c'][1]
    c_recalled = by_expected['route_c'][0]
    c_predictions = sum(n for (exp, got), n in confusion.items() if got == 'route_c')
    c_true_predictions = confusion[('route_c', 'route_c')]
    c_recall = c_recalled / c_expected if c_expected else 1.0
    c_precision = c_true_predictions / c_predictions if c_predictions else 1.0
    delay_acc = by_expected['starter'][0] / by_expected['starter'][1]

    print('FRESH_GROWTH_PROFILE_BLIND_V1')
    print(f'broad_accuracy={broad_acc:.3f} ({broad_correct}/{broad_total})')
    print(f'c_precision={c_precision:.3f} c_recall={c_recall:.3f}')
    print(f'delay_specificity={delay_acc:.3f}')
    print(f'subroute_accuracy={(len(SUB)-len(sub_wrong))/len(SUB):.3f}')
    print(f'final_trajectory_accuracy={(len(FINAL_PARENTS)*2-len(final_wrong))/(len(FINAL_PARENTS)*2):.3f}')
    for expected, pair in sorted(by_expected.items()):
        print(f'expected_{expected}={pair[0]}/{pair[1]}')
    if wrong:
        print('BROAD_WATCHLIST')
        for row in wrong:
            print(row)
    if sub_wrong:
        print('SUBROUTE_WATCHLIST')
        for row in sub_wrong:
            print(row)
    if final_wrong:
        print('FINAL_WATCHLIST')
        for row in final_wrong:
            print(row)

    # Release-style gates. A failure is evidence to inspect, not permission to relabel this rerun.
    ok = (
        broad_acc >= 0.90
        and c_precision >= 0.85
        and c_recall >= 0.85
        and delay_acc >= 0.875
        and not sub_wrong
        and not final_wrong
    )
    print('PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
