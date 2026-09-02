from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.pet_art import GEULSSIAL_ANIMATIONS, frame_filename
from bookeater.sprite_validation import validate_frame, validate_sprite_pack


def _chunk(kind: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(kind)
    crc = zlib.crc32(payload, crc) & 0xFFFFFFFF
    return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', crc)


def _png(width=190, height=190, *, color_type=6) -> bytes:
    if color_type == 6:
        pixel = b'\x00\x00\x00\x00'
    elif color_type == 2:
        pixel = b'\x00\x00\x00'
    else:
        raise ValueError(color_type)
    raw = b''.join(b'\x00' + pixel * width for _ in range(height))
    ihdr = struct.pack('>IIBBBBB', width, height, 8, color_type, 0, 0, 0)
    return (
        b'\x89PNG\r\n\x1a\n'
        + _chunk(b'IHDR', ihdr)
        + _chunk(b'IDAT', zlib.compress(raw))
        + _chunk(b'IEND', b'')
    )


def test_valid_rgba_frame_passes(tmp_path):
    frame = tmp_path / 'paperling_idle_00.png'
    frame.write_bytes(_png())
    assert validate_frame(frame) == ()


def test_wrong_canvas_is_rejected_without_restricting_character_design(tmp_path):
    frame = tmp_path / 'paperling_idle_00.png'
    frame.write_bytes(_png(128, 190))
    issues = validate_frame(frame)
    assert [x.code for x in issues] == ['wrong_canvas']


def test_non_rgba_png_is_rejected(tmp_path):
    frame = tmp_path / 'paperling_idle_00.png'
    frame.write_bytes(_png(color_type=2))
    issues = validate_frame(frame)
    assert [x.code for x in issues] == ['not_rgba8']


def test_crc_damage_is_detected(tmp_path):
    frame = tmp_path / 'paperling_idle_00.png'
    blob = bytearray(_png())
    # Corrupt one byte in IHDR payload without updating its CRC.
    blob[20] ^= 1
    frame.write_bytes(bytes(blob))
    issues = validate_frame(frame)
    assert len(issues) == 1
    assert issues[0].code == 'invalid_png'
    assert 'CRC mismatch' in issues[0].message


def test_required_pack_reports_missing_frames(tmp_path):
    root = tmp_path / 'pack'
    root.mkdir()
    root.joinpath(frame_filename('paperling', 'idle', 0)).write_bytes(_png())
    issues = validate_sprite_pack(root, 'paperling', required_states=('idle',))
    missing = [x for x in issues if x.code == 'missing']
    assert len(missing) == GEULSSIAL_ANIMATIONS['idle'].frame_count - 1


def test_complete_minimum_pack_idle_eat_walk_passes(tmp_path):
    root = tmp_path / 'pack'
    root.mkdir()
    for state in ('idle', 'eat', 'walk'):
        for i in range(GEULSSIAL_ANIMATIONS[state].frame_count):
            root.joinpath(frame_filename('paperling', state, i)).write_bytes(_png())
    assert validate_sprite_pack(root, 'paperling') == ()
