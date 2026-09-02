from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))

from PIL import Image

from bookeater.sprite_validation import validate_sprite_pack
from generate_route_sprites import generate_all_route_core_frames


def test_generated_route_core_packs_are_complete(tmp_path):
    files = generate_all_route_core_frames(tmp_path)
    assert len(files) == 42
    for slug in ('pagedge', 'inknest', 'lantern'):
        assert not validate_sprite_pack(tmp_path, slug, required_states=('idle', 'eat', 'walk'))


def test_route_faces_keep_distinct_lineage_signatures(tmp_path):
    generate_all_route_core_frames(tmp_path)
    a = Image.open(tmp_path / 'pagedge_idle_00.png').convert('RGBA')
    b = Image.open(tmp_path / 'inknest_idle_00.png').convert('RGBA')
    c = Image.open(tmp_path / 'lantern_idle_00.png').convert('RGBA')

    # A has a light paper face at the body center. B/C have dark cores.
    a_center = a.getpixel((95, 92))[:3]
    b_center = b.getpixel((95, 92))[:3]
    c_center = c.getpixel((95, 92))[:3]
    assert sum(a_center) > sum(b_center) + 250
    assert sum(a_center) > sum(c_center) + 250

    # B and C are not interchangeable silhouettes even though both have dark cores.
    assert b.tobytes() != c.tobytes()
    # All route frames remain transparent outside the creature.
    assert a.getpixel((0, 0))[3] == 0
    assert b.getpixel((0, 0))[3] == 0
    assert c.getpixel((0, 0))[3] == 0


def test_each_route_has_real_motion_between_core_frames(tmp_path):
    generate_all_route_core_frames(tmp_path)
    for slug in ('pagedge', 'inknest', 'lantern'):
        assert (tmp_path / f'{slug}_idle_00.png').read_bytes() != (tmp_path / f'{slug}_idle_02.png').read_bytes()
        assert (tmp_path / f'{slug}_eat_00.png').read_bytes() != (tmp_path / f'{slug}_eat_04.png').read_bytes()
        assert (tmp_path / f'{slug}_walk_00.png').read_bytes() != (tmp_path / f'{slug}_walk_01.png').read_bytes()
