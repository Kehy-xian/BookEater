from __future__ import annotations

import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.catalog_proxy import KakaoBookProvider, ProviderUnavailable, provider_from_env


class FakeResponse:
    def __init__(self, payload: object):
        self._raw = json.dumps(payload, ensure_ascii=False).encode('utf-8')

    def read(self, limit: int):
        return self._raw[:limit]


def _doc(title='테스트 책', *, isbn='9781234567890', authors=None):
    return {
        'title': title,
        'authors': authors or ['테스트 저자'],
        'contents': '<b>책</b> 설명 &amp; 내용',
        'url': 'https://book.example/item',
        'thumbnail': 'https://img.example/cover.jpg',
        'isbn': isbn,
        'publisher': '테스트 출판사',
    }


def test_provider_requires_server_side_key():
    with pytest.raises(ProviderUnavailable):
        provider_from_env({})
    provider = provider_from_env({'KAKAO_REST_API_KEY': 'server-only-key'})
    assert provider.rest_api_key == 'server-only-key'


def test_search_uses_official_kakao_book_endpoint_and_auth_header():
    captured = {}

    def opener(request, timeout):
        captured['url'] = request.full_url
        captured['headers'] = dict(request.header_items())
        return FakeResponse({'documents': [_doc()]})

    books = KakaoBookProvider('secret-rest-key', opener=opener).search('우주 과학', limit=7)
    assert len(books) == 1
    assert books[0]['id'] == '9781234567890'
    assert books[0]['title'] == '테스트 책'
    assert books[0]['description'] == '책 설명 & 내용'
    parsed = urlparse(captured['url'])
    assert parsed.scheme == 'https'
    assert parsed.netloc == 'dapi.kakao.com'
    assert parsed.path == '/v3/search/book'
    params = parse_qs(parsed.query)
    assert params['query'] == ['우주 과학']
    assert params['size'] == ['7']
    assert captured['headers']['Authorization'] == 'KakaoAK secret-rest-key'
    assert 'secret-rest-key' not in captured['url']


def test_pool_queries_are_server_owned_and_never_contain_reader_genetics():
    queries: list[str] = []

    def opener(request, timeout):
        params = parse_qs(urlparse(request.full_url).query)
        term = params['query'][0]
        queries.append(term)
        return FakeResponse({'documents': [_doc(title=f'{term} 책', isbn=f'97800000000{len(queries):02d}') ]})

    provider = KakaoBookProvider('key', opener=opener)
    books = provider.discovery_pool(limit=20)
    assert books
    assert queries
    for term in queries:
        assert term in {'소설', '과학', '역사', '사회', '예술', '에세이', '자연', '철학'}
    joined = ' '.join(queries)
    for private_word in ('사유', '탐구', '감정', '감각', 'form_id', 'stats', 'note_text'):
        assert private_word not in joined


def test_provider_dedupes_same_isbn_and_skips_blank_titles():
    def opener(request, timeout):
        return FakeResponse({'documents': [
            _doc(title='같은 책'),
            _doc(title='같은 책 재판'),
            _doc(title=''),
            _doc(title='ISBN 없는 책', isbn=''),
        ]})

    books = KakaoBookProvider('key', opener=opener).search('테스트', limit=10)
    assert [book['title'] for book in books] == ['같은 책', 'ISBN 없는 책']
    assert books[1]['id'].startswith('kakao-')


def test_search_query_length_is_bounded_before_network_call():
    called = {'value': False}

    def opener(request, timeout):
        called['value'] = True
        return FakeResponse({'documents': []})

    provider = KakaoBookProvider('key', opener=opener)
    with pytest.raises(ValueError):
        provider.search('가' * 201)
    assert called['value'] is False
