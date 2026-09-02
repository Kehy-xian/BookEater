from __future__ import annotations

"""Validation helpers for replaceable BookEater PNG sprite packs.

The validator is intentionally independent from Tk/Pillow so it can run in CI and in a packaged
build without adding image-library dependencies. Production frames use one fixed transparent RGBA
canvas; visual content inside that canvas may change freely at any time.
"""

from dataclasses import dataclass
from pathlib import Path
import struct

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


def read_png_info(path: str | Path) -> PngInfo:
    p = Path(path)
    with p.open('rb') as f:
        signature = f.read(8)
        if signature != PNG_SIGNATURE:
            raise ValueError('invalid PNG signature')
        length_raw = f.read(4)
        chunk_type = f.read(4)
        if len(length_raw) != 4 or chunk_type != b'IHDR':
            raise ValueError('PNG IHDR is missing')
        length = struct.unpack('>I', length_raw)[0]
        if length != 13:
            raise ValueError('PNG IHDR length is invalid')
        payload = f.read(13)
        if len(payload) != 13:
            raise ValueError('PNG IHDR is truncated')
        width, height, bit_depth, color_type, _compression, _filter, _interlace = struct.unpack(
            '>IIBBBBB', payload
        )
        if width <= 0 or height <= 0:
            raise ValueError('PNG dimensions must be positive')
        return PngInfo(width, height, bit_depth, color_type)


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
