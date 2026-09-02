from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.art_override_store import (
    SpritePackValidationError,
    active_pack_root,
    install_sprite_pack,
    override_source_root,
)
from bookeater.pet_art import GEULSSIAL_ANIMATIONS, frame_filename


def _chunk(kind: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(kind)
    crc = zlib.crc32(payload, crc) & 0xFFFFFFFF
    return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', crc)


def _png(marker: int = 0) -> bytes:
    width = height = 190
    # Transparent RGBA with a tiny marker in the first pixel so revisions can differ.
    rows = []
    first = bytes((marker % 256, 0, 0, 255))
    clear = b'\x00\x00\x00\x00'
    for y in range(height):
        row = first + clear * (width - 1) if y == 0 else clear * width
        rows.append(b'\x00' + row)
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + _chunk(b'IHDR', ihdr) + _chunk(b'IDAT', zlib.compress(b''.join(rows))) + _chunk(b'IEND', b'')


def _write_state(root: Path, slug: str, state: str, marker: int = 0):
    root.mkdir(parents=True, exist_ok=True)
    for i in range(GEULSSIAL_ANIMATIONS[state].frame_count):
        (root / frame_filename(slug, state, i)).write_bytes(_png(marker + i))


def test_valid_pack_activates_versioned_revision(tmp_path):
    source = tmp_path / 'source'
    override = tmp_path / 'art_overrides'
    for state in ('idle', 'eat', 'walk'):
        _write_state(source, 'paperling', state, 10)

    installed = install_sprite_pack(source, override, 'paperling')
    active = active_pack_root(override, 'paperling')
    assert active == installed.pack_root
    assert active is not None
    assert active.parent.parent.name == '.packs'
    assert override_source_root(override, 'paperling') == active


def test_invalid_new_pack_never_replaces_existing_active_revision(tmp_path):
    good = tmp_path / 'good'
    bad = tmp_path / 'bad'
    override = tmp_path / 'art_overrides'
    for state in ('idle', 'eat', 'walk'):
        _write_state(good, 'paperling', state, 20)
    first = install_sprite_pack(good, override, 'paperling')

    _write_state(bad, 'paperling', 'idle', 30)
    # eat/walk are deliberately missing.
    try:
        install_sprite_pack(bad, override, 'paperling')
    except SpritePackValidationError:
        pass
    else:
        raise AssertionError('invalid pack unexpectedly installed')

    assert active_pack_root(override, 'paperling') == first.pack_root


def test_partial_state_update_carries_forward_previous_override_states(tmp_path):
    full = tmp_path / 'full'
    idle_only = tmp_path / 'idle-only'
    override = tmp_path / 'art_overrides'
    for state in ('idle', 'eat', 'walk'):
        _write_state(full, 'paperling', state, 40)
    first = install_sprite_pack(full, override, 'paperling')

    _write_state(idle_only, 'paperling', 'idle', 90)
    second = install_sprite_pack(idle_only, override, 'paperling', states=('idle',))
    assert second.revision != first.revision
    assert active_pack_root(override, 'paperling') == second.pack_root

    # New idle bytes came from the update.
    assert (second.pack_root / frame_filename('paperling', 'idle', 0)).read_bytes() == (
        idle_only / frame_filename('paperling', 'idle', 0)
    ).read_bytes()
    # Unchanged walk/eat bytes were carried forward from the old immutable revision.
    for state in ('eat', 'walk'):
        name = frame_filename('paperling', state, 0)
        assert (second.pack_root / name).read_bytes() == (first.pack_root / name).read_bytes()


def test_malformed_active_pointer_is_ignored_and_legacy_flat_root_remains_available(tmp_path):
    override = tmp_path / 'art_overrides'
    (override / '.active').mkdir(parents=True)
    (override / '.active' / 'paperling.txt').write_text('../../escape', encoding='ascii')
    assert active_pack_root(override, 'paperling') is None
    assert override_source_root(override, 'paperling') == override
