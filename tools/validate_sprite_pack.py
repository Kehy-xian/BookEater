from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.sprite_validation import validate_sprite_pack


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate BookEater transparent PNG sprite frames.')
    parser.add_argument('root', type=Path, help='Directory containing <slug>_<state>_NN.png files')
    parser.add_argument('slug', help='Asset slug, e.g. paperling / pagedge / inknest / lantern')
    parser.add_argument(
        '--states',
        default='idle,eat,walk',
        help='Comma-separated states to require (default: idle,eat,walk)',
    )
    args = parser.parse_args()
    states = tuple(x.strip() for x in args.states.split(',') if x.strip())
    issues = validate_sprite_pack(args.root, args.slug, required_states=states)
    if issues:
        print(f'SPRITE_PACK_INVALID issues={len(issues)}')
        for issue in issues:
            print(f'{issue.code}: {issue.path}: {issue.message}')
        return 1
    print(f'SPRITE_PACK_OK slug={args.slug} states={",".join(states)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
