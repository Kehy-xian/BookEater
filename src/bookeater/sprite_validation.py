from __future__ import annotations

"""Validation helpers for replaceable BookEater PNG sprite packs.

The validator is intentionally independent from Tk/Pillow so it can run in CI and in a packaged
build without adding image-library dependencies. Production frames use one fixed transparent RGBA
canvas; visual content inside that canvas may change freely at any time.
"""

from dataclasses import dataclass
from pathlib import Path
import struct
import zlib

from .pet_art import GEULSSIAL_ANIMATIONS, frame_filename

PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
SPRITE_WIDTH = 190
SPRITE_HEIGHT = 190
RGBA_COLOR_TYPE = 6


@dataclass(frozen=True)
class PngInfo:
    width: int
    height: int
    bit_depth: int
    color_type: int


@dataclass(frozen=True)
class SpritePackIssue:
    path: Path
    code: str
    message: str


def _read_exact(stream, size: int, label: str) -> bytes:
    data = stream.read(size)
    if len(data) != size:
        raise ValueError(f'PNG {label} is truncated')
    return data


def read_png_info(path: str | Path) -> PngInfo:
    """Read PNG metadata while validating chunk boundaries and CRC integrity."""
    p = Path(path)
    with p.open('rb') as f:
        if _read_exact(f, 8, 'signature') != PNG_SIGNATURE:
            raise ValueError('invalid PNG signature')

        info: PngInfo | None = None
        seen_idat = False
        seen_iend = False
        chunk_index = 0

        while not seen_iend:
            length_raw = f.read(4)
            if not length_raw:
                raise ValueError('PNG IEND is missing')
            if len(length_raw) != 4:
                raise ValueError('PNG chunk length is truncated')
            length = struct.unpack('>I', length_raw)[0]
            chunk_type = _read_exact(f, 4, 'chunk type')
            label = chunk_type.decode('latin1', errors='replace')
            data = _read_exact(f, length, label)
            crc_raw = _read_exact(f, 4, 'chunk CRC')
            expected_crc = struct.unpack('>I', crc_raw)[0]
            actual_crc = zlib.crc32(chunk_type)
            actual_crc = zlib.crc32(data, actual_crc) & 0xFFFFFFFF
            if expected_crc != actual_crc:
                raise ValueError(f'PNG {label} CRC mismatch')

            if chunk_index == 0 and chunk_type != b'IHDR':
                raise ValueError('PNG IHDR must be the first chunk')
            if chunk_type == b'IHDR':
                if info is not None or length != 13:
                    raise ValueError('PNG IHDR is duplicated or invalid')
                width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                    '>IIBBBBB', data
                )
                if width <= 0 or height <= 0:
                    raise ValueError('PNG dimensions must be positive')
                if compression != 0 or filter_method != 0 or interlace not in {0, 1}:
                    raise ValueError('PNG IHDR uses unsupported metadata')
                info = PngInfo(width, height, bit_depth, color_type)
            elif chunk_type == b'IDAT':
                seen_idat = True
            elif chunk_type == b'IEND':
                if length != 0:
                    raise ValueError('PNG IEND must be empty')
                seen_iend = True
            chunk_index += 1

        if info is None:
            raise ValueError('PNG IHDR is missing')
        if not seen_idat:
            raise ValueError('PNG IDAT is missing')
        if f.read(1):
            raise ValueError('PNG has unexpected trailing bytes after IEND')
        return info


def validate_frame(path: str | Path) -> tuple[SpritePackIssue, ...]:
    p = Path(path)
    if not p.is_file():
        return (SpritePackIssue(p, 'missing', 'required frame is missing'),)
    try:
        info = read_png_info(p)
    except (OSError, ValueError) as exc:
        return (SpritePackIssue(p, 'invalid_png', str(exc)),)

    issues: list[SpritePackIssue] = []
    if (info.width, info.height) != (SPRITE_WIDTH, SPRITE_HEIGHT):
        issues.append(SpritePackIssue(
            p,
            'wrong_canvas',
            f'expected {SPRITE_WIDTH}x{SPRITE_HEIGHT}, got {info.width}x{info.height}',
        ))
    if info.bit_depth != 8 or info.color_type != RGBA_COLOR_TYPE:
        issues.append(SpritePackIssue(
            p,
            'not_rgba8',
            f'expected 8-bit RGBA PNG, got bit_depth={info.bit_depth} color_type={info.color_type}',
        ))
    return tuple(issues)


def validate_animation(
    root: str | Path,
    species_slug: str,
    state: str,
) -> tuple[SpritePackIssue, ...]:
    if state not in GEULSSIAL_ANIMATIONS:
        raise ValueError(f'unknown animation state: {state}')
    root = Path(root)
    spec = GEULSSIAL_ANIMATIONS[state]
    issues: list[SpritePackIssue] = []
    for index in range(spec.frame_count):
        issues.extend(validate_frame(root / frame_filename(species_slug, state, index)))
    return tuple(issues)


def validate_sprite_pack(
    root: str | Path,
    species_slug: str,
    *,
    required_states: tuple[str, ...] = ('idle', 'eat', 'walk'),
) -> tuple[SpritePackIssue, ...]:
    issues: list[SpritePackIssue] = []
    for state in required_states:
        issues.extend(validate_animation(root, species_slug, state))
    return tuple(issues)
