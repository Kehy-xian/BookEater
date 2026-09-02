from __future__ import annotations

"""Player-art growth route topology.

This module defines the *shape* of the approved four-stage evolution tree only.
Hidden reading tendencies choose among these routes elsewhere.

The structure is intentionally non-hierarchical within a tier:

    tier 0: starter
    tier 1: A / B / C                 (3 forms)
    tier 2: each tier-1 route -> 2    (6 forms)
    tier 3: each tier-2 form -> 2     (12 final forms)

Total forms: 1 + 3 + 6 + 12 = 22.
No sibling route is an upgrade of another sibling route.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GrowthFormSpec:
    form_id: str
    tier: int
    parent_id: str | None
    player_label: str


STARTER_FORM = GrowthFormSpec('starter', 0, None, '글씨알')

ROUTE_A = GrowthFormSpec('route_a', 1, 'starter', '2차 성장 A')
ROUTE_B = GrowthFormSpec('route_b', 1, 'starter', '2차 성장 B')
ROUTE_C = GrowthFormSpec('route_c', 1, 'starter', '2차 성장 C')

# Third-growth forms. Player-facing species names/art names are intentionally placeholders
# until their visual concepts are approved.
ROUTE_A1 = GrowthFormSpec('route_a1', 2, 'route_a', '3차 성장 A1')
ROUTE_A2 = GrowthFormSpec('route_a2', 2, 'route_a', '3차 성장 A2')
ROUTE_B1 = GrowthFormSpec('route_b1', 2, 'route_b', '3차 성장 B1')
ROUTE_B2 = GrowthFormSpec('route_b2', 2, 'route_b', '3차 성장 B2')
ROUTE_C1 = GrowthFormSpec('route_c1', 2, 'route_c', '3차 성장 C1')
ROUTE_C2 = GrowthFormSpec('route_c2', 2, 'route_c', '3차 성장 C2')


def _final(parent: GrowthFormSpec, suffix: str) -> GrowthFormSpec:
    suffix = suffix.lower()
    return GrowthFormSpec(
        form_id=f'{parent.form_id}_{suffix}',
        tier=3,
        parent_id=parent.form_id,
        player_label=f'4차 성장 {parent.player_label.split()[-1]}-{suffix.upper()}',
    )


THIRD_GROWTH_FORMS = (
    ROUTE_A1, ROUTE_A2,
    ROUTE_B1, ROUTE_B2,
    ROUTE_C1, ROUTE_C2,
)

FINAL_GROWTH_FORMS = tuple(
    _final(parent, suffix)
    for parent in THIRD_GROWTH_FORMS
    for suffix in ('alpha', 'beta')
)

SECOND_GROWTH_FORMS = (ROUTE_A, ROUTE_B, ROUTE_C)
SECOND_GROWTH_ROUTES = tuple(form.form_id for form in SECOND_GROWTH_FORMS)

ALL_GROWTH_FORMS = (STARTER_FORM,) + SECOND_GROWTH_FORMS + THIRD_GROWTH_FORMS + FINAL_GROWTH_FORMS
GROWTH_FORMS = {form.form_id: form for form in ALL_GROWTH_FORMS}


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


def children_of(form_id: str) -> tuple[GrowthFormSpec, ...]:
    form_id = str(form_id)
    return tuple(form for form in ALL_GROWTH_FORMS if form.parent_id == form_id)


def forms_at_tier(tier: int) -> tuple[GrowthFormSpec, ...]:
    tier = int(tier)
    return tuple(form for form in ALL_GROWTH_FORMS if form.tier == tier)


def lineage_path(form_id: str) -> tuple[str, ...]:
    """Return starter -> ... -> form_id without allowing cross-route jumps."""
    current = get_growth_form(form_id)
    out = [current.form_id]
    while current.parent_id is not None:
        current = get_growth_form(current.parent_id)
        out.append(current.form_id)
    return tuple(reversed(out))
