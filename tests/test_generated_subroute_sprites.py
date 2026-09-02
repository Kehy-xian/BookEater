from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))

from PIL import Image

from bookeater.sprite_validation import validate_sprite_pack
from generate_subroute_sprites import generate_all_subroute_core_frames

SLUGS = ('route_a1', 'route_a2', 'route_b1', 'route_b2', 'route_c1', 'route_c2')


def test_generated_subroute_packs_are_complete(tmp_path):
    files = generate_all_subroute_core_frames(tmp_path)
    assert len(files) == 84
    for slug in SLUGS:
        assert not validate_sprite_pack(tmp_path, slug, required_states=('idle', 'eat', 'walk'))


def test_subroute_faces_preserve_parent_lineage(tmp_path):
    generate_all_subroute_core_frames(tmp_path)
    imgs = {slug: Image.open(tmp_path / f'{slug}_idle_00.png').convert('RGBA') for slug in SLUGS}

    # A descendants keep a light paper face rather than inheriting B/C's dark core.
    for slug in ('route_a1', 'route_a2'):
        px = imgs[slug].getpixel((82, 90))[:3]
        assert sum(px) > 450

    # B/C descendants retain a dark inner core. Sample off-center so B2's window bars do not mask it.
    for slug in ('route_b1', 'route_b2', 'route_c1', 'route_c2'):
        px = imgs[slug].getpixel((82, 90))[:3]
        assert sum(px) < 250

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
