from __future__ import annotations

"""Thin real-book catalog client used by desktop recommendations.

The desktop never sends reading notes, hidden growth stats or lineage to this service. It only asks
for a generic discovery pool (or an explicit user search), then ranks those concrete books locally.
Production endpoints must use HTTPS; plain HTTP is accepted only for localhost development.
"""

from dataclasses import dataclass
import json
import os
from typing import Any, Callable
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl
from urllib.request import Request, urlopen

from .recommendations import BookCandidate

CATALOG_ENDPOINT_ENV = 'BOOKEATER_CATALOG_ENDPOINT'
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


def catalog_endpoint_from_env(environ: dict[str, str] | None = None) -> str | None:
    env = os.environ if environ is None else environ
    raw = str(env.get(CATALOG_ENDPOINT_ENV, '') or '').strip()
    return raw or None


def _append_query(url: str, **params: object) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in params.items():
        query[str(key)] = str(value)
    return urlunparse(parsed._replace(query=urlencode(query)))


def _safe_url(value: Any) -> str | None:
    text = str(value or '').strip()
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
        try:
            response = self.opener(request, timeout=max(1.0, float(self.timeout)))
            length = response.headers.get('Content-Length') if getattr(response, 'headers', None) else None
            if length and int(length) > MAX_RESPONSE_BYTES:
                raise CatalogResponseError('catalog response is too large')
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        except CatalogResponseError:
            raise
        except Exception as exc:
            raise CatalogUnavailable('catalog request failed') from exc
        if len(raw) > MAX_RESPONSE_BYTES:
            raise CatalogResponseError('catalog response is too large')
        try:
            data = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CatalogResponseError('catalog returned invalid JSON') from exc
        if not isinstance(data, dict) or not isinstance(data.get('books'), list):
            raise CatalogResponseError('catalog response must contain books list')

        out: list[BookCandidate] = []
        seen: set[str] = set()
        for raw_book in data['books']:
            if not isinstance(raw_book, dict):
                continue
            source_id = str(raw_book.get('id') or raw_book.get('source_id') or '').strip()
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
                    detail_url=_safe_url(raw_book.get('detail_url')),
                    cover_url=_safe_url(raw_book.get('cover_url')),
                    source=str(raw_book.get('source') or 'catalog').strip() or 'catalog',
                ))
            except ValueError:
                continue
        return out

    def discovery_pool(self, *, limit: int = 40) -> list[BookCandidate]:
        return self._get('v1/catalog/pool', limit=max(1, min(100, int(limit))))

    def search(self, query: str, *, limit: int = 30) -> list[BookCandidate]:
        q = str(query or '').strip()
        if not q:
            return []
        return self._get('v1/catalog/search', q=q, limit=max(1, min(100, int(limit))))


def configured_catalog_client(environ: dict[str, str] | None = None) -> CatalogClient | None:
    endpoint = catalog_endpoint_from_env(environ)
    if not endpoint:
        return None
    try:
        return CatalogClient(endpoint)
    except CatalogUnavailable:
        return None
