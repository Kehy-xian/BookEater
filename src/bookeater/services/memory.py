from __future__ import annotations

"""Local-only memory resurfacing for the desktop pet.

The service never invents a reading record. It selects only a real fed note already stored on the
user's computer, then adds a short diegetic line based on the monster's established broad route.
"""

from dataclasses import dataclass
import random

from ..game.growth_routes import get_growth_form, lineage_path
from ..storage.journal import ReadingJournalStore


@dataclass(frozen=True)
class MemoryMoment:
    book_title: str
    author: str
    note_text: str
    progress_text: str | None
    created_at: str
    monster_line: str


_LINES = {
    'starter': (
        '이 문장, 예전에 네가 내게 먹여 줬어.',
        '이건 아직도 내 안에 조그맣게 남아 있어.',
    ),
    'route_a': (
        '그때 너는 이 문장에서 꽤 오래 멈춰 있었네.',
        '이 생각은 다시 꺼내 봐도 아직 질문이 남아 있어.',
    ),
    'route_b': (
        '이 기록은 먹을 때 마음이 조금 오래 남았어.',
        '이 장면, 다시 보니까 그때의 느낌이 떠오른다.',
    ),
    'route_c': (
        '이 기록을 다른 책의 기억이랑 이어 보니까 재미있는 길이 보여.',
        '예전에 남긴 이 문장, 지금의 너라면 어디로 이어 갈까?',
    ),
}


def broad_route(form_id: str) -> str:
    try:
        form = get_growth_form(form_id)
    except ValueError:
        return 'starter'
    if form.tier < 1:
        return 'starter'
    return lineage_path(form.form_id)[1]


def choose_memory(
    journal: ReadingJournalStore,
    *,
    current_form: str = 'starter',
    rng: random.Random | None = None,
    book_limit: int = 80,
    notes_per_book: int = 120,
) -> MemoryMoment | None:
    rng = rng or random.Random()
    candidates: list[tuple[object, object]] = []
    for book in journal.list_books(limit=max(1, int(book_limit))):
        for note in journal.notes_for_book(book.book_id, limit=max(1, int(notes_per_book))):
            if note.status == 'fed' and note.note_text.strip():
                candidates.append((book, note))
    if not candidates:
        return None

    book, note = rng.choice(candidates)
    route = broad_route(current_form)
    line = rng.choice(_LINES.get(route, _LINES['starter']))
    return MemoryMoment(
        book_title=book.title,
        author=book.author,
        note_text=note.note_text,
        progress_text=note.progress_text,
        created_at=note.created_at,
        monster_line=line,
    )
