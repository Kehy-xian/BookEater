from __future__ import annotations

"""Convert noisy classifier output into conservative hidden growth nutrition.

The classifier is allowed to be broad and diagnostic. Evolution is deliberately stricter:
false nutrition accumulates into a visible phenotype, while skipping one ambiguous meal is
usually harmless. None of the thresholds or anchors in this file are player-facing.
"""

from dataclasses import dataclass
import re
from typing import Mapping, Any

RESPONSE = ('사유','탐구','감정','감각')
WORLD = ('상상','모험','자연','사회','어둠')
NUTRITION_POLICY_VERSION = 'growth-nutrition-v1.3'

# Response identity is protected again downstream by cumulative evidence + evolution hysteresis.
# Strong response-language may therefore pass on a smaller semantic margin; bare semantic guesses
# still need a wider margin. World modifiers stay stricter because a false visual mutation is salient.
RESPONSE_PRIMARY_MARGIN = 0.020
RESPONSE_ANCHORED_MARGIN = 0.010
WORLD_SEMANTIC_FALLBACK_MARGIN = 0.055
WORLD_ANCHORED_MARGIN = 0.020

BOOKKEEPING_CUE = re.compile(
    r'(?:ISBN|목차|\d+\s*쪽|쪽수|페이지\s*(?:번호|위치)?|분류(?:표시|기호)|서가|책\s*위치|반납|대출|빌렸|빌렸다|'
    r'좌석|사물함|출판연도|판본|상권|하권|책등|스티커|읽은\s*날짜|화면\s*밝기|책갈피|커버를\s*씌)'
)
SUBSTANTIVE_CUE = re.compile(
    r'(?:장면|문장|리듬|묘사|설정|공감|마음|생각|고민|의문|궁금|왜\s|정당|공정|불공평|'
    r'서럽|속상|슬프|안타깝|무섭|섬뜩|불안|울컥|재미|흥미|좋았|좋아|인상|원자료|근거|의미|선택|책임|느껴|'
    r'해석|비교해|찾아보|찾아\s*보|확인해\s*보|확인하고\s*싶|계산해)'
)

# Response anchors are intentionally broad-but-contextual. They never decide a trait by themselves:
# the local semantic classifier must already have selected that trait. They only allow a slightly
# smaller null-margin for ordinary human phrasing that embeddings sometimes under-score.
RESPONSE_ANCHORS = {
    '사유': re.compile(r'(?:생각|고민|판단|정당|공정|옳|의미|책임|기준|배려|회피|의문)'),
    '탐구': re.compile(r'(?:원자료|연구\s*원문|찾아\s*보|찾아보|확인해\s*보|비교해|계산해|대조해|근거)'),
    '감정': re.compile(r'(?:마음|속상|서럽|슬프|안타깝|울컥|불안|무서|섬뜩|씁쓸|화가|공감|흥미|재미)'),
    '감각': re.compile(r'(?:문장|리듬|문체|표현|번역|묘사|말투|소리|빛|색|대비|삽화|그림|배치|보기\s*편)'),
}

NAMING_OR_LABEL_CUE = re.compile(
    r'(?:(?:이라는|라는)\s*(?:(?:카페|동아리|프로젝트|제품|곡|전시)\s*)?(?:이름|제목)|'
    r'(?:카페|동아리|프로젝트|제품|향수|곡|전시|신문\s*코너)\s*(?:의\s*)?(?:이름|제목)|'
    r'(?:이라는|라는)\s*(?:브랜드|과목명)|제품명|분류(?:표시|기호)|ISBN|출판연도|판본|여행용)'
)
METAPHOR_CUE = re.compile(r'(?:처럼|듯|비유|표현)')

# Surface/design language is a high-value false-modifier trap: "꽃무늬 표지" is not nature,
# "바다색 배경" is not a sea-reading tendency, and "교육용 카드" is not a social theme.
VISUAL_SURFACE_CUE = re.compile(
    r'(?:표지|삽화|그림|무늬|배경|글자|글씨|디자인|색(?:상|감)?|카드|포스터).{0,35}'
    r'(?:예쁘|아름답|대비|배치|보기\s*편|어울|질감|색|디자인|인상)'
    r'|(?:예쁘|아름답|대비|배치|보기\s*편|어울|질감|색|디자인|인상).{0,35}'
    r'(?:표지|삽화|그림|무늬|배경|글자|글씨|카드|포스터)'
)
# If actual topic/action words are also present, a visual sentence can still carry a world signal.
WORLD_CONTENT_CUE = re.compile(
    r'(?:생태|기후|멸종|산불|철새|고래|갯벌|습지|제도|정책|재판|법\s*(?:절차|제도|체계)|노동|'
    r'임대료|재개발|투표|선거|감시|전쟁|폭력|억압|여행|여정|항해|탐험|국경|목적지|마법|가상\s*(?:세계|도시)|시간여행)'
)

NEGATED_ANCHORS = {
    '상상': re.compile(r'(?<![가-힣])(?:마법|꿈|상상|시간여행|외계|가상)[^.!?\n]{0,24}(?:아니|없|거의\s*없)'),
    '모험': re.compile(r'(?<![가-힣])(?:여행|여정|항해|탐험|국경|목적지)[^.!?\n]{0,24}(?:아니|없|거의\s*없)'),
    '자연': re.compile(r'(?<![가-힣])(?:숲|바다|생태|자연|동물|식물)[^.!?\n]{0,24}(?:아니|없|거의\s*없)'),
    '사회': re.compile(r'(?<![가-힣])(?:제도|사회|노동|정치|규칙)[^.!?\n]{0,24}(?:아니|없|거의\s*없)'),
    '어둠': re.compile(r'(?<![가-힣])(?:죽음|공포|폭력|감시|상실)[^.!?\n]{0,24}(?:아니|아니라|없|거의\s*없)'),
}

# Trait-specific anchors are private safety rails, not a keyword explanation system. Hangul
# left-boundary guards stop inner-word collisions such as 우[습지]만, 방[법], 건[강], [죽]순.
WORLD_ANCHORS = {
    '상상': re.compile(r'(?<![가-힣])(?:마법|꿈|상상|시간여행|시간.{0,8}(?:거꾸로|되감|멈|백\s*년)|외계|다른\s*행성|가상\s*세계|가상\s*도시|기억.{0,12}(?:병|옮)|현실에\s*없|비현실)'),
    '모험': re.compile(r'(?<![가-힣])(?:여행|여정|항해|항구|국경|목적지|기차.{0,10}갈아|배로.{0,10}섬|낯선.{0,8}(?:도시|곳)|탐험|등대)'),
    '자연': re.compile(r'(?<![가-힣])(?:숲|바다|갯벌|생태|생물|동물|식물|계절|기후|나비|곤충|산불|철새|고래|습지|빙하|태풍|홍수|해수|산호|강물|하천|꽃)'),
    '사회': re.compile(r'(?<![가-힣])(?:임대료|계약(?:직|\s*형태)|휴가|보험|정규직|비정규직|제도|정책|주거|재판|법\s*(?:절차|제도|체계)|법률|법원|법안|학교\s*규칙|회사\s*규정|권력|주민|노동|복지|교육|차별|불평등|지원금|재개발|투표|선거|공공)'),
    '어둠': re.compile(r'(?<![가-힣])(?:죽음|죽었|죽는|죽어|사망|사라진|상실|공포|무서|불안|섬뜩|감시|카메라.{0,10}기록|폭력|억압|격리|지워지|폐허|전쟁|밀려나|떠나야|들킬)')
}


@dataclass(frozen=True)
class GrowthNutrition:
    response: dict[str,float]
    world: dict[str,float]
    policy_version: str = NUTRITION_POLICY_VERSION

    @property
    def is_empty(self) -> bool:
        return not self.response and not self.world


def _as_float(mapping: Mapping[str, Any] | None, key: str, default: float = 0.0) -> float:
    try:
        return float((mapping or {}).get(key, default))
    except (TypeError, ValueError):
        return default


def _bookkeeping_only(text: str) -> bool:
    return bool(BOOKKEEPING_CUE.search(text)) and not bool(SUBSTANTIVE_CUE.search(text))


def project_growth_nutrition(text: str, analysis: Mapping[str, Any] | None) -> GrowthNutrition:
    """Project one private classifier result into hidden cumulative nutrition."""
    text = str(text or '')
    if _bookkeeping_only(text):
        return GrowthNutrition(response={}, world={})

    a = analysis or {}
    scores = a.get('scores') if isinstance(a.get('scores'), Mapping) else {}
    null = a.get('null') if isinstance(a.get('null'), Mapping) else {}
    predicted_r = [x for x in (a.get('response') or []) if x in RESPONSE]
    predicted_w = [x for x in (a.get('world') or []) if x in WORLD]

    rn = _as_float(null, 'response')
    wn = _as_float(null, 'world')
    response: dict[str,float] = {}
    world: dict[str,float] = {}

    if predicted_r:
        trait = predicted_r[0]
        margin = _as_float(scores, trait) - rn
        required = RESPONSE_ANCHORED_MARGIN if RESPONSE_ANCHORS[trait].search(text) else RESPONSE_PRIMARY_MARGIN
        if margin >= required:
            response[trait] = 1.0

    named_or_labelled = bool(NAMING_OR_LABEL_CUE.search(text))
    metaphorical = bool(METAPHOR_CUE.search(text))
    visual_surface_only = bool(VISUAL_SURFACE_CUE.search(text)) and not bool(WORLD_CONTENT_CUE.search(text))

    # Direct, contextual topic anchors may recover a high-confidence modifier that the broad
    # classifier omitted from its short label list. This never bypasses null margin, naming,
    # negation, metaphor or visual-surface guards.
    anchored_extras = [
        trait for trait in WORLD
        if trait not in predicted_w
        and WORLD_ANCHORS[trait].search(text)
        and (_as_float(scores, trait) - wn) >= WORLD_ANCHORED_MARGIN
    ]
    anchored_extras.sort(key=lambda t: _as_float(scores, t), reverse=True)
    candidates = predicted_w + anchored_extras

    accepted: list[str] = []
    for trait in candidates:
        margin = _as_float(scores, trait) - wn
        anchor = bool(WORLD_ANCHORS[trait].search(text))
        if trait in accepted or named_or_labelled or NEGATED_ANCHORS[trait].search(text):
            continue
        if visual_surface_only:
            continue
        if anchor:
            if margin < WORLD_ANCHORED_MARGIN:
                continue
            if metaphorical and margin < 0.055:
                continue
        elif margin < WORLD_SEMANTIC_FALLBACK_MARGIN:
            continue
        accepted.append(trait)
        if len(accepted) >= 2:
            break

    for i, trait in enumerate(accepted):
        world[trait] = 1.0 if i == 0 else 0.65

    return GrowthNutrition(response=response, world=world)


def apply_growth_nutrition(stats: Mapping[str, float] | None, nutrition: GrowthNutrition) -> dict[str,float]:
    """Return updated hidden cumulative stats without mutating the caller's mapping."""
    out = {str(k): float(v) for k,v in (stats or {}).items()}
    for group in (nutrition.response, nutrition.world):
        for trait, amount in group.items():
            out[trait] = max(0.0, out.get(trait, 0.0) + float(amount))
    return out
