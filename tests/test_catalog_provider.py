from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.services.catalog import (
    CatalogClient,
    CatalogResponseError,
    CatalogUnavailable,
    catalog_endpoint_from_env,
    configured_catalog_client,
)


class FakeResponse:
    def __init__(self, payload: object, *, headers=None):
        self.data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.headers = headers or {}

    def read(self, limit: int):
        return self.data[:limit]


def test_catalog_requires_https_except_localhost():
    with pytest.raises(CatalogUnavailable):
        CatalogClient('http://example.com')
    assert CatalogClient('https://catalog.example.com').endpoint.startswith('https://')
    assert CatalogClient('http://localhost:8080').endpoint.startswith('http://localhost')
    with pytest.raises(CatalogUnavailable):
        CatalogClient('https://user:secret@example.com')


def test_discovery_pool_sends_no_reading_or_growth_data_and_parses_only_real_books():
    seen_urls: list[str] = []

    def opener(request, timeout):
        seen_urls.append(request.full_url)
        return FakeResponse({'books': [
            {'id': '1', 'title': '실재 책 A', 'author': '저자 A', 'description': '설명',
             'detail_url': 'https://books.example/1', 'cover_url': 'javascript:bad'},
            {'id': '1', 'title': '중복 책'},
            {'id': '', 'title': 'ID 없는 책'},
            {'id': '2', 'title': ''},
            {'id': '3', 'title': '실재 책 B', 'author': ''},
        ]})

    client = CatalogClient('https://catalog.example.com', opener=opener)
    books = client.discovery_pool(limit=20)
    assert [b.title for b in books] == ['실재 책 A', '실재 책 B']
    assert books[0].cover_url is None
    assert books[0].detail_url == 'https://books.example/1'
    assert len(seen_urls) == 1
    url = seen_urls[0]
    assert '/v1/catalog/pool' in url
    assert 'limit=20' in url
    for secretish in ('사유', '탐구', '감정', '감각', 'stats', 'note', 'form_id'):
        assert secretish not in url


def test_search_sends_only_explicit_query():
    seen = {}

    def opener(request, timeout):
        seen['url'] = request.full_url
        return FakeResponse({'books': [{'id': 'a', 'title': '검색 결과'}]})

    books = CatalogClient('https://catalog.example.com', opener=opener).search('우주 과학', limit=5)
    assert [b.title for b in books] == ['검색 결과']
    assert 'q=%EC%9A%B0%EC%A3%BC+%EA%B3%BC%ED%95%99' in seen['url']
    assert 'limit=5' in seen['url']


def test_invalid_catalog_payload_never_becomes_fake_recommendations():
    def opener(request, timeout):
        return FakeResponse({'results': [{'title': '형식 오류'}]})

    client = CatalogClient('https://catalog.example.com', opener=opener)
    with pytest.raises(CatalogResponseError):
        client.discovery_pool()


def test_unconfigured_catalog_is_cleanly_disabled(tmp_path):
    assert configured_catalog_client({}, resources=tmp_path) is None
    assert configured_catalog_client({'BOOKEATER_CATALOG_ENDPOINT': ''}, resources=tmp_path) is None


def test_release_can_read_public_endpoint_from_bundled_resource(tmp_path):
    resources = tmp_path
    endpoint_file = resources / 'resources' / 'catalog_endpoint.txt'
    endpoint_file.parent.mkdir(parents=True)
    endpoint_file.write_text(
        '# public release endpoint\nhttps://catalog.bookeater.example/\n',
        encoding='utf-8',
    )

    assert catalog_endpoint_from_env({}, resources=resources) == 'https://catalog.bookeater.example/'
    client = configured_catalog_client({}, resources=resources)
    assert client is not None
    assert client.endpoint == 'https://catalog.bookeater.example'


def test_environment_endpoint_overrides_bundled_release_endpoint(tmp_path):
    endpoint_file = tmp_path / 'resources' / 'catalog_endpoint.txt'
    endpoint_file.parent.mkdir(parents=True)
    endpoint_file.write_text('https://release.example\n', encoding='utf-8')

    client = configured_catalog_client(
        {'BOOKEATER_CATALOG_ENDPOINT': 'http://localhost:8787'},
        resources=tmp_path,
    )
    assert client is not None
    assert client.endpoint == 'http://localhost:8787'
