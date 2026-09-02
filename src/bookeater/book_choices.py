from __future__ import annotations

"""Unambiguous, local-only labels for book selection controls."""

from collections import Counter
from collections.abc import Sequence

from .storage.journal import StoredBook


def _stable_book_token(book_id: str, group_ids: Sequence[str]) -> str:
    """Return the shortest useful stable prefix without exposing a full internal id."""
    value = str(book_id)
    for length in range(min(6, len(value)), len(value) + 1):
        token = value[:length]
        if sum(str(other).startswith(token) for other in group_ids) == 1:
            return token
    return value


def book_choice_map(books: Sequence[StoredBook]) -> dict[str, str]:
    """Map unique player-facing labels to book ids while preserving input order.

    A plain title/author label remains unchanged when it is unique. Duplicate labels first use
    publisher or ISBN metadata. Records that are still indistinguishable receive a short, stable
    id token so a combobox selection can never silently resolve to another book.
    """
    base_counts = Counter(book.display_name for book in books)
    candidates: list[str] = []
    for book in books:
        base = book.display_name
        if base_counts[base] == 1:
            candidates.append(base)
            continue
        if book.publisher:
            candidates.append(f'{base} · {book.publisher}')
        elif book.isbn13:
            candidates.append(f'{base} · ISBN {book.isbn13}')
        else:
            candidates.append(base)

    candidate_counts = Counter(candidates)
    colliding_ids: dict[str, list[str]] = {}
    for book, candidate in zip(books, candidates):
        if candidate_counts[candidate] > 1:
            colliding_ids.setdefault(candidate, []).append(book.book_id)

    choices: dict[str, str] = {}
    for book, candidate in zip(books, candidates):
        label = candidate
        if candidate_counts[candidate] > 1:
            token = _stable_book_token(book.book_id, colliding_ids[candidate])
            label = f'{candidate} · 구분 {token}'
        # Defend against a pathological title that already contains one of our qualifiers.
        if label in choices:
            token = _stable_book_token(book.book_id, [item.book_id for item in books])
            root = label
            attempt = 1
            while label in choices:
                suffix = token if attempt == 1 else f'{token}-{attempt}'
                label = f'{root} · 구분 {suffix}'
                attempt += 1
        choices[label] = book.book_id
    return choices
