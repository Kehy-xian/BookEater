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
NUTRITION_POLICY_VERSION = 'growth-nutrition-v1.2'

# Response identity is already protected by cumulative evolution + hysteresis, so a modest
# margin is enough. World/body decoration remains more conservative because false modifiers
# are visually salient.
RESPONSE_PRIMARY_MARGIN = 0.020
WORLD_SEMANTIC_FALLBACK_MARGIN = 0.045

# Metadata is common inside otherwise meaningful reading notes ("153쪽에서 ... 슬펐다").
# Therefore a bookkeeping word is no longer an automatic veto. We abstain only when the text
# looks administrative *and* lacks a substantive reflection cue.
BOOKKEEPING_CUE = re.compile(
    r'(?:ISBN|목차|\d+\s*쪽|쪽수|페이지\s*(?:번호|위치)?|분류(?:표시|기호)|서가|책\s*위치|반납|대출|빌렸|빌렸다|'
    r'좌석|사물함|출판연도|판본|상권|하권|책등|스티커|읽은\s*날짜|화면\s*밝기|책갈피|커버를\s*씌)'
)
SUBSTANTIVE_CUE = re.compile(
    r'(?:장면|문장|리듬|묘사|설정|공감|마음|생각|고민|의문|궁금|왜\s|정당|공정|불공평|'
    r'서럽|슬프|안타깝|무섭|섬뜩|불안|재미|흥미|좋았|좋아|인상|원자료|근거|의미|선택|책임|느껴|'
    r'해석|비교해|찾아보|찾아\s*보|확인해\s*보|확인하고\s*싶)'
)

# If a world-like word is explicitly a label/title/product/category, it must not mutate the
# creature. Keep this contextual; a normal story sentence such as "사라진 사람의 이름을..."
# must not be suppressed merely because it contains the noun "이름".
NAMING_OR_LABEL_CUE = re.compile(
    r'(?:(?:이라는|라는)\s*(?:(?:카페|동아리|프로젝트|제품|곡|전시)\s*)?(?:이름|제목)|'
    r'(?:카페|동아리|프로젝트|제품|향수|곡|전시|신문\s*코너)\s*(?:의\s*)?(?:이름|제목)|'
    r'(?:이라는|라는)\s*(?:브랜드|과목명)|제품명|분류(?:표시|기호)|ISBN|출판연도|판본|여행용)'
)
METAPHOR_CUE = re.compile(r'(?:처럼|듯|비유|표현)')

# Direct negation is a stronger signal than a literal trigger word. This protects sentences
# such as "마법 이야기는 아니고 ..." or "여행 장면은 거의 없었다".
NEGATED_ANCHORS = {
    '상상': re.compile(r'(?<![가-힣])(?:마법|꿈|상상|시간여행|외계|가상)[^.!?\n]{0,24}(?:아니|없|거의\s*없)'),
    '모험': re.compile(r'(?<![가-힣])(?:여행|여정|항해|탐험|국경|목적지)[^.!?\n]{0,24}(?:아니|없|거의\s*없)'),
    '자연': re.compile(r'(?<![가-힣])(?:숲|바다|생태|자연|동물|식물)[^.!?\n]{0,24}(?:아니|없|거의\s*없)'),
    '사회': re.compile(r'(?<![가-힣])(?:제도|사회|노동|정치|규칙)[^.!?\n]{0,24}(?:아니|없|거의\s*없)'),
    '어둠': re.compile(r'(?<![가-힣])(?:죽음|공포|폭력|감시|상실)[^.!?\n]{0,24}(?:아니|아니라|없|거의\s*없)'),
}

# Trait-specific anchors are a private safety rail, not a keyword explanation system.
# The negative Hangul look-behind prevents accidental substring hits: e.g. "우습지만" must
# not contain a fake "습지" signal, and "방법" must not contain a fake "법" signal.
WORLD_ANCHORS = {
    '상상': re.compile(r'(?<![가-힣])(?:마법|꿈|상상|시간여행|시간.{0,8}(?:거꾸로|멈|백\s*년)|외계|다른\s*행성|가상\s*세계|가상\s*도시|기억.{0,12}(?:병|옮)|현실에\s*없|비현실)'),
    '모험': re.compile(r'(?<![가-힣])(?:여행|여정|항해|항구|국경|목적지|기차.{0,10}갈아|배로.{0,10}섬|낯선.{0,8}(?:도시|곳)|탐험)'),
    '자연': re.compile(r'(?<![가-힣])(?:숲|바다|갯벌|생물|동물|식물|계절|기후|나비|곤충|산불|철새|고래|습지|빙하|태풍|강물|하천|꽃)'),
    '사회': re.compile(r'(?<![가-힣])(?:임대료|계약(?:직|\s*형태)|휴가|보험|정규직|비정규직|제도|법률|법원|법안|학교\s*규칙|회사\s*규정|권력|주민|노동|복지|교육|차별|불평등|지원금|재개발|투표|선거|공공)'),
    '어둠': re.compile(r'(?<![가-힣])(?:죽음|죽었|죽는|죽어|사망|사라진|상실|공포|무서|불안|섬뜩|감시|카메라.{0,10}기록|폭력|억압|격리|지워지|폐허|전쟁|밀려나|떠나야)'),
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
    """Project one private classifier result into hidden cumulative nutrition.

    Ordinary UI must consume only the downstream phenotype/presentation view. Do not expose
    margins, evidence counts, anchors, policy version, numeric nutrition or rejected labels.
    """
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

    # Body identity needs one dominant meal signal, not every plausible interpretation.
    if predicted_r:
        trait = predicted_r[0]
        if _as_float(scores, trait) - rn >= RESPONSE_PRIMARY_MARGIN:
            response[trait] = 1.0

    named_or_labelled = bool(NAMING_OR_LABEL_CUE.search(text))
    metaphorical = bool(METAPHOR_CUE.search(text))
    accepted: list[str] = []
    for trait in predicted_w:
        margin = _as_float(scores, trait) - wn
        anchor = bool(WORLD_ANCHORS[trait].search(text))
        if named_or_labelled or NEGATED_ANCHORS[trait].search(text):
            continue
        # A direct content anchor is enough unless it is explicitly metaphorical; otherwise
        # require a strong semantic margin. This favors abstention over decorative false mutations.
        if anchor:
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
