from __future__ import annotations

"""Tiny BookEater catalog proxy backed by Kakao/Daum book search.

Only this server sees ``KAKAO_REST_API_KEY``. The desktop never receives or stores that key and
never sends reading notes, hidden growth scores, lineage, or other genetic state to this server.

Public contract consumed by ``bookeater.services.catalog``:
  GET /v1/catalog/search?q=<explicit user query>&limit=30
  GET /v1/catalog/pool?limit=40

The discovery pool uses only server-owned broad seed terms. It is intentionally non-personalized;
BookEater performs personalization locally after receiving concrete, real-book candidates.
"""

from dataclasses import dataclass
from datetime import date
import hashlib
import html
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
import re
from typing import Any, Callable, Iterable
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

KAKAO_BOOK_URL = 'https://dapi.kakao.com/v3/search/book'
KAKAO_KEY_ENV = 'KAKAO_REST_API_KEY'
MAX_UPSTREAM_BYTES = 2 * 1024 * 1024
MAX_QUERY_CHARS = 200
MAX_PUBLIC_LIMIT = 100
DEFAULT_POOL_TERMS = (
    '소설', '과학', '역사', '사회', '예술', '에세이', '자연', '철학',
)
_TAG_RE = re.compile(r'<[^>]+>')


class ProviderUnavailable(RuntimeError):
    pass


class UpstreamError(RuntimeError):
    pass


def _plain(value: Any) -> str:
    text = html.unescape(str(value or ''))
    return ' '.join(_TAG_RE.sub('', text).split())


def _safe_http_url(value: Any) -> str | None:
    text = str(value or '').strip()
    if not text:
        return None
    parsed = urlparse(text)
    return text if parsed.scheme in {'http', 'https'} and parsed.netloc else None


def _isbn_id(raw: Any) -> str | None:
    tokens = re.findall(r'\d{10,13}', str(raw or ''))
    isbn13 = next((token for token in tokens if len(token) == 13), None)
    return isbn13 or (tokens[0] if tokens else None)


def _fallback_id(title: str, authors: str, detail_url: str | None) -> str:
    material = f'{title}\0{authors}\0{detail_url or ""}'.encode('utf-8')
    return 'kakao-' + hashlib.sha256(material).hexdigest()[:24]


def _public_book(document: dict[str, Any]) -> dict[str, Any] | None:
    title = _plain(document.get('title'))
    if not title:
        return None
    raw_authors = document.get('authors')
    if isinstance(raw_authors, list):
        authors = ', '.join(_plain(x) for x in raw_authors if _plain(x))
    else:
        authors = _plain(raw_authors)
    detail_url = _safe_http_url(document.get('url'))
    source_id = _isbn_id(document.get('isbn')) or _fallback_id(title, authors, detail_url)
    return {
        'id': source_id,
        'title': title,
        'author': authors,
        'description': _plain(document.get('contents')),
        'detail_url': detail_url,
        'cover_url': _safe_http_url(document.get('thumbnail')),
        'publisher': _plain(document.get('publisher')),
        'source': 'kakao-daum',
    }


@dataclass
class KakaoBookProvider:
    rest_api_key: str
    opener: Callable[..., Any] = urlopen
    timeout: float = 6.0

    def __post_init__(self) -> None:
        self.rest_api_key = str(self.rest_api_key or '').strip()
        if not self.rest_api_key:
            raise ProviderUnavailable('KAKAO_REST_API_KEY is not configured')

    def _request(self, query: str, *, size: int) -> list[dict[str, Any]]:
        query = str(query or '').strip()
        if not query:
            return []
        if len(query) > MAX_QUERY_CHARS:
            raise ValueError('query is too long')
        size = max(1, min(50, int(size)))
        url = KAKAO_BOOK_URL + '?' + urlencode({
            'query': query,
            'sort': 'accuracy',
            'page': 1,
            'size': size,
        })
        request = Request(
            url,
            headers={
                'Authorization': f'KakaoAK {self.rest_api_key}',
                'Accept': 'application/json',
                'User-Agent': 'BookEater-Catalog-Proxy/1',
            },
        )
        try:
            response = self.opener(request, timeout=max(1.0, float(self.timeout)))
            raw = response.read(MAX_UPSTREAM_BYTES + 1)
        except Exception as exc:
            raise UpstreamError('Kakao book search request failed') from exc
        if len(raw) > MAX_UPSTREAM_BYTES:
            raise UpstreamError('Kakao response is too large')
        try:
            payload = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UpstreamError('Kakao returned invalid JSON') from exc
        documents = payload.get('documents') if isinstance(payload, dict) else None
        if not isinstance(documents, list):
            raise UpstreamError('Kakao response has no documents list')
        out: list[dict[str, Any]] = []
        for item in documents:
            if not isinstance(item, dict):
                continue
            book = _public_book(item)
            if book is not None:
                out.append(book)
        return out

    @staticmethod
    def _dedupe(books: Iterable[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for book in books:
            source_id = str(book.get('id') or '')
            if not source_id or source_id in seen:
                continue
            seen.add(source_id)
            out.append(book)
            if len(out) >= limit:
                break
        return out

    def search(self, query: str, *, limit: int = 30) -> list[dict[str, Any]]:
        limit = max(1, min(MAX_PUBLIC_LIMIT, int(limit)))
        # Kakao allows at most 50 per page. The first release intentionally avoids pagination to
        # keep latency/quota predictable; public callers still receive up to 50 concrete results.
        return self._dedupe(self._request(query, size=min(50, limit)), limit)

    def discovery_pool(self, *, limit: int = 40) -> list[dict[str, Any]]:
        limit = max(1, min(MAX_PUBLIC_LIMIT, int(limit)))
        terms = list(DEFAULT_POOL_TERMS)
        # Rotate only the server-owned broad terms by week/day so every client does not always see
        # the same category first. No user profile or request history participates.
        offset = date.today().toordinal() % len(terms)
        terms = terms[offset:] + terms[:offset]
        each = max(2, min(12, math.ceil(limit / len(terms))))
        batches: list[list[dict[str, Any]]] = []
        for term in terms:
            try:
                batches.append(self._request(term, size=each))
            except UpstreamError:
                # A partial broad pool is still valid if another generic query succeeded.
                batches.append([])

        # Round-robin categories rather than exhausting one query first.
        mixed: list[dict[str, Any]] = []
        for index in range(max((len(batch) for batch in batches), default=0)):
            for batch in batches:
                if index < len(batch):
                    mixed.append(batch[index])
        return self._dedupe(mixed, limit)


def provider_from_env(environ: dict[str, str] | None = None) -> KakaoBookProvider:
    env = os.environ if environ is None else environ
    return KakaoBookProvider(str(env.get(KAKAO_KEY_ENV, '') or ''))


def _limit(values: dict[str, list[str]], default: int) -> int:
    raw = (values.get('limit') or values.get('max_results') or [str(default)])[0]
    try:
        return max(1, min(MAX_PUBLIC_LIMIT, int(raw)))
    except (TypeError, ValueError):
        return default


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


class CatalogHandler(BaseHTTPRequestHandler):
    server_version = 'BookEaterCatalog/1'

    def _send(self, status: int, payload: object) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
        parsed = urlparse(self.path)
        if parsed.path == '/health':
            self._send(HTTPStatus.OK, {'ok': True, 'provider': 'kakao-daum'})
            return
        try:
            provider = provider_from_env()
        except ProviderUnavailable:
            self._send(HTTPStatus.SERVICE_UNAVAILABLE, {'error': 'catalog_not_configured'})
            return

        params = parse_qs(parsed.query, keep_blank_values=True)
        try:
            if parsed.path in {'/v1/catalog/search', '/v1/books/search'}:
                query = (params.get('q') or [''])[0].strip()
                if not query:
                    self._send(HTTPStatus.BAD_REQUEST, {'error': 'query_required'})
                    return
                books = provider.search(query, limit=_limit(params, 30))
            elif parsed.path in {'/v1/catalog/pool', '/v1/books/list'}:
                books = provider.discovery_pool(limit=_limit(params, 40))
            else:
                self._send(HTTPStatus.NOT_FOUND, {'error': 'not_found'})
                return
        except ValueError:
            self._send(HTTPStatus.BAD_REQUEST, {'error': 'invalid_request'})
            return
        except UpstreamError:
            self._send(HTTPStatus.BAD_GATEWAY, {'error': 'catalog_upstream_failed'})
            return
        self._send(HTTPStatus.OK, {'books': books})

    def do_POST(self) -> None:  # noqa: N802
        self._send(HTTPStatus.METHOD_NOT_ALLOWED, {'error': 'method_not_allowed'})

    def log_message(self, format: str, *args: object) -> None:
        # Keep the tiny dev server quiet by default. Production hosting should use structured logs
        # and must never log the Kakao key (which is header-only and never returned).
        return


def main() -> int:
    host = os.environ.get('BOOKEATER_CATALOG_HOST', '127.0.0.1')
    port = int(os.environ.get('BOOKEATER_CATALOG_PORT', '8787'))
    # Validate credentials at startup rather than accepting traffic that can never succeed.
    provider_from_env()
    server = ThreadingHTTPServer((host, port), CatalogHandler)
    print(f'BookEater catalog proxy listening on http://{host}:{port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
