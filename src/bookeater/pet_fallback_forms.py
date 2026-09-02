from __future__ import annotations

"""Resolve which approved silhouette may be drawn when production PNGs are unavailable.

Unapproved final forms deliberately inherit the nearest approved ancestor. This keeps placeholder
slots visually undisclosed instead of accidentally inventing a final design in code.
"""

from .game.form_catalog import catalog_entry
from .game.growth_routes import lineage_path


def approved_visual_form(form_id: str) -> str:
    """Return the nearest approved form at or above ``form_id`` in its lineage."""
    try:
        path = lineage_path(str(form_id))
    except ValueError:
        return 'starter'
    for candidate in reversed(path):
        try:
            if catalog_entry(candidate).concept_approved:
                return candidate
        except ValueError:
            continue
    return 'starter'


def fallback_family(form_id: str) -> str:
    visual = approved_visual_form(form_id)
    if visual == 'starter':
        return 'starter'
    if visual.startswith('route_a'):
        return 'a'
    if visual.startswith('route_b'):
        return 'b'
    if visual.startswith('route_c'):
        return 'c'
    return 'starter'


def fallback_variant(form_id: str) -> str:
    visual = approved_visual_form(form_id)
    if visual in {'starter', 'route_a', 'route_b', 'route_c'}:
        return 'base'
    if visual.endswith('1'):
        return '1'
    if visual.endswith('2'):
        return '2'
    return 'base'
