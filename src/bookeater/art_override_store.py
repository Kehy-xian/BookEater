from __future__ import annotations

"""Versioned, replaceable art packs for the desktop pet.

A new design is staged into an immutable revision directory and becomes visible only after a tiny
active-pointer file is atomically replaced. Failed validation/copy never mutates the active pack.
This is deliberately independent from reading history and evolution persistence.
"""

from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import uuid

from .pet_art import GEULSSIAL_ANIMATIONS, frame_filename
from .sprite_validation import SpritePackIssue, validate_sprite_pack

PACKS_DIRNAME = '.packs'
ACTIVE_DIRNAME = '.active'
_REVISION_RE = re.compile(r'^[0-9a-f]{32}$')


class SpritePackValidationError(ValueError):
    def __init__(self, issues: tuple[SpritePackIssue, ...]):
        self.issues = issues
        super().__init__(f'sprite pack has {len(issues)} validation issue(s)')


@dataclass(frozen=True)
class InstalledSpritePack:
    slug: str
    revision: str
    pack_root: Path
    states: tuple[str, ...]


def _validate_slug(slug: str) -> str:
    slug = str(slug or '').strip().lower()
    # Reuse the canonical filename validation rather than maintaining a second slug grammar.
    frame_filename(slug, 'idle', 0)
    return slug


def _validate_states(states: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(str(s).strip() for s in states if str(s).strip()))
    if not normalized:
        raise ValueError('at least one animation state is required')
    unknown = [s for s in normalized if s not in GEULSSIAL_ANIMATIONS]
    if unknown:
        raise ValueError(f'unknown animation state(s): {", ".join(unknown)}')
    return normalized


def _pointer_path(override_root: Path, slug: str) -> Path:
    return override_root / ACTIVE_DIRNAME / f'{slug}.txt'


def active_pack_root(override_root: str | Path, slug: str) -> Path | None:
    """Resolve the immutable active revision directory, ignoring malformed pointers safely."""
    root = Path(override_root)
    slug = _validate_slug(slug)
    pointer = _pointer_path(root, slug)
    try:
        revision = pointer.read_text(encoding='ascii').strip()
    except OSError:
        return None
    if not _REVISION_RE.fullmatch(revision):
        return None
    candidate = root / PACKS_DIRNAME / slug / revision
    return candidate if candidate.is_dir() else None


def override_source_root(override_root: str | Path, slug: str) -> Path:
    """Use the active versioned pack when present, otherwise support the legacy flat directory."""
    root = Path(override_root)
    return active_pack_root(root, slug) or root


def _copy_existing_active(old_root: Path | None, new_root: Path) -> None:
    if old_root is None:
        return
    for source in old_root.iterdir():
        if source.is_file() and source.suffix.lower() == '.png':
            shutil.copy2(source, new_root / source.name)


def _copy_state(source_root: Path, target_root: Path, slug: str, state: str) -> None:
    spec = GEULSSIAL_ANIMATIONS[state]
    for index in range(spec.frame_count):
        name = frame_filename(slug, state, index)
        shutil.copy2(source_root / name, target_root / name)


def install_sprite_pack(
    source_root: str | Path,
    override_root: str | Path,
    slug: str,
    *,
    states: tuple[str, ...] = ('idle', 'eat', 'walk'),
) -> InstalledSpritePack:
    """Validate, stage, revalidate, then atomically activate a design revision.

    Existing active states are copied forward before selected states are overlaid, so a later
    single-state art tweak does not discard other already-installed animations.
    """
    source = Path(source_root)
    root = Path(override_root)
    slug = _validate_slug(slug)
    states = _validate_states(states)

    issues = validate_sprite_pack(source, slug, required_states=states)
    if issues:
        raise SpritePackValidationError(issues)

    revision = uuid.uuid4().hex
    pack_parent = root / PACKS_DIRNAME / slug
    pack_root = pack_parent / revision
    active_dir = root / ACTIVE_DIRNAME
    pack_parent.mkdir(parents=True, exist_ok=True)
    active_dir.mkdir(parents=True, exist_ok=True)

    # Build a complete immutable revision before exposing it through the active pointer.
    pack_root.mkdir(parents=False, exist_ok=False)
    try:
        _copy_existing_active(active_pack_root(root, slug), pack_root)
        for state in states:
            _copy_state(source, pack_root, slug, state)

        # Revalidate the copied bytes, not only the source, before activation.
        copied_issues = validate_sprite_pack(pack_root, slug, required_states=states)
        if copied_issues:
            raise SpritePackValidationError(copied_issues)

        pointer = _pointer_path(root, slug)
        pointer_tmp = active_dir / f'.{slug}.{revision}.tmp'
        pointer_tmp.write_text(revision + '\n', encoding='ascii')
        os.replace(pointer_tmp, pointer)
    except Exception:
        shutil.rmtree(pack_root, ignore_errors=True)
        raise

    return InstalledSpritePack(slug, revision, pack_root, states)
