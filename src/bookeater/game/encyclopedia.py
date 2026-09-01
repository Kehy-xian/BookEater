from __future__ import annotations

"""Player-facing encyclopedia copy.

Descriptions are intentionally short, atmospheric hints. They must never expose classifier
labels, thresholds, keywords, or the exact hidden route-selection recipe.
"""

from dataclasses import dataclass

from .growth_routes import GROWTH_FORMS


@dataclass(frozen=True)
class EncyclopediaForm:
    form_id: str
    name: str
    tier: int
    hint: str


ENCYCLOPEDIA_FORMS = {
    'starter': EncyclopediaForm(
        'starter', '글씨알', GROWTH_FORMS['starter'].tier,
        '아직 세상의 문장을 조심조심 맛보며 자기 모습을 만들어 가는 작은 종이 친구.',
    ),
    'route_a': EncyclopediaForm(
        'route_a', 'Route A', GROWTH_FORMS['route_a'].tier,
        '읽은 흔적을 차곡차곡 품으며 제 나름의 질서를 만들어 가는 종이 친구.',
    ),
    'route_b': EncyclopediaForm(
        'route_b', 'Route B', GROWTH_FORMS['route_b'].tier,
        '읽은 흔적을 구기고 겹쳐 자기만의 묘한 결을 만들어 가는 종이 친구.',
    ),
}


def encyclopedia_form(form_id: str) -> EncyclopediaForm:
    try:
        return ENCYCLOPEDIA_FORMS[str(form_id)]
    except KeyError as exc:
        raise ValueError(f'unknown encyclopedia form: {form_id}') from exc
