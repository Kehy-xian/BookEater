from __future__ import annotations

from bookeater.book_choices import book_choice_map
from bookeater.storage.journal import StoredBook


def _book(
    book_id: str,
    *,
    title: str = '같은 책',
    author: str = '같은 저자',
    publisher: str | None = None,
    isbn13: str | None = None,
) -> StoredBook:
    return StoredBook(
        book_id=book_id,
        title=title,
        author=author,
        status='reading',
        isbn13=isbn13,
        publisher=publisher,
        cover_url=None,
        source='manual',
    )


def test_unique_book_label_stays_unchanged() -> None:
    choices = book_choice_map([_book('book-1', title='오디세이아', author='호메로스')])

    assert choices == {'오디세이아 — 호메로스': 'book-1'}


def test_duplicate_display_names_never_overwrite_a_book_id() -> None:
    books = [_book('abc111-first'), _book('abc222-second')]

    choices = book_choice_map(books)

    assert list(choices.values()) == ['abc111-first', 'abc222-second']
    assert len(choices) == 2
    assert all('구분 abc' in label for label in choices)


def test_duplicate_names_use_available_metadata_before_internal_token() -> None:
    books = [
        _book('book-1', publisher='첫 출판사'),
        _book('book-2', isbn13='9781234567890'),
    ]

    choices = book_choice_map(books)

    assert choices == {
        '같은 책 — 같은 저자 · 첫 출판사': 'book-1',
        '같은 책 — 같은 저자 · ISBN 9781234567890': 'book-2',
    }


def test_same_metadata_still_produces_stable_unique_labels() -> None:
    books = [
        _book('stable-one', publisher='같은 출판사'),
        _book('stable-two', publisher='같은 출판사'),
    ]

    first = book_choice_map(books)
    second = book_choice_map(list(reversed(books)))

    assert len(first) == 2
    assert set(first.items()) == set(second.items())
