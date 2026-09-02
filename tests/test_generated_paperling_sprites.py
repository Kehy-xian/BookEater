from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))

from PIL import Image

from bookeater.sprite_validation import validate_sprite_pack
from generate_paperling_sprites import generate_paperling_core_frames


def test_generated_paperling_core_pack_is_complete_rgba_and_transparent(tmp_path):
    files = generate_paperling_core_frames(tmp_path)
    assert len(files) == 14
    assert not validate_sprite_pack(tmp_path, 'paperling', required_states=('idle', 'eat', 'walk'))

    idle = Image.open(tmp_path / 'paperling_idle_00.png')
    assert idle.mode == 'RGBA'
    assert idle.size == (190, 190)
    alpha = idle.getchannel('A')
    assert alpha.getextrema() == (0, 255)


def test_generated_core_states_are_visually_distinct(tmp_path):
    generate_paperling_core_frames(tmp_path)
    idle_hashes = {(tmp_path / f'paperling_idle_{i:02d}.png').read_bytes() for i in range(4)}
    eat_hashes = {(tmp_path / f'paperling_eat_{i:02d}.png').read_bytes() for i in range(6)}
    walk_hashes = {(tmp_path / f'paperling_walk_{i:02d}.png').read_bytes() for i in range(4)}
    assert len(idle_hashes) >= 3
    assert len(eat_hashes) >= 5
    assert len(walk_hashes) >= 2
    assert (tmp_path / 'paperling_idle_00.png').read_bytes() != (tmp_path / 'paperling_eat_00.png').read_bytes()
