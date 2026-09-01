from __future__ import annotations

"""Player-art growth route topology.

This module intentionally defines *shape/topology only*.  It does not expose or decide which
hidden reading tendency chooses a route.  The current approved art structure is:

    starter 글씨알
       ├─ route_a   (second-growth tier)
       └─ route_b   (second-growth tier)

Route A and Route B are siblings at exactly the same growth tier.  Neither is an upgrade of the
other and no valid transition exists from A -> B or B -> A.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GrowthFormSpec:
    form_id: str
    tier: int
    parent_id: str | None
    player_label: str


STARTER_FORM = GrowthFormSpec(
    form_id='starter',
    tier=0,
    parent_id=None,
    player_label='글씨알',
)

ROUTE_A = GrowthFormSpec(
    form_id='route_a',
    tier=1,
    parent_id='starter',
    player_label='2차 성장 A',
)

ROUTE_B = GrowthFormSpec(
    form_id='route_b',
    tier=1,
    parent_id='starter',
    player_label='2차 성장 B',
)

GROWTH_FORMS = {
    form.form_id: form
    for form in (STARTER_FORM, ROUTE_A, ROUTE_B)
}

SECOND_GROWTH_ROUTES = (ROUTE_A.form_id, ROUTE_B.form_id)


def get_growth_form(form_id: str) -> GrowthFormSpec:
    try:
        return GROWTH_FORMS[str(form_id)]
    except KeyError as exc:
        raise ValueError(f'unknown growth form: {form_id}') from exc


def same_growth_tier(left: str, right: str) -> bool:
    return get_growth_form(left).tier == get_growth_form(right).tier


def valid_direct_transition(source: str, target: str) -> bool:
    """Return whether the approved art tree contains source -> target directly."""
    src = get_growth_form(source)
    dst = get_growth_form(target)
    return dst.parent_id == src.form_id and dst.tier == src.tier + 1
