from __future__ import annotations

"""Convert noisy classifier output into conservative hidden growth nutrition.

This module is intentionally *not* a player-facing explanation layer.  The NLP model may
return several plausible labels, but evolution should react only to sufficiently stable
signals so that one arguable sentence does not visibly distort a long-term creature.

Thresholds below were calibrated on inspected diagnostics.  They must be validated on a
fresh holdout before being treated as a release gate.
"""

from dataclasses import dataclass
import re
from typing import Mapping, Any

RESPONSE = ('사유','탐구','감정','감각')
WORLD = ('상상','모험','자연','사회','어둠')

# Product-growth gates are intentionally stricter than the diagnostic classifier.
# False nutrition is more harmful than missing one ambiguous meal because records accumulate.
RESPONSE_PRIMARY_MARGIN = 0.026
RESPONSE_SECONDARY_MARGIN = 0.035
WORLD_SEMANTIC_MARGIN = 0.0185
WORLD_METAPHOR_MARGIN = 0.055

# A world keyword used as a comparison/metaphor should not by itself mutate the creature.
METAPHOR_CUE = re.compile(r'(?:처럼|듯|비유|표현)')

@dataclass(frozen=True)
class GrowthNutrition:
    response: dict[str,float]
    world: dict[str,float]

    @property
    def is_empty(self) -> bool:
        return not self.response and not self.world


def _as_float(mapping: Mapping[str, Any] | None, key: str, default: float = 0.0) -> float:
    try:
        return float((mapping or {}).get(key, default))
    except (TypeError, ValueError):
        return default


def project_growth_nutrition(text: str, analysis: Mapping[str, Any] | None) -> GrowthNutrition:
    """Project one private classifier result into hidden cumulative nutrition.

    Ordinary UI must never expose the thresholds, margins, evidence counts or returned
    numeric nutrition.  It should consume only the downstream phenotype/presentation view.
    """
    a = analysis or {}
    scores = a.get('scores') if isinstance(a.get('scores'), Mapping) else {}
    null = a.get('null') if isinstance(a.get('null'), Mapping) else {}
    evidence = a.get('evidence') if isinstance(a.get('evidence'), Mapping) else {}
    predicted_r = [x for x in (a.get('response') or []) if x in RESPONSE]
    predicted_w = [x for x in (a.get('world') or []) if x in WORLD]

    rn = _as_float(null, 'response')
    wn = _as_float(null, 'world')
    response: dict[str,float] = {}
    world: dict[str,float] = {}

    for i, trait in enumerate(predicted_r[:2]):
        margin = _as_float(scores, trait) - rn
        required = RESPONSE_PRIMARY_MARGIN if i == 0 else RESPONSE_SECONDARY_MARGIN
        if margin >= required:
            # Secondary interpretations are useful, but should accumulate more slowly.
            response[trait] = 1.0 if i == 0 else 0.55

    metaphorical = bool(METAPHOR_CUE.search(str(text or '')))
    accepted_world: list[str] = []
    for trait in predicted_w:
        margin = _as_float(scores, trait) - wn
        try:
            hits = int((evidence or {}).get(trait, 0) or 0)
        except (TypeError, ValueError):
            hits = 0
        if hits == 0 and margin < WORLD_SEMANTIC_MARGIN:
            continue
        if hits > 0 and metaphorical and margin < WORLD_METAPHOR_MARGIN:
            continue
        accepted_world.append(trait)
        if len(accepted_world) >= 2:
            break

    for i, trait in enumerate(accepted_world):
        world[trait] = 1.0 if i == 0 else 0.65

    return GrowthNutrition(response=response, world=world)


def apply_growth_nutrition(stats: Mapping[str, float] | None, nutrition: GrowthNutrition) -> dict[str,float]:
    """Return updated hidden cumulative stats without mutating the caller's mapping."""
    out = {str(k): float(v) for k,v in (stats or {}).items()}
    for group in (nutrition.response, nutrition.world):
        for trait, amount in group.items():
            out[trait] = max(0.0, out.get(trait, 0.0) + float(amount))
    return out
