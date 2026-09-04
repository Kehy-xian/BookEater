from pathlib import Path
import sys

from PIL import Image
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))

import expand_bundled_sprites as expand
from bookeater.pet_art import GEULSSIAL_ANIMATIONS, frame_filename
from bookeater.sprite_validation import validate_sprite_pack


def _write_distinct_state(root: Path, state: str) -> dict[str, bytes]:
    root.mkdir(parents=True, exist_ok=True)
    written = {}
    for index in range(GEULSSIAL_ANIMATIONS[state].frame_count):
        path = root / frame_filename('paperling', state, index)
        Image.new('RGBA', (190, 190), (20 + index, 40, 60, 255)).save(path)
        written[path.name] = path.read_bytes()
    return written


def test_hand_authored_states_survive_while_missing_core_states_are_filled(tmp_path, monkeypatch):
    sprite_dir = tmp_path / 'sprites'
    monkeypatch.setattr(expand, 'SPRITE_DIR', sprite_dir)
    monkeypatch.setattr(expand, 'ARCHIVE_DIR', tmp_path / 'archives')
    original_idle = _write_distinct_state(sprite_dir, 'idle')

    source = expand.expand_paperling()

    assert source == 'packaged-idle+baseline'
    assert {path.name: path.read_bytes() for path in sprite_dir.glob('paperling_idle_*.png')} == original_idle
    assert not validate_sprite_pack(sprite_dir, 'paperling', required_states=expand.CORE_STATES)


def test_partial_hand_authored_state_is_rejected_before_fallback_fill(tmp_path, monkeypatch):
    sprite_dir = tmp_path / 'sprites'
    monkeypatch.setattr(expand, 'SPRITE_DIR', sprite_dir)
    monkeypatch.setattr(expand, 'ARCHIVE_DIR', tmp_path / 'archives')
    sprite_dir.mkdir()
    Image.new('RGBA', (190, 190), (20, 40, 60, 255)).save(sprite_dir / 'paperling_idle_00.png')

    with pytest.raises(RuntimeError, match='paperling sprite validation failed'):
        expand.expand_paperling()
