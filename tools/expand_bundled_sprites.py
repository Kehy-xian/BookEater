from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.pet_art import GEULSSIAL_ANIMATIONS, frame_filename
from bookeater.sprite_validation import SPRITE_HEIGHT, SPRITE_WIDTH, validate_sprite_pack
from generate_paperling_sprites import generate_paperling_core_frames
from generate_route_sprites import generate_route_core_frames

ARCHIVE_DIR = ROOT / 'resources' / 'sprite_archives'
SPRITE_DIR = ROOT / 'resources' / 'sprites'
CORE_STATES = ('idle', 'eat', 'walk')
ATLAS_COLUMNS = 7
ATLAS_ROWS = 2

# Approved starter atlas layout, row-major. The visual can be replaced later without changing code
# as long as the same 7x2 cell contract is preserved.
PAPERLING_ATLAS_ORDER = (
    ('idle', 0), ('idle', 1), ('idle', 2), ('idle', 3),
    ('eat', 0), ('eat', 1), ('eat', 2),
    ('eat', 3), ('eat', 4), ('eat', 5),
    ('walk', 0), ('walk', 1), ('walk', 2), ('walk', 3),
)


def _atlas_parts(slug: str) -> tuple[Path, ...]:
    parts = tuple(sorted(ARCHIVE_DIR.glob(f'{slug}_atlas.b85.part*')))
    if not parts:
        return ()
    # A partially committed atlas must never break a playable build. Only a contiguous set of
    # part00..partNN is considered installable; otherwise the replaceable baseline is generated.
    indices: list[int] = []
    for part in parts:
        suffix = part.name.rsplit('part', 1)[-1]
        if not suffix.isdigit():
            return ()
        indices.append(int(suffix))
    if indices != list(range(len(parts))):
        return ()
    return parts


def _decode_atlas(parts: tuple[Path, ...]):
    if not parts:
        return None
    # Pillow is build-only; it is not imported by the shipped desktop application.
    from PIL import Image

    encoded = ''.join(p.read_text(encoding='ascii').strip() for p in parts)
    try:
        raw = base64.b85decode(encoded.encode('ascii'))
        image = Image.open(BytesIO(raw))
        image.load()
    except Exception as exc:
        raise RuntimeError(f'cannot decode sprite atlas: {type(exc).__name__}') from exc
    expected_size = (SPRITE_WIDTH * ATLAS_COLUMNS, SPRITE_HEIGHT * ATLAS_ROWS)
    if image.size != expected_size:
        raise RuntimeError(f'sprite atlas must be {expected_size[0]}x{expected_size[1]}, got {image.size}')
    return image.convert('RGBA')


def _issues_for(slug: str, target: Path = SPRITE_DIR):
    return validate_sprite_pack(target, slug, required_states=CORE_STATES)


def _validate(slug: str, target: Path = SPRITE_DIR) -> None:
    issues = _issues_for(slug, target)
    if issues:
        detail = '; '.join(f'{x.code}:{x.path.name}' for x in issues[:8])
        raise RuntimeError(f'{slug} sprite validation failed: {detail}')


def _existing_core_files(slug: str) -> tuple[Path, ...]:
    if not SPRITE_DIR.is_dir():
        return ()
    return tuple(SPRITE_DIR.glob(f'{slug}_*.png'))


def expand_paperling() -> str:
    parts = _atlas_parts('paperling')
    atlas = _decode_atlas(parts)

    if atlas is None:
        existing = _existing_core_files('paperling')
        if existing:
            _validate('paperling')
            return 'packaged'
        # Safe replaceable baseline that preserves the approved starter identity. A complete later
        # atlas automatically takes precedence without any runtime/gameplay change.
        generate_paperling_core_frames(SPRITE_DIR)
        _validate('paperling')
        return 'baseline'

    with tempfile.TemporaryDirectory(prefix='bookeater-sprites-') as temp:
        staging = Path(temp)
        for atlas_index, (state, frame_index) in enumerate(PAPERLING_ATLAS_ORDER):
            col = atlas_index % ATLAS_COLUMNS
            row = atlas_index // ATLAS_COLUMNS
            box = (
                col * SPRITE_WIDTH,
                row * SPRITE_HEIGHT,
                (col + 1) * SPRITE_WIDTH,
                (row + 1) * SPRITE_HEIGHT,
            )
            frame = atlas.crop(box)
            target = staging / frame_filename('paperling', state, frame_index)
            frame.save(target, format='PNG', optimize=True)

        _validate('paperling', staging)
        SPRITE_DIR.mkdir(parents=True, exist_ok=True)
        for state in CORE_STATES:
            for i in range(GEULSSIAL_ANIMATIONS[state].frame_count):
                name = frame_filename('paperling', state, i)
                shutil.copy2(staging / name, SPRITE_DIR / name)
    return 'atlas'


def ensure_route(slug: str) -> str:
    existing = _existing_core_files(slug)
    if existing:
        # Packaged hand-authored art is allowed to replace the generated baseline, but it must be
        # complete. A partial committed route pack is a release error rather than something to mix.
        _validate(slug)
        return 'packaged'
    generate_route_core_frames(SPRITE_DIR, slug)
    _validate(slug)
    return 'baseline'


def main() -> int:
    sources = {'paperling': expand_paperling()}
    for slug in ('pagedge', 'inknest', 'lantern'):
        sources[slug] = ensure_route(slug)
    print('BUNDLED_SPRITES_EXPANDED ' + ' '.join(f'{k}={v}' for k, v in sources.items()))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
