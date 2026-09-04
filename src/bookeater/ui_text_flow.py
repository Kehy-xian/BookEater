from __future__ import annotations

"""Shared pacing and keyboard rules for story-like popup text."""


TYPEWRITER_DELAY_MS = 84
_TEXT_INPUT_CLASSES = frozenset({'Entry', 'TEntry', 'Text'})


def typewriter_prefix(message: str, index: int) -> str:
    """Return a paced prefix with a blank visual line between authored lines."""
    return str(message)[:max(0, int(index))].replace('\n', '\n\n')


def space_can_advance(widget_class: str | None) -> bool:
    """Never steal Space from a title, name, or free-writing input."""
    return str(widget_class or '') not in _TEXT_INPUT_CLASSES
