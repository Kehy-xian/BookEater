from __future__ import annotations

"""Player-facing presentation for the approved A/B/C growth tree.

Body lineage comes from reading-response patterns. World/topic axes remain independent and
become sparse visual motifs instead of multiplying the species grid. Internal scores, labels,
thresholds and branch reasons never cross this module's public view boundary.
"""

from typing import Mapping

from .form_catalog import catalog_entry
from .growth_route_resolver import GrowthRouteDecision, WORLD
from .presentation import PublicGrowthView


WORLD_MOTIFS = {
    '상상': '꿈빛',
    '모험': '길무늬',
    '자연': '잎결',
    '사회': '창문무늬',
    '어둠': '그늘결',
}

WORLD_HINTS = {
    '꿈빛': '현실 밖의 가능성을 오래 바라본 흔적도 희미하게 빛난다.',
    '길무늬': '낯선 길과 움직임을 따라간 흔적도 몸 어딘가에 남아 있다.',
    '잎결': '생명과 환경의 변화를 바라본 흔적도 조용히 남아 있다.',
    '창문무늬': '사람들이 함께 살아가는 규칙을 바라본 흔적도 배어 있다.',
    '그늘결': '위태롭고 어두운 순간을 오래 바라본 흔적도 남아 있다.',
}


def _score(stats: Mapping[str, float], key: str) -> float:
    try:
        return max(0.0, float(stats.get(key, 0.0)))
    except (TypeError, ValueError):
        return 0.0


def world_motifs(stats: Mapping[str, float], *, tier: int) -> tuple[str, ...]:
    """Return zero, one, or two stable world motifs without forcing a topic label.

    The starter can carry at most one very light motif; evolved forms can keep a second motif only
    when it is genuinely strong and close to the first. These are art instructions, not species.
    """
    ranked = sorted(((_score(stats, key), key) for key in WORLD), reverse=True)
    if not ranked or ranked[0][0] < 3.0:
        return ()
    top_score, top_key = ranked[0]
    out = [WORLD_MOTIFS[top_key]]
    if tier >= 1 and len(ranked) > 1:
        second_score, second_key = ranked[1]
        if second_score >= 4.0 and second_score >= top_score * 0.78:
            out.append(WORLD_MOTIFS[second_key])
    return tuple(out)


def route_public_growth_view(
    decision: GrowthRouteDecision,
    stats: Mapping[str, float],
    *,
    previous_form: str | None = None,
) -> PublicGrowthView:
    entry = catalog_entry(decision.form_id)
    motifs = world_motifs(stats, tier=decision.tier)
    hint = entry.hint
    if motifs:
        hint = f"{hint} {WORLD_HINTS[motifs[0]]}"

    if previous_form is not None and decision.form_id != previous_form:
        change = f'{entry.public_name}(으)로 모습이 달라졌다. 어떤 기록이 이 모습을 만들었는지는 내 몬스터만 알고 있다.'
    elif decision.delayed:
        change = '조금 더 먹어 보고 싶은지 아직 다음 모습으로 변하지 않았다.'
    else:
        change = '기록이 몸 안에 차곡차곡 쌓이고 있다.'

    return PublicGrowthView(
        stage=decision.tier,
        species=entry.public_name,
        visual_modifiers=motifs,
        tendency_hint=hint,
        change_message=change,
    )
