from __future__ import annotations

"""Stable art contract for the desktop pet.

The current playable build still draws a lightweight vector placeholder. This module defines
how production sprite assets will be named and discovered so art can replace that placeholder
without touching reading, growth, persistence, or NLP code.
"""

from dataclasses import dataclass
from pathlib import Path


PET_STATES = (
    'idle',
    'eat',
    'walk',
    'read',
    'sleep',
    'talk',
    'spit_memory',
    'snack',
    'delicious',
    'play',
    'wash',
    'bump',
    'drop',
)


@dataclass(frozen=True)
class PetPalette:
    paper: str = '#F4EDDA'
    paper_shadow: str = '#DED3BA'
    ink: str = '#25211E'
    outline: str = '#29241F'
    bookmark: str = '#B95F55'


@dataclass(frozen=True)
class AnimationSpec:
    state: str
    frame_count: int
    frame_ms: int
    loop: bool = True

    def __post_init__(self) -> None:
        if self.state not in PET_STATES:
            raise ValueError(f'unknown pet state: {self.state}')
        if self.frame_count <= 0:
            raise ValueError('frame_count must be positive')
        if self.frame_ms <= 0:
            raise ValueError('frame_ms must be positive')


GEULSSIAL_ANIMATIONS = {
    # Four deliberately slow frames form one 1.68-second breathing cycle. Artwork should keep
    # feet/shadow on one baseline and move/squash only the torso so the pet does not float.
    'idle': AnimationSpec('idle', 4, 420, True),
    'eat': AnimationSpec('eat', 6, 115, False),
    'walk': AnimationSpec('walk', 4, 130, True),
    'read': AnimationSpec('read', 3, 220, True),
    'sleep': AnimationSpec('sleep', 3, 420, True),
    'talk': AnimationSpec('talk', 2, 180, True),
    'spit_memory': AnimationSpec('spit_memory', 4, 145, False),
    # These states are optional in packaged art. Missing sets use the safe procedural fallback,
    # while a complete local override can replace each action without changing application code.
    'snack': AnimationSpec('snack', 6, 120, False),
    'delicious': AnimationSpec('delicious', 3, 260, False),
    'play': AnimationSpec('play', 4, 150, True),
    'wash': AnimationSpec('wash', 4, 190, True),
    'bump': AnimationSpec('bump', 3, 130, False),
    'drop': AnimationSpec('drop', 2, 120, True),
}


def frame_filename(species_slug: str, state: str, index: int) -> str:
    species_slug = str(species_slug or '').strip().lower()
    if not species_slug or any(ch not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for ch in species_slug):
        raise ValueError('species_slug must be a lowercase ASCII asset slug')
    if state not in PET_STATES:
        raise ValueError(f'unknown pet state: {state}')
    if index < 0:
        raise ValueError('frame index must not be negative')
    return f'{species_slug}_{state}_{index:02d}.png'


def expected_frame_paths(asset_root: str | Path, species_slug: str, state: str) -> tuple[Path, ...]:
    spec = GEULSSIAL_ANIMATIONS[state]
    root = Path(asset_root)
    return tuple(root / frame_filename(species_slug, state, i) for i in range(spec.frame_count))


def complete_animation_available(asset_root: str | Path, species_slug: str, state: str) -> bool:
    """Never half-load an animation; a missing frame means use the vector fallback."""
    return all(path.is_file() for path in expected_frame_paths(asset_root, species_slug, state))
