from __future__ import annotations

"""Fresh growth-profile holdout v2.

Authored only after the v1 C-overrouting patch and diagnostic were complete. It focuses on a new
failure surface: clear response lineage coexisting with diverse world/topic interests. World axes
should usually remain motifs rather than stealing a clearly established A/B body lineage.
"""

from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.game.growth_route_resolver import resolve_growth_route


CASES = [
    # Clear A with realistic side-reactions; three active axes alone must not imply C.
    ('a201', 'route_a', {'사유': 2.6, '탐구': 2.1, '감정': 1.4, '감각': 0.4}),
    ('a202', 'route_a', {'사유': 3.1, '탐구': 1.8, '감정': 1.5, '감각': 0.2}),
    ('a203', 'route_a', {'사유': 1.7, '탐구': 3.2, '감정': 1.1, '감각': 0.5}),
    ('a204', 'route_a', {'사유': 3.7, '탐구': 1.0, '감정': 1.5, '감각': 0.3}),
    # Clear A plus diverse worlds: worlds should become motifs, not automatically Route C.
    ('a205', 'route_a', {'사유': 3.2, '탐구': 1.8, '감정': 0.8, '감각': 0.4, '자연': 2.3, '사회': 2.0, '모험': 1.2}),
    ('a206', 'route_a', {'사유': 1.8, '탐구': 3.4, '감정': 0.7, '감각': 0.4, '상상': 2.4, '어둠': 2.0, '사회': 1.0}),
    ('a207', 'route_a', {'사유': 4.1, '탐구': 1.2, '감정': 0.8, '자연': 2.5, '사회': 1.7}),

    # Clear B equivalents.
    ('b201', 'route_b', {'감정': 2.6, '감각': 2.1, '사유': 1.4, '탐구': 0.4}),
    ('b202', 'route_b', {'감정': 3.1, '감각': 1.8, '사유': 1.5, '탐구': 0.2}),
    ('b203', 'route_b', {'감정': 1.7, '감각': 3.2, '사유': 1.1, '탐구': 0.5}),
    ('b204', 'route_b', {'감정': 3.7, '감각': 1.0, '사유': 1.5, '탐구': 0.3}),
    ('b205', 'route_b', {'감정': 3.2, '감각': 1.8, '사유': 0.8, '탐구': 0.4, '상상': 2.3, '어둠': 2.0, '사회': 1.2}),
    ('b206', 'route_b', {'감정': 1.8, '감각': 3.4, '사유': 0.7, '탐구': 0.4, '자연': 2.4, '모험': 2.0, '사회': 1.0}),
    ('b207', 'route_b', {'감정': 4.1, '감각': 1.2, '사유': 0.8, '자연': 2.5, '사회': 1.7}),

    # Genuine C via developed balanced/mixed responses.
    ('c201', 'route_c', {'사유': 2.5, '탐구': 1.1, '감정': 2.2, '감각': 1.0}),
    ('c202', 'route_c', {'사유': 1.7, '탐구': 1.6, '감정': 1.8, '감각': 1.5}),
    ('c203', 'route_c', {'사유': 2.1, '탐구': 1.2, '감정': 2.0, '감각': 1.1, '사회': 1.0}),
    ('c204', 'route_c', {'사유': 1.4, '탐구': 1.8, '감정': 1.5, '감각': 1.7}),
    # Genuine C via world-dominant connected profile with no strong response lineage.
    ('c205', 'route_c', {'사유': 1.0, '감정': 0.9, '상상': 3.2, '사회': 2.6, '어둠': 1.4}),
    ('c206', 'route_c', {'탐구': 1.1, '감각': 0.8, '자연': 3.0, '모험': 2.7, '사회': 1.5}),
    ('c207', 'route_c', {'사유': 1.2, '감정': 1.1, '모험': 2.8, '상상': 2.5, '자연': 2.1}),

    # Still not enough to permanently choose a lineage.
    ('d201', 'starter', {'사유': 2.3, '감정': 2.2, '탐구': 0.5, '감각': 0.4}),
    ('d202', 'starter', {'탐구': 2.4, '감각': 2.3, '사유': 0.4, '감정': 0.4}),
    ('d203', 'starter', {'사유': 1.4, '탐구': 1.3, '감정': 1.4, '감각': 1.3}),
    ('d204', 'starter', {'사유': 1.6, '탐구': 1.2, '감정': 1.5, '감각': 1.2}),
    ('d205', 'starter', {'사유': 0.7, '감정': 0.7, '상상': 1.8, '사회': 1.5}),
    ('d206', 'starter', {'탐구': 0.8, '감각': 0.7, '자연': 1.7, '모험': 1.6}),
    ('d207', 'starter', {'사유': 1.9, '감정': 1.8, '상상': 1.0, '사회': 0.8}),
]


def main() -> int:
    wrong = []
    confusion = Counter()
    for case_id, expected, stats in CASES:
        got = resolve_growth_route(stats, 9).form_id
        confusion[(expected, got)] += 1
        if got != expected:
            wrong.append((case_id, expected, got, stats))

    total = len(CASES)
    acc = (total - len(wrong)) / total
    c_pred = sum(n for (expected, got), n in confusion.items() if got == 'route_c')
    c_true = confusion[('route_c', 'route_c')]
    c_expected = sum(n for (expected, _got), n in confusion.items() if expected == 'route_c')
    c_precision = c_true / c_pred if c_pred else 1.0
    c_recall = c_true / c_expected if c_expected else 1.0
    a_recall = confusion[('route_a', 'route_a')] / 7
    b_recall = confusion[('route_b', 'route_b')] / 7
    delay = confusion[('starter', 'starter')] / 7

    print('FRESH_GROWTH_PROFILE_BLIND_V2')
    print(f'accuracy={acc:.3f} ({total-len(wrong)}/{total})')
    print(f'a_recall={a_recall:.3f} b_recall={b_recall:.3f}')
    print(f'c_precision={c_precision:.3f} c_recall={c_recall:.3f}')
    print(f'delay_specificity={delay:.3f}')
    if wrong:
        print('WATCHLIST')
        for row in wrong:
            print(row)

    ok = (
        acc >= 0.90
        and a_recall >= 0.85
        and b_recall >= 0.85
        and c_precision >= 0.85
        and c_recall >= 0.85
        and delay >= 0.85
    )
    print('PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
