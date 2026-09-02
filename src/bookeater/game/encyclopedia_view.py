from __future__ import annotations

"""Pure player-facing presentation model for the 22-slot growth encyclopedia."""

from dataclasses import dataclass
from typing import Iterable

from .form_catalog import catalog_entry
from .growth_routes import ALL_GROWTH_FORMS


@dataclass(frozen=True)
class EncyclopediaRow:
    form_id: str
    parent_id: str | None
    tier: int
    name: str
    status: str
    hint: str
    found: bool
    concept_approved: bool
    sprite_ready: bool


def build_encyclopedia_rows(encountered_ids: Iterable[str]) -> tuple[EncyclopediaRow, ...]:
    encountered = {str(value) for value in encountered_ids}
    rows: list[EncyclopediaRow] = []

    for form in ALL_GROWTH_FORMS:
        entry = catalog_entry(form.form_id)
        found = form.form_id in encountered
        if found:
            name = entry.public_name
            if entry.sprite_ready:
                status = '발견 · 게임 아트 준비됨'
            elif entry.concept_approved:
                status = '발견 · 스프라이트 준비중'
            else:
                status = '발견 · 이미지 추후 업데이트'
            hint = entry.hint
        else:
            name = '???'
            status = '미발견' if entry.concept_approved else '미발견 · 빈 슬롯'
            hint = '아직 만나지 못한 몬스터다. 어떤 기록을 먹으면 만날 수 있을지는 비밀이다.'

        rows.append(EncyclopediaRow(
            form_id=form.form_id,
            parent_id=form.parent_id,
            tier=form.tier,
            name=name,
            status=status,
            hint=hint,
            found=found,
            concept_approved=entry.concept_approved,
            sprite_ready=entry.sprite_ready,
        ))

    return tuple(rows)
