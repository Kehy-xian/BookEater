from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))

from PIL import Image

from bookeater.sprite_validation import validate_sprite_pack
from generate_subroute_sprites import generate_all_subroute_core_frames

SLUGS = ('route_a1', 'route_a2', 'route_b1', 'route_b2', 'route_c1', 'route_c2')


def _dark_ratio(image: Image.Image, box=(76, 76, 115, 119)) -> float:
    """Measure dark-core coverage without depending on one eye/window pixel.

    Light eyes and B2 window bars are intentionally part of the designs, so one coordinate is a
    brittle lineage check. A region ratio verifies the actual face substrate instead: A should be
    mostly ivory paper while B/C should be mostly dark core.
    """
    region = image.crop(box).convert('RGBA')
    visible = [px for px in region.getdata() if px[3] > 0]
    assert visible
    dark = [px for px in visible if sum(px[:3]) / 3 < 120]
    return len(dark) / len(visible)


def test_generated_subroute_packs_are_complete(tmp_path):
    files = generate_all_subroute_core_frames(tmp_path)
    assert len(files) == 84
    for slug in SLUGS:
        assert not validate_sprite_pack(tmp_path, slug, required_states=('idle', 'eat', 'walk'))


def test_subroute_faces_preserve_parent_lineage(tmp_path):
    generate_all_subroute_core_frames(tmp_path)
    imgs = {slug: Image.open(tmp_path / f'{slug}_idle_00.png').convert('RGBA') for slug in SLUGS}
    ratios = {slug: _dark_ratio(img) for slug, img in imgs.items()}

    # A descendants keep a light paper face rather than inheriting B/C's dark core.
    for slug in ('route_a1', 'route_a2'):
        assert ratios[slug] < 0.32, f'{slug} unexpectedly looks dark-core: ratio={ratios[slug]:.3f}'

    # B/C descendants retain a dark inner core despite bright eyes or shell/window details.
    for slug in ('route_b1', 'route_b2', 'route_c1', 'route_c2'):
        assert ratios[slug] > 0.42, f'{slug} lost its dark-core lineage: ratio={ratios[slug]:.3f}'

    # Sibling silhouettes are materially different, not simple face swaps.
    assert imgs['route_a1'].tobytes() != imgs['route_a2'].tobytes()
    assert imgs['route_b1'].tobytes() != imgs['route_b2'].tobytes()
    assert imgs['route_c1'].tobytes() != imgs['route_c2'].tobytes()


def test_subroute_motion_frames_change_without_route_swaps(tmp_path):
    generate_all_subroute_core_frames(tmp_path)
    for slug in SLUGS:
        idle0 = (tmp_path / f'{slug}_idle_00.png').read_bytes()
        idle2 = (tmp_path / f'{slug}_idle_02.png').read_bytes()
        eat0 = (tmp_path / f'{slug}_eat_00.png').read_bytes()
        eat5 = (tmp_path / f'{slug}_eat_05.png').read_bytes()
        walk0 = (tmp_path / f'{slug}_walk_00.png').read_bytes()
        walk1 = (tmp_path / f'{slug}_walk_01.png').read_bytes()
        assert idle0 != idle2
        assert eat0 != eat5
        assert walk0 != walk1
