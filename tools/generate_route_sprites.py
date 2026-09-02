from __future__ import annotations

"""Build-time baseline sprites for the three first-evolution route bodies.

These are deliberately replaceable visual baselines. Their job is to keep each approved lineage
recognizable until final hand-authored sprite atlases replace them:
- Route A: paper/book face, never a dark core.
- Route B: crumpled paper nest around a dark ink core with light face.
- Route C: lantern shell around a warm-glowing dark core with handle and vents.
"""

from pathlib import Path

CANVAS = 190
PAPER = (244, 237, 218, 255)
PAPER_LIGHT = (251, 246, 233, 255)
PAPER_SHADE = (222, 211, 186, 255)
INK = (43, 37, 32, 255)
CORE = (38, 36, 33, 255)
OUTLINE = (70, 61, 52, 255)
BOOKMARK = (185, 79, 67, 255)
BOOKMARK_DARK = (119, 49, 43, 255)
WARM = (255, 235, 174, 255)
SHADOW = (0, 0, 0, 34)
CORE_COUNTS = {'idle': 4, 'eat': 6, 'walk': 4}


def _pose(state: str, index: int) -> tuple[int, int]:
    if state == 'idle':
        return (0, -1, -3, -1)[index], 0
    if state == 'eat':
        return (0, -2, -4, -2, 1, 0)[index], 0
    if state == 'walk':
        return (0, -2, 0, -2)[index], (-1, 1, -1, 1)[index]
    raise ValueError(state)


def _feet(draw, *, phase: int = 0) -> None:
    left = -3 if phase < 0 else (3 if phase > 0 else 0)
    right = -left
    draw.ellipse((57 + left, 134, 82 + left, 151), fill=INK, outline=OUTLINE, width=2)
    draw.ellipse((108 + right, 134, 133 + right, 151), fill=INK, outline=OUTLINE, width=2)


def _scrap(draw, index: int, target_x: int = 86, target_y: int = 97) -> None:
    start_x, start_y = 20, 58
    t = index / 5.0
    x = round(start_x + (target_x - start_x) * t)
    y = round(start_y + (target_y - start_y) * t)
    draw.polygon([(x, y), (x + 15, y - 3), (x + 17, y + 13), (x + 3, y + 16)],
                 fill=PAPER_LIGHT, outline=(151, 137, 114, 255))
    draw.line((x + 4, y + 4, x + 12, y + 2), fill=(116, 104, 88, 255), width=1)
    draw.line((x + 4, y + 8, x + 13, y + 7), fill=(116, 104, 88, 255), width=1)


def _paper_face(draw, x: int, y: int, *, mouth_open: bool) -> None:
    draw.ellipse((x - 18, y - 15, x - 8, y + 1), fill=INK)
    draw.ellipse((x + 8, y - 15, x + 18, y + 1), fill=INK)
    if mouth_open:
        draw.ellipse((x - 9, y + 5, x + 9, y + 20), fill=INK)
    else:
        draw.arc((x - 13, y + 3, x + 13, y + 17), start=195, end=345, fill=INK, width=3)


def _light_face(draw, x: int, y: int, *, mouth_open: bool, color=WARM) -> None:
    draw.ellipse((x - 18, y - 15, x - 8, y + 1), fill=color)
    draw.ellipse((x + 8, y - 15, x + 18, y + 1), fill=color)
    if mouth_open:
        draw.ellipse((x - 9, y + 5, x + 9, y + 20), fill=color)
    else:
        draw.arc((x - 13, y + 3, x + 13, y + 17), start=195, end=345, fill=color, width=3)


def _route_a(draw, state: str, index: int) -> None:
    bob, phase = _pose(state, index)
    draw.ellipse((48, 149, 142, 160), fill=SHADOW)
    _feet(draw, phase=phase)
    x, y = 92, 91 + bob

    # Layered page block behind the front cover.
    for i in range(5):
        dx = 24 + i * 5
        draw.rounded_rectangle((x - 36 + dx, y - 41 + i, x + 43 + dx, y + 42 - i),
                               radius=4, fill=(232, 222, 199, 255), outline=(174, 160, 133, 255), width=1)
    draw.polygon([(x + 19, y - 47), (x + 31, y - 60), (x + 44, y - 47), (x + 38, y - 28)],
                 fill=BOOKMARK, outline=BOOKMARK_DARK)
    draw.rounded_rectangle((x - 43, y - 43, x + 39, y + 43), radius=5,
                           fill=PAPER, outline=OUTLINE, width=3)
    draw.line((x + 29, y - 35, x + 29, y + 35), fill=(188, 174, 146, 255), width=1)
    # Small sticky-note/page details; these remain secondary to the face.
    draw.rectangle((x + 12, y - 34, x + 32, y - 19), fill=PAPER_LIGHT, outline=(184, 169, 142, 255))
    draw.line((x + 16, y - 29, x + 28, y - 29), fill=(158, 144, 121, 255), width=1)
    _paper_face(draw, x - 6, y, mouth_open=state == 'eat')
    if state == 'eat':
        _scrap(draw, index, x - 9, y + 3)


def _route_b(draw, state: str, index: int) -> None:
    bob, phase = _pose(state, index)
    draw.ellipse((46, 149, 144, 160), fill=SHADOW)
    _feet(draw, phase=phase)
    x, y = 95, 93 + bob

    draw.polygon([(x + 26, y - 52), (x + 41, y - 63), (x + 53, y - 48), (x + 43, y - 28)],
                 fill=BOOKMARK, outline=BOOKMARK_DARK)
    # Crumpled paper ring. The center is intentionally open and dark.
    ring = [(95, 35 + bob), (124, 39 + bob), (145, 57 + bob), (151, 86 + bob),
            (145, 119 + bob), (124, 139 + bob), (94, 146 + bob), (64, 139 + bob),
            (44, 119 + bob), (38, 89 + bob), (44, 59 + bob), (64, 41 + bob)]
    draw.polygon(ring, fill=PAPER, outline=OUTLINE)
    draw.line(ring + [ring[0]], fill=OUTLINE, width=3, joint='curve')
    # Facets make B visibly crumpled rather than book-layered.
    facets = [
        [(55, 55), (72, 43), (80, 61)], [(84, 42), (104, 35), (109, 56)],
        [(117, 45), (137, 57), (122, 66)], [(139, 72), (151, 88), (133, 94)],
        [(137, 106), (145, 123), (123, 121)], [(109, 128), (124, 139), (99, 145)],
        [(75, 128), (93, 145), (63, 139)], [(48, 104), (63, 121), (43, 120)],
        [(43, 75), (58, 59), (64, 81)],
    ]
    for pts in facets:
        shifted = [(px, py + bob) for px, py in pts]
        draw.polygon(shifted, fill=PAPER_SHADE, outline=(188, 172, 143, 255))
    draw.ellipse((62, 59 + bob, 128, 127 + bob), fill=CORE, outline=(20, 19, 18, 255), width=2)
    _light_face(draw, x, y - 1, mouth_open=state == 'eat', color=(250, 241, 211, 255))
    # B cheek hatches live on the dark core.
    for sx in (-1, 1):
        cx = x + sx * 25
        draw.line((cx - 2, y + 12, cx, y + 18), fill=(245, 230, 197, 255), width=1)
        draw.line((cx + 2, y + 12, cx + 4, y + 18), fill=(245, 230, 197, 255), width=1)
    if state == 'eat':
        _scrap(draw, index, x - 5, y + 3)


def _route_c(draw, state: str, index: int) -> None:
    bob, phase = _pose(state, index)
    draw.ellipse((47, 149, 143, 160), fill=SHADOW)
    _feet(draw, phase=phase)
    x, y = 95, 95 + bob

    # Metal handle distinguishes C immediately from the paper nest.
    draw.arc((67, 24 + bob, 123, 70 + bob), start=180, end=360, fill=(105, 91, 72, 255), width=5)
    draw.polygon([(x + 28, y - 52), (x + 43, y - 59), (x + 50, y - 43), (x + 39, y - 31)],
                 fill=BOOKMARK, outline=BOOKMARK_DARK)
    shell = [(67, 48 + bob), (123, 48 + bob), (140, 65 + bob), (146, 119 + bob),
             (129, 140 + bob), (61, 140 + bob), (44, 119 + bob), (50, 65 + bob)]
    draw.polygon(shell, fill=PAPER, outline=OUTLINE)
    draw.line(shell + [shell[0]], fill=OUTLINE, width=3, joint='curve')
    # Dark teardrop/window core.
    core = [(95, 61 + bob), (119, 79 + bob), (116, 119 + bob), (95, 132 + bob),
            (74, 119 + bob), (71, 79 + bob)]
    draw.polygon(core, fill=CORE, outline=(20, 19, 18, 255))
    # Lantern vents stay in the ivory shell, never across the face.
    for sx in (-1, 1):
        vx = x + sx * 35
        for vy in (77 + bob, 99 + bob):
            draw.rounded_rectangle((vx - 5, vy - 7, vx + 5, vy + 7), radius=2, fill=CORE)
    _light_face(draw, x, y - 2, mouth_open=state == 'eat')
    if state == 'eat':
        _scrap(draw, index, x - 4, y + 2)


def render_route_frame(slug: str, state: str, index: int):
    from PIL import Image, ImageDraw

    if state not in CORE_COUNTS or index not in range(CORE_COUNTS[state]):
        raise ValueError(f'invalid core state/index: {state}/{index}')
    image = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    if slug == 'pagedge':
        _route_a(draw, state, index)
    elif slug == 'inknest':
        _route_b(draw, state, index)
    elif slug == 'lantern':
        _route_c(draw, state, index)
    else:
        raise ValueError(f'unsupported route slug: {slug}')
    return image


def generate_route_core_frames(target_dir: str | Path, slug: str) -> tuple[Path, ...]:
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for state, count in CORE_COUNTS.items():
        for index in range(count):
            path = target / f'{slug}_{state}_{index:02d}.png'
            render_route_frame(slug, state, index).save(path, format='PNG', optimize=True)
            written.append(path)
    return tuple(written)


def generate_all_route_core_frames(target_dir: str | Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for slug in ('pagedge', 'inknest', 'lantern'):
        files.extend(generate_route_core_frames(target_dir, slug))
    return tuple(files)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('target', nargs='?', default='resources/sprites')
    parser.add_argument('--slug', choices=('pagedge', 'inknest', 'lantern'))
    args = parser.parse_args()
    files = (generate_route_core_frames(args.target, args.slug)
             if args.slug else generate_all_route_core_frames(args.target))
    print(f'ROUTE_BASELINES_WRITTEN={len(files)}')
