from __future__ import annotations

"""Create the private first growth imprint from an explicitly named favourite book.

The catalog receives only the typed title. The selected public metadata is analysed locally and
stored as a bookless reading entry, so it influences growth without appearing on the bookshelf.
"""

from dataclasses import dataclass
import uuid

from .catalog import CatalogClient


@dataclass(frozen=True)
class BirthImprintResult:
    status: str
    matched_title: str | None = None


def _match(title: str, candidates):
    needle = ''.join(title.casefold().split())
    exact = [item for item in candidates if ''.join(item.title.casefold().split()) == needle]
    return (exact or list(candidates) or [None])[0]


def create_birth_imprint(runtime, favorite_title: str, *, client: CatalogClient | None) -> BirthImprintResult:
    title = ' '.join(str(favorite_title or '').split())
    runtime.settings.set('favorite_book_title', title)
    if not title or client is None:
        runtime.settings.set('birth_imprint_status', 'lookup_failed')
        return BirthImprintResult('lookup_failed')
    try:
        candidate = _match(title, client.search(title, limit=10))
    except Exception:
        candidate = None
    if candidate is None:
        runtime.settings.set('birth_imprint_status', 'lookup_failed')
        return BirthImprintResult('lookup_failed')

    # Public catalog metadata only. This is deliberately not attached to a journal book.
    digest = ' '.join(part for part in (
        candidate.title,
        candidate.author,
        candidate.publisher or '',
        candidate.description,
    ) if part).strip()
    if not digest:
        runtime.settings.set('birth_imprint_status', 'lookup_failed')
        return BirthImprintResult('lookup_failed')
    feed_id = 'birth-' + uuid.uuid4().hex
    try:
        outcome = runtime.feed_service.submit(feed_id, digest)
    except Exception:
        runtime.settings.set('birth_imprint_status', 'analysis_failed')
        return BirthImprintResult('analysis_failed', candidate.title)
    runtime.settings.set('birth_imprint_feed_id', feed_id)
    runtime.settings.set('birth_imprint_status', outcome.status)
    runtime.settings.set('favorite_book_match', candidate.title)
    return BirthImprintResult(outcome.status, candidate.title)
