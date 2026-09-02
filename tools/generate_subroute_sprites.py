from __future__ import annotations

"""Build-time baselines for the six approved second-evolution silhouettes.

The art remains replaceable. These generators encode only the currently approved identity and
lineage rules so a playable build never substitutes another route's face while hand-authored
sprite sheets are still being refined.
"""

from pathlib import Path

from generate_route_sprites import (
    BOOKMARK,
    BOOKMARK_DARK,
    CORE,
    CORE_COUNTS,
    INK,
    OUTLINE,
    PAPER,
    PAPER_LIGHT,
    PAPER_SHADE,
    SHADOW,
    WARM,
    _feet,
    _light_face,
    _paper_face,
    _pose,
    _scrap,
)

CANVAS = 190


def _a1(draw, state: str, index: int) -> None:
    """Contemplative folded triangular form; light paper face, never a dark core."""
    bob, phase = _pose(state, index)
    draw.ellipse((50, 150, 140, 160), fill=SHADOW)
    _feet(draw, phase=phase)
    x, y = 95, 96 + bob

    # Red quill/bookmark emerging from the folded crown.
    draw.polygon([(x - 2, y - 63), (x + 9, y - 82), (x + 14, y - 60), (x + 4, y - 43)],
                 fill=BOOKMARK, outline=BOOKMARK_DARK)
    draw.line((x + 3, y - 64, x + 10, y - 77), fill=(228, 137, 113, 255), width=2)

    # Fundamental triangular silhouette with layered folds.
    outer = [(x, y - 57), (x + 48, y + 38), (x + 25, y + 47), (x, y + 41),
             (x - 25, y + 47), (x - 48, y + 38)]
    draw.polygon(outer, fill=PAPER, outline=OUTLINE)
    draw.line(outer + [outer[0]], fill=OUTLINE, width=3, joint='curve')
    draw.polygon([(x - 48, y + 38), (x - 18, y - 7), (x, y + 13), (x - 7, y + 41)],
                 fill=PAPER_SHADE, outline=(186, 170, 142, 255))
    draw.polygon([(x + 48, y + 38), (x + 18, y - 7), (x, y + 13), (x + 7, y + 41)],
                 fill=PAPER_LIGHT, outline=(186, 170, 142, 255))

    # Calm closed-eye identity; eating temporarily opens the mouth but keeps A face style.
    if state == 'eat':
        draw.ellipse((x - 18, y - 17, x - 8, y - 5), fill=INK)
        draw.ellipse((x + 8, y - 17, x + 18, y - 5), fill=INK)
        draw.ellipse((x - 8, y + 1, x + 8, y + 15), fill=INK)
        _scrap(draw, index, x - 5, y)
    else:
        draw.arc((x - 20, y - 19, x - 6, y - 8), start=190, end=350, fill=INK, width=3)
        draw.arc((x + 6, y - 19, x + 20, y - 8), start=190, end=350, fill=INK, width=3)
        draw.arc((x - 8, y, x + 8, y + 10), start=195, end=345, fill=INK, width=2)
    # Tiny clasp/hands reinforce the meditative pose without changing face lineage.
    draw.ellipse((x - 9, y + 20, x + 1, y + 30), fill=INK)
    draw.ellipse((x - 1, y + 20, x + 9, y + 30), fill=INK)


def _a2(draw, state: str, index: int) -> None:
    """Curious page-ear book form; light paper face, lively silhouette."""
    bob, phase = _pose(state, index)
    draw.ellipse((47, 149, 143, 160), fill=SHADOW)
    _feet(draw, phase=phase)
    x, y = 92, 96 + bob

    # Large page ears are the main silhouette change.
    draw.polygon([(x - 30, y - 42), (x - 23, y - 78), (x - 6, y - 49)],
                 fill=PAPER_LIGHT, outline=OUTLINE)
    draw.polygon([(x + 7, y - 49), (x + 27, y - 80), (x + 34, y - 42)],
                 fill=PAPER_LIGHT, outline=OUTLINE)
    draw.line((x - 22, y - 69, x - 12, y - 53), fill=(181, 166, 140, 255), width=1)
    draw.line((x + 18, y - 68, x + 28, y - 52), fill=(181, 166, 140, 255), width=1)

    # Page fan along the back/right.
    for i in range(5):
        draw.polygon([(x + 24 + i * 5, y - 32 + i), (x + 58 + i * 3, y - 19 + i * 3),
                      (x + 29 + i * 5, y + 34 - i)],
                     fill=(232, 222, 199, 255), outline=(174, 160, 133, 255))
    draw.polygon([(x + 13, y - 45), (x + 26, y - 57), (x + 37, y - 43), (x + 31, y - 26)],
                 fill=BOOKMARK, outline=BOOKMARK_DARK)
    draw.rounded_rectangle((x - 43, y - 42, x + 37, y + 41), radius=5,
                           fill=PAPER, outline=OUTLINE, width=3)
    _paper_face(draw, x - 5, y, mouth_open=state == 'eat')
    if state == 'eat':
        _scrap(draw, index, x - 7, y + 3)


def _b1(draw, state: str, index: int) -> None:
    """Shaggy hooded crumple form; B's dark core face remains exposed."""
    bob, phase = _pose(state, index)
    draw.ellipse((44, 150, 146, 160), fill=SHADOW)
    _feet(draw, phase=phase)
    x, y = 95, 96 + bob

    draw.polygon([(x + 28, y - 56), (x + 43, y - 67), (x + 54, y - 50), (x + 43, y - 31)],
                 fill=BOOKMARK, outline=BOOKMARK_DARK)
    hood = [(x, y - 59), (x + 28, y - 53), (x + 48, y - 34), (x + 58, y - 7),
            (x + 52, y + 35), (x + 34, y + 49), (x + 13, y + 40),
            (x, y + 51), (x - 13, y + 40), (x - 34, y + 49),
            (x - 52, y + 35), (x - 58, y - 7), (x - 48, y - 34), (x - 28, y - 53)]
    draw.polygon(hood, fill=PAPER, outline=OUTLINE)
    draw.line(hood + [hood[0]], fill=OUTLINE, width=3, joint='curve')
    # Torn layered hem/hood facets.
    for dx, dy in ((-43, -25), (-24, -45), (8, -48), (36, -29), (-48, 13), (43, 13), (-29, 36), (25, 37)):
        draw.polygon([(x + dx - 8, y + dy), (x + dx + 2, y + dy - 10), (x + dx + 12, y + dy + 6)],
                     fill=PAPER_SHADE, outline=(186, 170, 142, 255))
    draw.ellipse((x - 32, y - 34, x + 32, y + 30), fill=CORE, outline=(20, 19, 18, 255), width=2)
    _light_face(draw, x, y - 3, mouth_open=state == 'eat', color=(250, 241, 211, 255))
    if state == 'eat':
        _scrap(draw, index, x - 4, y)


def _b2(draw, state: str, index: int) -> None:
    """Enclosed crumpled shell with barred round window; same B core face behind it."""
    bob, phase = _pose(state, index)
    draw.ellipse((48, 150, 142, 160), fill=SHADOW)
    _feet(draw, phase=phase)
    x, y = 95, 96 + bob

    draw.polygon([(x + 21, y - 58), (x + 36, y - 69), (x + 48, y - 53), (x + 38, y - 34)],
                 fill=BOOKMARK, outline=BOOKMARK_DARK)
    shell = [(x, y - 61), (x + 30, y - 54), (x + 50, y - 29), (x + 55, y + 13),
             (x + 40, y + 45), (x, y + 53), (x - 40, y + 45), (x - 55, y + 13),
             (x - 50, y - 29), (x - 30, y - 54)]
    draw.polygon(shell, fill=PAPER, outline=OUTLINE)
    draw.line(shell + [shell[0]], fill=OUTLINE, width=3, joint='curve')
    # Broad folded bands wrap the shell.
    draw.line((x - 46, y - 25, x + 39, y - 45), fill=(185, 169, 141, 255), width=4)
    draw.line((x - 49, y + 33, x + 50, y + 13), fill=(185, 169, 141, 255), width=4)

    draw.ellipse((x - 30, y - 28, x + 30, y + 31), fill=CORE, outline=(116, 99, 79, 255), width=5)
    # Window bars are part of B2's shell, not another route's face.
    draw.line((x, y - 27, x, y + 30), fill=(194, 176, 145, 255), width=4)
    draw.line((x - 29, y + 1, x + 29, y + 1), fill=(194, 176, 145, 255), width=4)
    # Eyes remain visible behind the bars.
    draw.ellipse((x - 19, y - 16, x - 9, y - 2), fill=(250, 241, 211, 255))
    draw.ellipse((x + 9, y - 16, x + 19, y - 2), fill=(250, 241, 211, 255))
    if state == 'eat':
        draw.ellipse((x - 8, y + 10, x + 8, y + 24), fill=(250, 241, 211, 255))
        _scrap(draw, index, x - 5, y + 5)


def _c1(draw, state: str, index: int) -> None:
    """Petal/leaf lantern form with the same warm C core face."""
    bob, phase = _pose(state, index)
    draw.ellipse((43, 150, 147, 160), fill=SHADOW)
    _feet(draw, phase=phase)
    x, y = 95, 96 + bob

    draw.arc((68, 21 + bob, 122, 67 + bob), start=180, end=360, fill=(105, 91, 72, 255), width=5)
    draw.polygon([(x + 26, y - 55), (x + 41, y - 63), (x + 48, y - 47), (x + 38, y - 32)],
                 fill=BOOKMARK, outline=BOOKMARK_DARK)
    # Large petals fundamentally widen the silhouette.
    petals = [
        [(x - 35, y - 12), (x - 66, y - 42), (x - 55, y + 9)],
        [(x - 29, y + 13), (x - 61, y + 42), (x - 19, y + 40)],
        [(x + 35, y - 12), (x + 66, y - 42), (x + 55, y + 9)],
        [(x + 29, y + 13), (x + 61, y + 42), (x + 19, y + 40)],
    ]
    for pts in petals:
        draw.polygon(pts, fill=PAPER_LIGHT, outline=(178, 163, 137, 255))
    shell = [(x - 32, y - 47), (x + 32, y - 47), (x + 43, y - 28),
             (x + 37, y + 39), (x, y + 49), (x - 37, y + 39), (x - 43, y - 28)]
    draw.polygon(shell, fill=PAPER, outline=OUTLINE)
    draw.line(shell + [shell[0]], fill=OUTLINE, width=3, joint='curve')
    core = [(x, y - 35), (x + 24, y - 17), (x + 21, y + 27), (x, y + 38),
            (x - 21, y + 27), (x - 24, y - 17)]
    draw.polygon(core, fill=CORE, outline=(20, 19, 18, 255))
    _light_face(draw, x, y - 2, mouth_open=state == 'eat')
    if state == 'eat':
        _scrap(draw, index, x - 4, y + 2)


def _c2(draw, state: str, index: int) -> None:
    """Tall sheltered scholar-lantern form; warm core remains visible in front."""
    bob, phase = _pose(state, index)
    draw.ellipse((48, 150, 142, 160), fill=SHADOW)
    _feet(draw, phase=phase)
    x, y = 95, 96 + bob

    draw.arc((69, 17 + bob, 121, 65 + bob), start=180, end=360, fill=(105, 91, 72, 255), width=5)
    draw.polygon([(x + 27, y - 59), (x + 40, y - 66), (x + 48, y - 51), (x + 39, y - 35)],
                 fill=BOOKMARK, outline=BOOKMARK_DARK)
    # Scalloped cap + long bell cloak create a distinct taller silhouette.
    draw.pieslice((x - 37, y - 62, x + 37, y - 30), start=180, end=360,
                  fill=PAPER_SHADE, outline=OUTLINE, width=2)
    shell = [(x - 34, y - 44), (x + 34, y - 44), (x + 43, y + 38),
             (x + 24, y + 49), (x, y + 44), (x - 24, y + 49), (x - 43, y + 38)]
    draw.polygon(shell, fill=PAPER, outline=OUTLINE)
    draw.line(shell + [shell[0]], fill=OUTLINE, width=3, joint='curve')
    core = [(x, y - 31), (x + 23, y - 15), (x + 20, y + 25), (x, y + 36),
            (x - 20, y + 25), (x - 23, y - 15)]
    draw.polygon(core, fill=CORE, outline=(20, 19, 18, 255))
    for sx in (-1, 1):
        draw.rectangle((x + sx * 33 - 4, y - 12, x + sx * 33 + 4, y + 2), fill=CORE)
    _light_face(draw, x, y - 2, mouth_open=state == 'eat')
    # Small hanging story token, secondary and removable in later art revisions.
    draw.line((x + 43, y - 20, x + 48, y + 8), fill=(112, 95, 72, 255), width=2)
    draw.rectangle((x + 43, y + 6, x + 54, y + 19), fill=PAPER_LIGHT, outline=(112, 95, 72, 255))
    if state == 'eat':
        _scrap(draw, index, x - 4, y + 2)


_DRAWERS = {
    'route_a1': _a1,
    'route_a2': _a2,
    'route_b1': _b1,
    'route_b2': _b2,
    'route_c1': _c1,
    'route_c2': _c2,
}


def render_subroute_frame(slug: str, state: str, index: int):
    from PIL import Image, ImageDraw

    if slug not in _DRAWERS:
        raise ValueError(f'unsupported subroute slug: {slug}')
    if state not in CORE_COUNTS or index not in range(CORE_COUNTS[state]):
        raise ValueError(f'invalid core state/index: {state}/{index}')
    image = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    _DRAWERS[slug](draw, state, index)
    return image


def generate_subroute_core_frames(target_dir: str | Path, slug: str) -> tuple[Path, ...]:
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for state, count in CORE_COUNTS.items():
        for index in range(count):
            path = target / f'{slug}_{state}_{index:02d}.png'
            render_subroute_frame(slug, state, index).save(path, format='PNG', optimize=True)
            written.append(path)
    return tuple(written)


def generate_all_subroute_core_frames(target_dir: str | Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for slug in _DRAWERS:
        files.extend(generate_subroute_core_frames(target_dir, slug))
    return tuple(files)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('target', nargs='?', default='resources/sprites')
    parser.add_argument('--slug', choices=tuple(_DRAWERS))
    args = parser.parse_args()
    files = (generate_subroute_core_frames(args.target, args.slug)
             if args.slug else generate_all_subroute_core_frames(args.target))
    print(f'SUBROUTE_BASELINES_WRITTEN={len(files)}')
