from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.services.birth_imprint import create_birth_imprint
from bookeater.services.recommendations import BookCandidate


class Settings:
    def __init__(self): self.values = {}
    def set(self, key, value): self.values[key] = value


class Feed:
    def __init__(self): self.calls = []
    def submit(self, feed_id, text):
        self.calls.append((feed_id, text))
        return SimpleNamespace(status='fed')


class Catalog:
    def search(self, query, *, limit):
        assert query == '어린 왕자'
        return [BookCandidate(
            source_id='9780000000000', title='어린 왕자', author='생텍쥐페리',
            description='낯선 별을 여행하며 관계와 책임을 생각하는 이야기',
            detail_url=None, cover_url=None, source='aladin', isbn13='9780000000000',
            publisher='테스트 출판사',
        )]


def runtime():
    return SimpleNamespace(settings=Settings(), feed_service=Feed())


def test_birth_imprint_uses_catalog_metadata_as_bookless_hidden_feed():
    app = runtime()
    result = create_birth_imprint(app, ' 어린  왕자 ', client=Catalog())
    assert result.status == 'fed'
    assert app.settings.values['favorite_book_title'] == '어린 왕자'
    assert app.settings.values['favorite_book_match'] == '어린 왕자'
    assert len(app.feed_service.calls) == 1
    feed_id, digest = app.feed_service.calls[0]
    assert feed_id.startswith('birth-')
    assert '낯선 별을 여행' in digest


def test_failed_lookup_keeps_title_without_inventing_genetics():
    app = runtime()
    result = create_birth_imprint(app, '없는 책', client=None)
    assert result.status == 'lookup_failed'
    assert app.settings.values['favorite_book_title'] == '없는 책'
    assert app.feed_service.calls == []
