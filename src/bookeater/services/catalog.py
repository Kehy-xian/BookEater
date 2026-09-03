from __future__ import annotations

"""Thin real-book catalog client used by desktop recommendations.

The desktop never sends reading notes, hidden growth stats or lineage to this service. It only asks
for a generic discovery pool (or an explicit user search), then ranks those concrete books locally.
Production endpoints must use HTTPS; plain HTTP is accepted only for localhost development.

Endpoint selection is public configuration, not a credential:
1. BOOKEATER_CATALOG_ENDPOINT environment override (development/diagnostics)
2. bundled resources/catalog_endpoint.txt (normal release build)
3. no endpoint -> recommendation UI stays safely disabled
"""

from dataclasses import dataclass
import html
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl
from urllib.request import Request, urlopen

from .recommendations import BookCandidate

CATALOG_ENDPOINT_ENV = 'BOOKEATER_CATALOG_ENDPOINT'
CATALOG_ENDPOINT_FILE = Path('resources/catalog_endpoint.txt')
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class CatalogUnavailable(RuntimeError):
    pass


class CatalogResponseError(RuntimeError):
    pass


def _valid_endpoint(url: str) -> str:
    value = str(url or '').strip()
    if not value:
        raise CatalogUnavailable('catalog endpoint is not configured')
    parsed = urlparse(value)
    if parsed.username or parsed.password:
        raise CatalogUnavailable('credentials must not be embedded in desktop catalog URL')
    host = (parsed.hostname or '').lower()
    local = host in {'localhost', '127.0.0.1', '::1'}
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and local):
        raise CatalogUnavailable('catalog endpoint must use HTTPS')
    if not parsed.netloc:
        raise CatalogUnavailable('catalog endpoint is invalid')
    return value.rstrip('/')


def _resource_root() -> Path:
    bundle = getattr(sys, '_MEIPASS', None)
    if bundle:
        return Path(bundle)
    # catalog.py lives at <repo>/src/bookeater/services/catalog.py
    return Path(__file__).resolve().parents[3]


def _bundled_endpoint(resources: str | Path | None = None) -> str | None:
    root = Path(resources) if resources is not None else _resource_root()
    path = root / CATALOG_ENDPOINT_FILE
    if not path.is_file():
        return None
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    for line in lines:
        value = line.strip()
        if value and not value.startswith('#'):
            return value
    return None


def catalog_endpoint_from_env(
    environ: dict[str, str] | None = None,
    *,
    resources: str | Path | None = None,
) -> str | None:
    env = os.environ if environ is None else environ
    raw = str(env.get(CATALOG_ENDPOINT_ENV, '') or '').strip()
    if raw:
        return raw
    return _bundled_endpoint(resources)


def _append_query(url: str, **params: object) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in params.items():
        query[str(key)] = str(value)
    return urlunparse(parsed._replace(query=urlencode(query)))


def _safe_url(value: Any) -> str | None:
    text = html.unescape(str(value or '')).strip()
    if not text:
        return None
    parsed = urlparse(text)
    return text if parsed.scheme in {'https', 'http'} and parsed.netloc else None


@dataclass(frozen=True)
class CatalogClient:
    endpoint: str
    timeout: float = 6.0
    opener: Callable[..., Any] = urlopen

    def __post_init__(self) -> None:
        object.__setattr__(self, 'endpoint', _valid_endpoint(self.endpoint))

    def _get(self, path: str, **params: object) -> list[BookCandidate]:
        url = _append_query(f'{self.endpoint}/{path.lstrip("/")}', **params)
        request = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'BookEater/desktop'})
        response = None
        try:
            response = self.opener(request, timeout=max(1.0, float(self.timeout)))
            geturl = getattr(response, 'geturl', None)
            final_url = geturl() if callable(geturl) else url
            _valid_endpoint(final_url or url)
            length = response.headers.get('Content-Length') if getattr(response, 'headers', None) else None
            if length is not None:
                try:
                    declared = int(length)
                except (TypeError, ValueError) as exc:
                    raise CatalogResponseError('catalog response has an invalid Content-Length') from exc
                if declared < 0:
                    raise CatalogResponseError('catalog response has an invalid Content-Length')
                if declared > MAX_RESPONSE_BYTES:
                    raise CatalogResponseError('catalog response is too large')
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        except CatalogResponseError:
            raise
        except CatalogUnavailable:
            raise
        except Exception as exc:
            raise CatalogUnavailable('catalog request failed') from exc
        finally:
            close = getattr(response, 'close', None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
        if len(raw) > MAX_RESPONSE_BYTES:
            raise CatalogResponseError('catalog response is too large')
        try:
            data = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CatalogResponseError('catalog returned invalid JSON') from exc
        if not isinstance(data, dict):
            raise CatalogResponseError('catalog response must be an object')
        raw_books = data.get('items')
        if not isinstance(raw_books, list):
            raw_books = data.get('books')
        if not isinstance(raw_books, list):
            raise CatalogResponseError('catalog response must contain items or books list')

        out: list[BookCandidate] = []
        seen: set[str] = set()
        for raw_book in raw_books:
            if not isinstance(raw_book, dict):
                continue
            source_id = str(
                raw_book.get('id')
                or raw_book.get('source_id')
                or raw_book.get('isbn13')
                or raw_book.get('isbn')
                or ''
            ).strip()
            title = str(raw_book.get('title') or '').strip()
            if not source_id or not title or source_id in seen:
                continue
            seen.add(source_id)
            try:
                out.append(BookCandidate(
                    source_id=source_id,
                    title=title,
                    author=str(raw_book.get('author') or '').strip(),
                    description=str(raw_book.get('description') or '').strip(),
                    detail_url=_safe_url(raw_book.get('detail_url') or raw_book.get('link')),
                    cover_url=_safe_url(raw_book.get('cover_url')),
                    source=str(raw_book.get('source') or 'catalog').strip() or 'catalog',
                ))
            except ValueError:
                continue
        return out

    def discovery_pool(self, *, limit: int = 40) -> list[BookCandidate]:
        return self._get(
            'v1/books/list',
            type='Bestseller',
            max_results=max(1, min(20, int(limit))),
        )

    def search(self, query: str, *, limit: int = 30) -> list[BookCandidate]:
        q = str(query or '').strip()
        if not q:
            return []
        return self._get('v1/books/search', q=q, max_results=max(1, min(20, int(limit))))


def configured_catalog_client(
    environ: dict[str, str] | None = None,
    *,
    resources: str | Path | None = None,
) -> CatalogClient | None:
    endpoint = catalog_endpoint_from_env(environ, resources=resources)
    if not endpoint:
        return None
    try:
        return CatalogClient(endpoint)
    except CatalogUnavailable:
        return None
