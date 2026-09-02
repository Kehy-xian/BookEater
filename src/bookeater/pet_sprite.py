from __future__ import annotations

"""Route-aware production sprite discovery and Tk cache.

Concept art is never treated as a sprite. A form/state is drawable from PNG only when every
required frame exists; otherwise the desktop pet must use its vector fallback. This prevents
half-installed updates from producing frozen or missing creatures.
"""

from pathlib import Path
from typing import Any

from .game.form_catalog import catalog_entry
from .pet_art import GEULSSIAL_ANIMATIONS, complete_animation_available, expected_frame_paths

SPRITE_RELATIVE_DIR = Path('resources') / 'sprites'


def sprite_root(resource_root: str | Path) -> Path:
    return Path(resource_root) / SPRITE_RELATIVE_DIR


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
    if not slug:
        return ()
    return expected_frame_paths(sprite_root(resource_root), slug, state)


class TkSpriteCache:
    """Load Tk PhotoImages lazily and keep Python references alive for Canvas rendering."""

    def __init__(self, tk_module: Any, resource_root: str | Path):
        self.tk = tk_module
        self.resource_root = Path(resource_root)
        self._cache: dict[tuple[str, str], tuple[Any, ...] | None] = {}

    def frames(self, form_id: str, state: str) -> tuple[Any, ...] | None:
        key = (str(form_id), str(state))
        if key in self._cache:
            return self._cache[key]
        if not production_animation_available(self.resource_root, form_id, state):
            self._cache[key] = None
            return None
        try:
            images = tuple(
                self.tk.PhotoImage(file=str(path))
                for path in production_frame_paths(self.resource_root, form_id, state)
            )
        except Exception:
            # Corrupt or unsupported PNG: keep the playable vector fallback instead of crashing.
            self._cache[key] = None
            return None
        self._cache[key] = images
        return images

    def invalidate(self, form_id: str | None = None) -> None:
        if form_id is None:
            self._cache.clear()
            return
        prefix = str(form_id)
        for key in tuple(self._cache):
            if key[0] == prefix:
                self._cache.pop(key, None)
