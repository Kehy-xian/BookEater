from __future__ import annotations

from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import threading
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

import server.catalog_proxy as proxy
from bookeater.services.catalog import CatalogClient
from bookeater.services.recommendations import rank_real_candidates


class FakeProvider:
    def __init__(self):
        self.search_queries: list[tuple[str, int]] = []

    @staticmethod
    def _books():
        return [
            {
                'id': 'isbn-thinking',
                'title': '생각을 잇는 실제 책',
                'author': '저자 A',
                'description': '선택의 이유를 생각하고 질문하는 이야기',
                'detail_url': 'https://books.example/thinking',
                'cover_url': 'https://books.example/thinking.jpg',
                'source': 'test-catalog',
            },
            {
                'id': 'isbn-heart',
                'title': '마음을 건너는 실제 책',
                'author': '저자 B',
                'description': '관계와 감정을 따라가는 이야기',
                'detail_url': 'https://books.example/heart',
                'cover_url': None,
                'source': 'test-catalog',
            },
            {
                'id': 'isbn-space',
                'title': '우주를 여는 실제 책',
                'author': '저자 C',
                'description': '낯선 우주와 상상의 세계를 탐험한다',
                'detail_url': 'https://books.example/space',
                'cover_url': None,
                'source': 'test-catalog',
            },
        ]

    def discovery_pool(self, *, limit: int = 40):
        return self._books()[:limit]

    def search(self, query: str, *, limit: int = 30):
        self.search_queries.append((query, limit))
        return [book for book in self._books() if query in book['title'] or query in book['description']][:limit]


class FakeAnalyzer:
    def analyze(self, text: str):
        if '생각' in text or '질문' in text:
            return {'response': ['사유'], 'world': []}
        if '마음' in text or '감정' in text:
            return {'response': ['감정'], 'world': []}
        if '우주' in text or '상상' in text:
            return {'response': [], 'world': ['상상']}
        return {}


@contextmanager
def running_proxy(monkeypatch):
    provider = FakeProvider()
    monkeypatch.setattr(proxy, 'provider_from_env', lambda environ=None: provider)
    server = ThreadingHTTPServer(('127.0.0.1', 0), proxy.CatalogHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield provider, f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_real_http_proxy_to_desktop_to_local_ranker_roundtrip(monkeypatch):
    with running_proxy(monkeypatch) as (_provider, endpoint):
        health = urlopen(endpoint + '/health', timeout=2).read().decode('utf-8')
        assert '"ok":true' in health

        client = CatalogClient(endpoint)
        candidates = client.discovery_pool(limit=20)
        assert [item.source_id for item in candidates] == [
            'isbn-thinking', 'isbn-heart', 'isbn-space'
        ]

        taste = rank_real_candidates(
            candidates,
            FakeAnalyzer(),
            {'사유': 10.0, '감정': 1.0, '상상': 0.0},
            mode='taste',
            limit=3,
        )
        expand = rank_real_candidates(
            candidates,
            FakeAnalyzer(),
            {'사유': 10.0, '감정': 1.0, '상상': 0.0},
            mode='expand',
            limit=3,
        )

        assert taste[0].candidate.source_id == 'isbn-thinking'
        assert expand[0].candidate.source_id in {'isbn-heart', 'isbn-space'}
        supplied = {candidate.source_id for candidate in candidates}
        assert {row.candidate.source_id for row in taste} <= supplied
        assert {row.candidate.source_id for row in expand} <= supplied


def test_explicit_search_roundtrip_sends_only_the_user_query(monkeypatch):
    with running_proxy(monkeypatch) as (provider, endpoint):
        client = CatalogClient(endpoint)
        books = client.search('우주', limit=5)
        assert [book.source_id for book in books] == ['isbn-space']
        assert provider.search_queries == [('우주', 5)]
