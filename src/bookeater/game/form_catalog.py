from __future__ import annotations

"""Player-facing monster catalog metadata.

Concept approval and production sprite readiness are deliberately separate. The user has
approved the starter, three first-growth route bodies, and two second-growth bodies under each
route. Final forms keep stable slots but remain visually undisclosed until later art approval.
"""

from dataclasses import dataclass

from .growth_routes import ALL_GROWTH_FORMS, GROWTH_FORMS


# These slugs are generated into the packaged production sprite set and verified by Windows CI.
# Keeping this explicit prevents a concept-only entry from being advertised as game-ready later.
_PRODUCTION_SPRITE_SLUGS = frozenset({
    'paperling', 'pagedge', 'inknest', 'lantern',
    'route_a1', 'route_a2', 'route_b1', 'route_b2', 'route_c1', 'route_c2',
})


@dataclass(frozen=True)
class FormCatalogEntry:
    form_id: str
    public_name: str
    hint: str
    concept_approved: bool
    asset_slug: str | None

    @property
    def sprite_ready(self) -> bool:
        return self.asset_slug in _PRODUCTION_SPRITE_SLUGS


# These names are intentionally conservative. Route/tier art is approved, but final Korean
# species names have not all been chosen yet; do not manufacture permanent names from concept art.
_APPROVED: dict[str, FormCatalogEntry] = {
    'starter': FormCatalogEntry(
        'starter', '글씨알',
        '아직 세상의 문장을 조심조심 맛보며 자기 모습을 만들어 가는 작은 친구.',
        True, 'paperling',
    ),
    'route_a': FormCatalogEntry(
        'route_a', 'Route A',
        '문장 속 의미와 이유를 오래 들여다보는 쪽으로 모습이 달라졌다.',
        True, 'pagedge',
    ),
    'route_b': FormCatalogEntry(
        'route_b', 'Route B',
        '마음에 남은 울림과 표현을 자기 안에 오래 품는 쪽으로 모습이 달라졌다.',
        True, 'inknest',
    ),
    'route_c': FormCatalogEntry(
        'route_c', 'Route C',
        '서로 다른 생각과 세계를 이어 보며 빛을 밝히는 쪽으로 모습이 달라졌다.',
        True, 'lantern',
    ),
    'route_a1': FormCatalogEntry(
        'route_a1', 'Route A · 타입 1',
        '한 문장을 오래 곱씹으며 자기 생각을 깊게 만드는 흔적이 짙다.',
        True, 'route_a1',
    ),
    'route_a2': FormCatalogEntry(
        'route_a2', 'Route A · 타입 2',
        '궁금한 것을 그냥 지나치지 않고 끝까지 따라가는 흔적이 짙다.',
        True, 'route_a2',
    ),
    'route_b1': FormCatalogEntry(
        'route_b1', 'Route B · 타입 1',
        '인물의 마음과 관계에서 생긴 울림을 오래 기억하는 흔적이 짙다.',
        True, 'route_b1',
    ),
    'route_b2': FormCatalogEntry(
        'route_b2', 'Route B · 타입 2',
        '문장과 장면의 분위기, 표현의 결을 세심하게 맛보는 흔적이 짙다.',
        True, 'route_b2',
    ),
    'route_c1': FormCatalogEntry(
        'route_c1', 'Route C · 타입 1',
        '여러 방식으로 느끼고 생각한 것을 한데 엮는 흔적이 짙다.',
        True, 'route_c1',
    ),
    'route_c2': FormCatalogEntry(
        'route_c2', 'Route C · 타입 2',
        '서로 다른 세계와 주제를 연결해 새로운 길을 보는 흔적이 짙다.',
        True, 'route_c2',
    ),
}


def _placeholder(form_id: str) -> FormCatalogEntry:
    return FormCatalogEntry(
        form_id=form_id,
        public_name='???',
        hint='아직 모습을 준비 중인 진화형이다.',
        concept_approved=False,
        asset_slug=None,
    )


FORM_CATALOG: dict[str, FormCatalogEntry] = {
    form.form_id: _APPROVED.get(form.form_id, _placeholder(form.form_id))
    for form in ALL_GROWTH_FORMS
}


def catalog_entry(form_id: str) -> FormCatalogEntry:
    form_id = str(form_id)
    if form_id not in GROWTH_FORMS:
        raise ValueError(f'unknown growth form: {form_id}')
    return FORM_CATALOG[form_id]


def approved_concept_ids() -> tuple[str, ...]:
    return tuple(
        form.form_id for form in ALL_GROWTH_FORMS
        if FORM_CATALOG[form.form_id].concept_approved
    )


def placeholder_ids() -> tuple[str, ...]:
    return tuple(
        form.form_id for form in ALL_GROWTH_FORMS
        if not FORM_CATALOG[form.form_id].concept_approved
    )
