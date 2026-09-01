from __future__ import annotations
from dataclasses import dataclass, asdict
from .evolution import EvolutionDecision

# Player-facing growth must stay intentionally opaque.
# Internal traits, weights, keyword hits, confidence and classifier reasons are never exposed here.
# The user should only get broad, diegetic hints from the creature's final form and visual changes.

BASE_HINTS = {
    '사유': (
        '아직 어떤 생각을 오래 품는지 천천히 드러나는 중이다.',
        '질문을 오래 붙잡고 생각의 결을 따라가는 흔적이 보인다.',
        '답을 서두르기보다 질문을 품고 의미를 오래 되새기는 쪽으로 자랐다.',
    ),
    '탐구': (
        '무언가를 모으고 살펴보는 버릇이 조금씩 생기고 있다.',
        '단서와 사실을 모아 서로 연결하려는 흔적이 보인다.',
        '궁금한 것을 그냥 지나치지 않고 단서를 모아 확인하는 쪽으로 자랐다.',
    ),
    '감정': (
        '마음에 남는 장면을 오래 기억하려는 것 같다.',
        '사람의 마음과 관계의 변화를 오래 간직하는 흔적이 보인다.',
        '사건 자체보다 그 안의 마음과 관계를 오래 기억하는 쪽으로 자랐다.',
    ),
    '감각': (
        '문장과 장면의 분위기에 민감하게 반응하기 시작했다.',
        '리듬과 이미지, 분위기의 작은 차이를 기억하는 흔적이 보인다.',
        '말의 리듬과 장면의 결, 분위기를 세심하게 맛보는 쪽으로 자랐다.',
    ),
}

WORLD_HINTS = {
    '상상': '현실 바깥의 가능성과 기묘한 세계를 좋아한 흔적도 남아 있다.',
    '모험': '낯선 길과 이동, 새로운 장소에 끌린 흔적도 남아 있다.',
    '자연': '생명과 계절, 환경의 변화에 눈길을 준 흔적도 남아 있다.',
    '사회': '사람들이 함께 살아가는 규칙과 구조를 바라본 흔적도 남아 있다.',
    '어둠': '불안과 상실, 위태로운 순간을 오래 바라본 흔적도 남아 있다.',
}

GENERIC_FEED_LINES = (
    '기록 한 조각을 꿀꺽 삼켰다.',
    '방금 남긴 문장이 몸 어딘가에 스며든 것 같다.',
    '한참 우물거리더니 조용히 기억해 두었다.',
    '무슨 맛인지는 말해주지 않고 만족한 표정을 짓는다.',
)

@dataclass(frozen=True)
class PublicGrowthView:
    stage: int
    species: str
    visual_modifiers: tuple[str, ...]
    tendency_hint: str
    change_message: str

    def to_dict(self) -> dict:
        return asdict(self)


def _base_hint(decision: EvolutionDecision) -> str:
    if decision.base_trait not in BASE_HINTS:
        return '아직 어느 쪽으로 자랄지 쉽게 짐작하기 어렵다.'
    # Stage 1 stays intentionally vague; stage 2 and 3 reveal only broad tendencies.
    idx = 0 if decision.stage <= 1 else 1 if decision.stage == 2 else 2
    return BASE_HINTS[decision.base_trait][idx]


def _world_hint(decision: EvolutionDecision) -> str:
    if decision.stage < 2 or not decision.modifier_traits:
        return ''
    # Never enumerate internal labels. At most two broad story hints are combined.
    hints = [WORLD_HINTS[t] for t in decision.modifier_traits if t in WORLD_HINTS][:2]
    return ' '.join(hints)


def public_growth_view(decision: EvolutionDecision, *, previous_stage: int | None = None) -> PublicGrowthView:
    hint = _base_hint(decision)
    extra = _world_hint(decision)
    if extra:
        hint = f'{hint} {extra}'

    if previous_stage is not None and decision.stage > previous_stage:
        change = f'{decision.species}(으)로 모습이 달라졌다. 무엇을 먹고 이렇게 자랐는지는 아직 비밀이다.'
    elif decision.changed_base and decision.stage >= 2:
        # Do not explain the internal reason for a body-type shift.
        change = '오래 쌓인 기록 때문인지 몸의 인상이 조금 달라졌다.'
    else:
        change = '조금씩 자라고 있지만 정확한 변화의 이유는 아직 알 수 없다.'

    return PublicGrowthView(
        stage=decision.stage,
        species=decision.species,
        visual_modifiers=decision.visual_modifiers,
        tendency_hint=hint,
        change_message=change,
    )


def generic_feed_line(entry_id: int | str) -> str:
    # Stable selection keeps tests deterministic while feeling varied in normal use.
    try:
        key = int(entry_id)
    except (TypeError, ValueError):
        key = sum(ord(c) for c in str(entry_id))
    return GENERIC_FEED_LINES[key % len(GENERIC_FEED_LINES)]
