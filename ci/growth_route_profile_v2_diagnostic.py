from __future__ import annotations

"""Post-fix diagnostic only.

The v2 cases already influenced resolver changes, so this file must never be described as fresh.
It simply confirms those sealed profiles still behave after the new 16-record first gate.
"""

from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT))

from bookeater.game.growth_route_resolver import resolve_growth_route
from ci.growth_route_profile_blind_v2 import CASES


def main() -> int:
    wrong = []
    confusion = Counter()
    for case_id, expected, stats in CASES:
        got = resolve_growth_route(stats, 16).form_id
        confusion[(expected, got)] += 1
        if got != expected:
            wrong.append((case_id, expected, got))

    total = len(CASES)
    acc = (total - len(wrong)) / total
    print('POST_FIX_V2_DIAGNOSTIC')
    print(f'accuracy={acc:.3f} ({total-len(wrong)}/{total})')
    if wrong:
        print('WATCHLIST')
        for row in wrong:
            print(row)
    ok = acc >= 0.90
    print('PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
