from __future__ import annotations

from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.pet_art import GEULSSIAL_ANIMATIONS, frame_filename
from bookeater.sprite_validation import validate_sprite_pack

ARCHIVE_DIR = ROOT / 'resources' / 'sprite_archives'
SPRITE_DIR = ROOT / 'resources' / 'sprites'
BUNDLED_PACKS = {
    'paperling': ARCHIVE_DIR / 'paperling_core14.zip',
}
CORE_STATES = ('idle', 'eat', 'walk')


def expected_names(slug: str) -> set[str]:
    return {
        frame_filename(slug, state, i)
        for state in CORE_STATES
        for i in range(GEULSSIAL_ANIMATIONS[state].frame_count)
    }


def expand_one(slug: str, archive: Path) -> None:
    if not archive.is_file():
        # During source development the archive may intentionally be absent; vector fallback stays
        # playable. Release/package CI separately asserts required starter art is present.
        return
    expected = expected_names(slug)
    with zipfile.ZipFile(archive) as zf:
        names = {info.filename for info in zf.infolist() if not info.is_dir()}
        if names != expected:
            missing = sorted(expected - names)
            extra = sorted(names - expected)
            raise RuntimeError(f'{archive.name}: unexpected contents missing={missing} extra={extra}')
        if any(Path(name).name != name for name in names):
            raise RuntimeError(f'{archive.name}: nested/traversal paths are not allowed')

        with tempfile.TemporaryDirectory(prefix='bookeater-sprites-') as temp:
            staging = Path(temp)
            for name in sorted(names):
                target = staging / name
                with zf.open(name) as src, target.open('wb') as dst:
                    shutil.copyfileobj(src, dst)
            issues = validate_sprite_pack(staging, slug, required_states=CORE_STATES)
            if issues:
                detail = '; '.join(f'{x.code}:{x.path.name}' for x in issues[:8])
                raise RuntimeError(f'{archive.name}: sprite validation failed: {detail}')
            SPRITE_DIR.mkdir(parents=True, exist_ok=True)
            for name in sorted(names):
                shutil.copy2(staging / name, SPRITE_DIR / name)


def main() -> int:
    for slug, archive in BUNDLED_PACKS.items():
        expand_one(slug, archive)
    print('BUNDLED_SPRITES_EXPANDED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
