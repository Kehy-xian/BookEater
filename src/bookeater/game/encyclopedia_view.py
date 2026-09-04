from __future__ import annotations

"""Pure player-facing presentation model for the 22-slot growth encyclopedia."""

from dataclasses import dataclass
from typing import Iterable

from .form_catalog import catalog_entry
from .growth_routes import ALL_GROWTH_FORMS, children_of, get_growth_form


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


def build_encyclopedia_rows(
    encountered_ids: Iterable[str], *, current_form: str | None = None,
) -> tuple[EncyclopediaRow, ...]:
    encountered = {str(value) for value in encountered_ids}
    valid_encountered = {value for value in encountered if any(f.form_id == value for f in ALL_GROWTH_FORMS)}
    if current_form is not None:
        frontier_parents = {str(current_form)}
    elif valid_encountered:
        deepest = max(get_growth_form(value).tier for value in valid_encountered)
        frontier_parents = {
            value for value in valid_encountered if get_growth_form(value).tier == deepest
        }
    else:
        frontier_parents = {'starter'}
    visible = set(valid_encountered)
    for parent in frontier_parents:
        visible.update(child.form_id for child in children_of(parent))
    rows: list[EncyclopediaRow] = []

    for form in ALL_GROWTH_FORMS:
        if form.form_id not in visible:
            continue
        entry = catalog_entry(form.form_id)
        found = form.form_id in encountered
        if found:
            name = entry.public_name
            status = '만남'
            hint = entry.hint
        else:
            name = '???'
            status = '미발견'
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
