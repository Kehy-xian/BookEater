from __future__ import annotations

"""Derive non-core animations from whichever approved core sprites are active at build time.

READ/SLEEP/TALK/SPIT_MEMORY are generated from each form's own core PNGs. This avoids a visual jump
back to vector art while keeping design hot-swappable: replacing a core pack and rebuilding also
refreshes these derived states. Hand-authored complete state packs may still replace them later.
"""

from pathlib import Path

from PIL import Image, ImageDraw

from bookeater.pet_art import GEULSSIAL_ANIMATIONS, frame_filename

DERIVED_STATES = ('read', 'sleep', 'talk', 'spit_memory')
APPROVED_SLUGS = (
    'paperling', 'pagedge', 'inknest', 'lantern',
    'route_a1', 'route_a2', 'route_b1', 'route_b2', 'route_c1', 'route_c2',
)

FACE_CENTERS: dict[str, tuple[int, int]] = {
    'paperling': (95, 93),
    'pagedge': (86, 91),
    'inknest': (95, 92),
    'lantern': (95, 93),
    'route_a1': (95, 96),
    'route_a2': (87, 96),
    'route_b1': (95, 93),
    'route_b2': (95, 96),
    'route_c1': (95, 94),
    'route_c2': (95, 94),
}

PAPER = (250, 245, 231, 255)
PAPER_EDGE = (137, 122, 99, 255)
INK = (43, 37, 32, 255)
BOOKMARK = (185, 79, 67, 255)
WARM = (255, 235, 174, 255)


def _core_path(root: Path, slug: str, state: str, index: int) -> Path:
    return root / frame_filename(slug, state, index)


def _base_idle(root: Path, slug: str, index: int) -> Image.Image:
    # Cycle through the form's own four idle frames so the derived state keeps its breathing motion.
    path = _core_path(root, slug, 'idle', index % GEULSSIAL_ANIMATIONS['idle'].frame_count)
    if not path.is_file():
        raise FileNotFoundError(f'core idle frame missing: {path.name}')
    image = Image.open(path).convert('RGBA')
    if image.size != (190, 190):
        raise ValueError(f'core sprite must be 190x190: {path.name}')
    return image


def _draw_open_book(draw: ImageDraw.ImageDraw, frame: int) -> None:
    # Foreground book is neutral/readable across all lineages and never changes the monster face.
    lift = (0, -2, -1)[frame % 3]
    y = 132 + lift
    left = [(45, y), (91, y + 9), (91, y + 35), (48, y + 27)]
    right = [(99, y + 9), (145, y), (142, y + 27), (99, y + 35)]
    draw.polygon(left, fill=PAPER, outline=PAPER_EDGE)
    draw.polygon(right, fill=PAPER, outline=PAPER_EDGE)
    draw.line((95, y + 8, 95, y + 35), fill=PAPER_EDGE, width=2)
    for dy in (10, 16, 22):
        draw.line((57, y + dy, 84, y + dy + 5), fill=(177, 163, 139, 255), width=1)
        draw.line((106, y + dy + 5, 133, y + dy), fill=(177, 163, 139, 255), width=1)
    # One small red reading marker, consistent with the family bookmark motif.
    draw.polygon([(94, y + 31), (101, y + 35), (97, y + 44), (92, y + 37)], fill=BOOKMARK)


def _draw_sleep_marks(draw: ImageDraw.ImageDraw, slug: str, frame: int) -> None:
    x, y = FACE_CENTERS[slug]
    # Do not repaint the face substrate: that could erase B2 bars or future design details.
    # A small eyelid accent plus Zs is layered safely over any visual revision.
    eye_color = WARM if slug.startswith(('inknest', 'lantern', 'route_b', 'route_c')) else INK
    offset = (0, 1, 0)[frame % 3]
    draw.line((x - 18, y - 5 + offset, x - 8, y - 5 + offset), fill=eye_color, width=2)
    draw.line((x + 8, y - 5 + offset, x + 18, y - 5 + offset), fill=eye_color, width=2)
    z = 0 if frame == 0 else (4 if frame == 1 else 8)
    draw.text((139 + z, 46 - z), 'Z', fill=(103, 95, 86, 230))
    if frame == 2:
        draw.text((151, 34), 'z', fill=(129, 120, 109, 200))


def _draw_talk_mark(draw: ImageDraw.ImageDraw, slug: str, frame: int) -> None:
    # The window draws the actual dialogue bubble. A tiny motion mark prevents a frozen sprite.
    x, y = FACE_CENTERS[slug]
    color = WARM if slug.startswith(('inknest', 'lantern', 'route_b', 'route_c')) else INK
    if frame % 2:
        draw.arc((x + 22, y - 3, x + 32, y + 8), start=280, end=80, fill=color, width=2)
    else:
        draw.arc((x + 23, y - 7, x + 36, y + 9), start=285, end=75, fill=color, width=2)


def _draw_memory_card(draw: ImageDraw.ImageDraw, slug: str, frame: int) -> None:
    x, y = FACE_CENTERS[slug]
    # Card moves out of the mouth and upward/right across four frames.
    dx = (0, 13, 27, 43)[frame]
    dy = (8, 1, -8, -18)[frame]
    cx, cy = x + dx, y + dy
    draw.rounded_rectangle((cx - 9, cy - 7, cx + 12, cy + 10), radius=3,
                           fill=PAPER, outline=PAPER_EDGE, width=1)
    draw.line((cx - 5, cy - 2, cx + 7, cy - 2), fill=(151, 138, 116, 255), width=1)
    draw.line((cx - 5, cy + 2, cx + 5, cy + 2), fill=(151, 138, 116, 255), width=1)
    draw.rectangle((cx + 5, cy - 7, cx + 12, cy - 2), fill=BOOKMARK)


def render_derived_frame(root: str | Path, slug: str, state: str, index: int) -> Image.Image:
    root = Path(root)
    if slug not in APPROVED_SLUGS:
        raise ValueError(f'unsupported approved slug: {slug}')
    if state not in DERIVED_STATES:
        raise ValueError(f'unsupported derived state: {state}')
    spec = GEULSSIAL_ANIMATIONS[state]
    if index not in range(spec.frame_count):
        raise ValueError(f'frame index out of range: {state}/{index}')

    base_index = index if state != 'spit_memory' else min(index, 3)
    image = _base_idle(root, slug, base_index)
    draw = ImageDraw.Draw(image)
    if state == 'read':
        _draw_open_book(draw, index)
    elif state == 'sleep':
        _draw_sleep_marks(draw, slug, index)
    elif state == 'talk':
        _draw_talk_mark(draw, slug, index)
    elif state == 'spit_memory':
        _draw_memory_card(draw, slug, index)
    return image


def _state_paths(root: Path, slug: str, state: str) -> tuple[Path, ...]:
    spec = GEULSSIAL_ANIMATIONS[state]
    return tuple(root / frame_filename(slug, state, i) for i in range(spec.frame_count))


def ensure_derived_state(root: str | Path, slug: str, state: str) -> str:
    """Keep a complete hand-authored state; generate only when no state files exist.

    A partial hand-authored state is a release error, because silently filling missing frames would
    mix two art revisions within one animation.
    """
    root = Path(root)
    paths = _state_paths(root, slug, state)
    existing = [path for path in paths if path.is_file()]
    if len(existing) == len(paths):
        return 'packaged'
    if existing:
        missing = [path.name for path in paths if not path.is_file()]
        raise RuntimeError(f'partial {slug}/{state} sprite state; missing={missing}')
    for index, path in enumerate(paths):
        render_derived_frame(root, slug, state, index).save(path, format='PNG', optimize=True)
    return 'derived'


def ensure_all_derived_states(root: str | Path) -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}
    for slug in APPROVED_SLUGS:
        for state in DERIVED_STATES:
            result[(slug, state)] = ensure_derived_state(root, slug, state)
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('root', nargs='?', default='resources/sprites')
    args = parser.parse_args()
    result = ensure_all_derived_states(args.root)
    generated = sum(value == 'derived' for value in result.values())
    kept = sum(value == 'packaged' for value in result.values())
    print(f'DERIVED_STATES_READY generated={generated} packaged={kept}')
