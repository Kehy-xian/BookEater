from __future__ import annotations

"""Route-aware production sprite discovery and Tk cache.

Art is intentionally hot-swappable. Packaged production sprites are the stable default, while a
complete animation placed in the local ``art_overrides`` directory may replace that state without
changing reading, growth, persistence, or NLP code. We never mix partial override frames with
packaged frames: a state comes from one complete source or falls back safely.
"""

from pathlib import Path
from typing import Any

from .game.form_catalog import catalog_entry
from .pet_art import GEULSSIAL_ANIMATIONS, complete_animation_available, expected_frame_paths

SPRITE_RELATIVE_DIR = Path('resources') / 'sprites'
ART_OVERRIDE_DIRNAME = 'art_overrides'


def sprite_root(resource_root: str | Path) -> Path:
    return Path(resource_root) / SPRITE_RELATIVE_DIR


def default_override_root(data_dir: str | Path) -> Path:
    return Path(data_dir) / ART_OVERRIDE_DIRNAME


def _runtime_override_root() -> Path:
    # Lazy import keeps the sprite contract usable in isolation while making the normal desktop
    # shell automatically follow BOOKEATER_DATA_DIR / platform-local data-directory rules.
    from .runtime import default_data_dir
    return default_override_root(default_data_dir())


def asset_slug_for_form(form_id: str) -> str | None:
    return catalog_entry(form_id).asset_slug


def production_animation_available(
    resource_root: str | Path,
    form_id: str,
    state: str,
) -> bool:
    slug = asset_slug_for_form(form_id)
    if not slug or state not in GEULSSIAL_ANIMATIONS:
        return False
    return complete_animation_available(sprite_root(resource_root), slug, state)


def production_frame_paths(
    resource_root: str | Path,
    form_id: str,
    state: str,
) -> tuple[Path, ...]:
    slug = asset_slug_for_form(form_id)
    if not slug or state not in GEULSSIAL_ANIMATIONS:
        return ()
    return expected_frame_paths(sprite_root(resource_root), slug, state)


def override_animation_available(
    override_root: str | Path | None,
    form_id: str,
    state: str,
) -> bool:
    if override_root is None:
        return False
    slug = asset_slug_for_form(form_id)
    if not slug or state not in GEULSSIAL_ANIMATIONS:
        return False
    return complete_animation_available(Path(override_root), slug, state)


def override_frame_paths(
    override_root: str | Path | None,
    form_id: str,
    state: str,
) -> tuple[Path, ...]:
    if override_root is None:
        return ()
    slug = asset_slug_for_form(form_id)
    if not slug or state not in GEULSSIAL_ANIMATIONS:
        return ()
    return expected_frame_paths(Path(override_root), slug, state)


def resolved_frame_paths(
    resource_root: str | Path,
    form_id: str,
    state: str,
    *,
    override_root: str | Path | None = None,
) -> tuple[Path, ...]:
    """Return one complete animation source, preferring a local art override.

    A partial override never borrows missing frames from the packaged bundle. This makes an art
    replacement atomic at the animation-state level and keeps half-copied development assets from
    producing mixed designs on screen.
    """
    if override_animation_available(override_root, form_id, state):
        return override_frame_paths(override_root, form_id, state)
    if production_animation_available(resource_root, form_id, state):
        return production_frame_paths(resource_root, form_id, state)
    return ()


class TkSpriteCache:
    """Load Tk PhotoImages lazily and keep Python references alive for Canvas rendering."""

    def __init__(
        self,
        tk_module: Any,
        resource_root: str | Path,
        *,
        override_root: str | Path | None = None,
    ):
        self.tk = tk_module
        self.resource_root = Path(resource_root)
        self.override_root = Path(override_root) if override_root is not None else _runtime_override_root()
        self._cache: dict[tuple[str, str], tuple[Any, ...] | None] = {}

    def _try_load(self, paths: tuple[Path, ...]) -> tuple[Any, ...] | None:
        if not paths:
            return None
        try:
            return tuple(self.tk.PhotoImage(file=str(path)) for path in paths)
        except Exception:
            return None

    def frames(self, form_id: str, state: str) -> tuple[Any, ...] | None:
        key = (str(form_id), str(state))
        if key in self._cache:
            return self._cache[key]

        # A complete local override is preferred, but a corrupt PNG must not suppress a healthy
        # packaged animation. Sources are attempted atomically and never mixed frame-by-frame.
        if override_animation_available(self.override_root, form_id, state):
            images = self._try_load(override_frame_paths(self.override_root, form_id, state))
            if images is not None:
                self._cache[key] = images
                return images

        if production_animation_available(self.resource_root, form_id, state):
            images = self._try_load(production_frame_paths(self.resource_root, form_id, state))
            if images is not None:
                self._cache[key] = images
                return images

        # Both image sources are unavailable/corrupt: desktop shell will draw the vector fallback.
        self._cache[key] = None
        return None

    def invalidate(self, form_id: str | None = None) -> None:
        if form_id is None:
            self._cache.clear()
            return
        prefix = str(form_id)
        for key in tuple(self._cache):
            if key[0] == prefix:
                self._cache.pop(key, None)
