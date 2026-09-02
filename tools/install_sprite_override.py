from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.art_override_store import SpritePackValidationError, install_sprite_pack
from bookeater.pet_sprite import default_override_root
from bookeater.runtime import default_data_dir


def main() -> int:
    parser = argparse.ArgumentParser(description='Safely install a BookEater sprite design revision.')
    parser.add_argument('source', type=Path, help='Directory containing sprite PNG frames')
    parser.add_argument('slug', help='Asset slug, e.g. paperling / pagedge / inknest / lantern')
    parser.add_argument('--states', default='idle,eat,walk', help='Comma-separated states to replace')
    parser.add_argument('--data-dir', type=Path, default=None, help='Override BookEater user-data directory')
    args = parser.parse_args()

    states = tuple(x.strip() for x in args.states.split(',') if x.strip())
    data_dir = args.data_dir or default_data_dir()
    override_root = default_override_root(data_dir)
    try:
        installed = install_sprite_pack(args.source, override_root, args.slug, states=states)
    except SpritePackValidationError as exc:
        print(f'SPRITE_PACK_NOT_INSTALLED issues={len(exc.issues)}')
        for issue in exc.issues:
            print(f'{issue.code}: {issue.path}: {issue.message}')
        return 1
    except (OSError, ValueError) as exc:
        print(f'SPRITE_PACK_NOT_INSTALLED error={type(exc).__name__}: {exc}')
        return 2

    print(f'SPRITE_PACK_INSTALLED slug={installed.slug} revision={installed.revision}')
    print(f'active_root={installed.pack_root}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
