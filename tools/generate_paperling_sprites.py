from __future__ import annotations

"""Build-time Paperling sprite generator.

This is deliberately a replaceable baseline, not a permanent art lock. It preserves the approved
starter identity (paper egg, folded corner, ink face, dark feet, red bookmark tail) while letting a
later approved atlas or user art override replace it without touching gameplay code.
"""

from pathlib import Path

CANVAS = 190
PAPER = (244, 237, 218, 255)
PAPER_SHADE = (222, 211, 186, 255)
PAPER_LIGHT = (251, 246, 233, 255)
INK = (43, 37, 32, 255)
OUTLINE = (70, 61, 52, 255)
BOOKMARK = (185, 79, 67, 255)
BOOKMARK_DARK = (119, 49, 43, 255)
SHADOW = (0, 0, 0, 34)


def _draw_base(draw, *, bob: int = 0, foot_phase: int = 0, mouth_open: bool = False) -> None:
    # Shadow stays pinned so idle motion reads as breathing instead of floating.
    draw.ellipse((48, 148, 142, 160), fill=SHADOW)

    y = bob
    left_foot = -2 if foot_phase < 0 else (2 if foot_phase > 0 else 0)
    right_foot = -left_foot
    draw.ellipse((58 + left_foot, 133, 82 + left_foot, 151), fill=INK, outline=OUTLINE, width=2)
    draw.ellipse((109 + right_foot, 133, 133 + right_foot, 151), fill=INK, outline=OUTLINE, width=2)

    # Red bookmark tail behind the body.
    tail = [(130, 94 + y), (161, 101 + y), (153, 111 + y), (163, 119 + y), (129, 112 + y)]
    draw.polygon(tail, fill=BOOKMARK, outline=BOOKMARK_DARK)
    draw.line((134, 99 + y, 153, 104 + y), fill=(224, 139, 116, 255), width=2)

    # Slightly asymmetric paper egg silhouette.
    body = [(94, 31 + y), (119, 35 + y), (137, 52 + y), (146, 78 + y),
            (143, 111 + y), (132, 132 + y), (112, 142 + y), (80, 142 + y),
            (57, 133 + y), (45, 112 + y), (42, 83 + y), (49, 56 + y),
            (67, 39 + y)]
    draw.polygon(body, fill=PAPER, outline=OUTLINE)
    draw.line(body + [body[0]], fill=OUTLINE, width=3, joint='curve')

    # Folded top-right paper corner.
    fold = [(92, 31 + y), (119, 35 + y), (112, 58 + y), (91, 47 + y)]
    draw.polygon(fold, fill=PAPER_LIGHT, outline=(174, 158, 130, 255))
    draw.line((91, 47 + y, 112, 58 + y), fill=(189, 172, 143, 255), width=2)

    # Small torn/folded side crease.
    side_fold = [(137, 93 + y), (125, 99 + y), (138, 108 + y), (126, 114 + y)]
    draw.polygon(side_fold, fill=PAPER_SHADE, outline=(176, 158, 132, 255))

    # Eyes and eyebrows keep the starter face distinct from B/C dark-core faces.
    draw.ellipse((67, 76 + y, 78, 96 + y), fill=INK)
    draw.ellipse((111, 76 + y, 122, 96 + y), fill=INK)
    draw.line((65, 67 + y, 73, 64 + y), fill=INK, width=3)
    draw.line((115, 64 + y, 123, 68 + y), fill=INK, width=3)

    if mouth_open:
        draw.ellipse((87, 101 + y, 104, 119 + y), fill=INK)
        draw.ellipse((91, 104 + y, 100, 110 + y), fill=(110, 49, 43, 255))
    else:
        # W-shaped wavy mouth.
        pts = [(77, 105 + y), (83, 111 + y), (90, 104 + y), (97, 111 + y),
               (104, 104 + y), (111, 110 + y)]
        draw.line(pts, fill=INK, width=4, joint='curve')

    # Cheek hatches.
    for x in (57, 62, 128, 133):
        draw.line((x, 101 + y, x - 2, 108 + y), fill=INK, width=2)


def _draw_scrap(draw, phase: int, *, bob: int = 0) -> None:
    # A tiny text scrap moves toward the mouth over the six eating frames.
    xs = (30, 43, 55, 66, 78, 87)
    ys = (60, 64, 69, 78, 89, 98)
    x, y = xs[phase], ys[phase]
    draw.polygon([(x, y), (x + 18, y - 4), (x + 20, y + 16), (x + 3, y + 18)],
                 fill=PAPER_LIGHT, outline=(151, 137, 114, 255))
    draw.line((x + 5, y + 4, x + 15, y + 2), fill=(116, 104, 88, 255), width=1)
    draw.line((x + 5, y + 8, x + 14, y + 7), fill=(116, 104, 88, 255), width=1)
    if phase >= 4:
        draw.text((x - 5, y - 8), 'A', fill=INK)


def render_frame(state: str, index: int):
    from PIL import Image, ImageDraw

    image = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    if state == 'idle':
        bobs = (0, -1, -3, -1)
        _draw_base(draw, bob=bobs[index])
    elif state == 'eat':
        bobs = (0, -2, -4, -2, 1, 0)
        _draw_base(draw, bob=bobs[index], mouth_open=True)
        _draw_scrap(draw, index, bob=bobs[index])
    elif state == 'walk':
        bobs = (0, -2, 0, -2)
        phases = (-1, 1, -1, 1)
        _draw_base(draw, bob=bobs[index], foot_phase=phases[index])
    else:
        raise ValueError(f'unsupported core starter state: {state}')
    return image


def generate_paperling_core_frames(target_dir: str | Path) -> tuple[Path, ...]:
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    counts = {'idle': 4, 'eat': 6, 'walk': 4}
    written: list[Path] = []
    for state, count in counts.items():
        for index in range(count):
            path = target / f'paperling_{state}_{index:02d}.png'
            render_frame(state, index).save(path, format='PNG', optimize=True)
            written.append(path)
    return tuple(written)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('target', nargs='?', default='resources/sprites')
    args = parser.parse_args()
    files = generate_paperling_core_frames(args.target)
    print(f'PAPERLING_BASELINE_WRITTEN={len(files)}')
