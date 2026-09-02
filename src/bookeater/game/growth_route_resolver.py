from __future__ import annotations

"""Resolve the approved A/B/C four-stage art tree from accumulated reading records.

The resolver consumes only aggregate hidden trait weights. It is deliberately conservative:
when the evidence is too weak or too tied, the monster waits at its current form instead of
being forced down a branch.

Tier meaning:
- tier 0 starter: fewer than 5 meaningful records, or branch evidence still too weak
- tier 1 A/B/C: broad reading-response pattern
- tier 2: finer response/world pattern within the chosen broad route
- tier 3 alpha/beta: deepening vs broadening trajectory using recent records when available
"""

from dataclasses import dataclass
from typing import Mapping

from .growth_routes import get_growth_form

REACTION = ('사유', '탐구', '감정', '감각')
WORLD = ('상상', '모험', '자연', '사회', '어둠')
ALL_AXES = REACTION + WORLD


@dataclass(frozen=True)
class GrowthRouteDecision:
    form_id: str
    tier: int
    delayed: bool
    internal_reason: str


def _score(stats: Mapping[str, float], key: str) -> float:
    try:
        return max(0.0, float(stats.get(key, 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _sum(stats: Mapping[str, float], keys: tuple[str, ...]) -> float:
    return sum(_score(stats, key) for key in keys)


def _active_count(stats: Mapping[str, float], keys: tuple[str, ...]) -> int:
    values = [_score(stats, key) for key in keys]
    top = max(values, default=0.0)
    if top <= 0:
        return 0
    floor = max(0.75, top * 0.34)
    return sum(value >= floor for value in values)


def _dominant_axis(stats: Mapping[str, float]) -> str | None:
    ranked = sorted(((_score(stats, key), key) for key in ALL_AXES), reverse=True)
    return ranked[0][1] if ranked and ranked[0][0] > 0 else None


def _focus_ratio(stats: Mapping[str, float]) -> float:
    values = [_score(stats, key) for key in ALL_AXES]
    total = sum(values)
    return (max(values) / total) if total > 0 else 0.0


def _stage(entry_count: int) -> int:
    entry_count = max(0, int(entry_count))
    if entry_count < 5:
        return 0
    if entry_count < 15:
        return 1
    if entry_count < 40:
        return 2
    return 3


def _second_growth(stats: Mapping[str, float]) -> tuple[str | None, str]:
    cognitive = _sum(stats, ('사유', '탐구'))
    resonant = _sum(stats, ('감정', '감각'))
    response_total = cognitive + resonant
    world_total = _sum(stats, WORLD)
    response_diversity = _active_count(stats, REACTION)
    world_diversity = _active_count(stats, WORLD)

    # Positive C criteria: actual cross-response complexity or strong multi-world connection.
    balanced_cross_response = (
        cognitive >= 2.5 and resonant >= 2.5
        and max(cognitive, resonant) <= min(cognitive, resonant) * 1.55
    )
    connected_world = (
        world_total >= 3.5 and world_diversity >= 2
        and world_total >= response_total * 0.65
    )
    if response_diversity >= 3 or balanced_cross_response or connected_world:
        return 'route_c', 'multi-axis or connected-world pattern'

    if response_total < 3.0:
        return None, 'broad route evidence still sparse'

    if cognitive >= resonant * 1.18 and cognitive - resonant >= 1.0:
        return 'route_a', 'cognitive response cluster leads'
    if resonant >= cognitive * 1.18 and resonant - cognitive >= 1.0:
        return 'route_b', 'resonant response cluster leads'
    return None, 'broad route remains tied'


def _choose_pair(
    stats: Mapping[str, float],
    left_key: str,
    right_key: str,
    left_form: str,
    right_form: str,
) -> tuple[str | None, str]:
    left = _score(stats, left_key)
    right = _score(stats, right_key)
    if max(left, right) < 2.5:
        return None, 'sub-route evidence still sparse'
    if left >= right * 1.14 and left - right >= 0.75:
        return left_form, f'{left_key} clearly leads {right_key}'
    if right >= left * 1.14 and right - left >= 0.75:
        return right_form, f'{right_key} clearly leads {left_key}'
    return None, 'sub-route remains tied'


def _third_growth(route: str, stats: Mapping[str, float]) -> tuple[str | None, str]:
    if route == 'route_a':
        return _choose_pair(stats, '사유', '탐구', 'route_a1', 'route_a2')
    if route == 'route_b':
        return _choose_pair(stats, '감정', '감각', 'route_b1', 'route_b2')

    # Route C is not a leftovers bucket. It splits by what makes the profile complex.
    response_diversity = _active_count(stats, REACTION)
    world_diversity = _active_count(stats, WORLD)
    response_total = _sum(stats, REACTION)
    world_total = _sum(stats, WORLD)
    cross_response = min(
        _sum(stats, ('사유', '탐구')),
        _sum(stats, ('감정', '감각')),
    )
    c1 = response_diversity + min(2.0, cross_response / 2.5)
    c2 = world_diversity + min(2.0, world_total / max(3.0, response_total))
    if max(c1, c2) < 2.5:
        return None, 'C sub-route evidence still sparse'
    if c1 >= c2 + 0.55:
        return 'route_c1', 'complexity comes mainly from mixed response styles'
    if c2 >= c1 + 0.55:
        return 'route_c2', 'complexity comes mainly from connected world themes'
    return None, 'C sub-route remains tied'


def _final_growth(parent_form: str, cumulative: Mapping[str, float], recent: Mapping[str, float] | None) -> tuple[str | None, str]:
    sample = recent if recent is not None else cumulative
    if _sum(sample, ALL_AXES) < 2.0:
        return None, 'recent trajectory evidence still sparse'

    cumulative_focus = _focus_ratio(cumulative)
    recent_focus = _focus_ratio(sample)
    cumulative_active = _active_count(cumulative, ALL_AXES)
    recent_active = _active_count(sample, ALL_AXES)
    cumulative_dom = _dominant_axis(cumulative)
    recent_dom = _dominant_axis(sample)

    # alpha = deepening: recent records reinforce a stable dominant direction.
    deepening = (
        recent_dom is not None
        and recent_dom == cumulative_dom
        and recent_focus >= max(0.30, cumulative_focus * 0.90)
        and recent_active <= max(4, cumulative_active)
    )
    # beta = broadening: dominant direction changes or more axes become meaningfully active.
    broadening = (
        recent_dom is not None
        and (
            (cumulative_dom is not None and recent_dom != cumulative_dom)
            or recent_active >= cumulative_active + 1
            or recent_focus <= cumulative_focus * 0.82
        )
    )

    if deepening and not broadening:
        return f'{parent_form}_alpha', 'recent records deepen the established signature'
    if broadening and not deepening:
        return f'{parent_form}_beta', 'recent records broaden the established signature'
    # If both/neither fire, use a stable concentration fallback rather than random branching.
    return (
        f'{parent_form}_alpha', 'trajectory concentration fallback: deepening'
    ) if recent_focus >= 0.34 else (
        f'{parent_form}_beta', 'trajectory concentration fallback: broadening'
    )


def resolve_growth_route(
    cumulative_stats: Mapping[str, float],
    entry_count: int,
    *,
    recent_stats: Mapping[str, float] | None = None,
    current_form: str = 'starter',
) -> GrowthRouteDecision:
    """Resolve the highest supported form without forcing weak/tied evidence."""
    target_stage = _stage(entry_count)
    if target_stage == 0:
        return GrowthRouteDecision('starter', 0, False, 'not enough meaningful records yet')

    route, why = _second_growth(cumulative_stats)
    if route is None:
        current = get_growth_form(current_form)
        keep = current.form_id if current.tier <= 0 else current.form_id
        return GrowthRouteDecision(keep, current.tier, True, why)
    if target_stage == 1:
        return GrowthRouteDecision(route, 1, False, why)

    third, why3 = _third_growth(route, cumulative_stats)
    if third is None:
        return GrowthRouteDecision(route, 1, True, why3)
    if target_stage == 2:
        return GrowthRouteDecision(third, 2, False, why3)

    final, why4 = _final_growth(third, cumulative_stats, recent_stats)
    if final is None:
        return GrowthRouteDecision(third, 2, True, why4)
    return GrowthRouteDecision(final, 3, False, why4)
