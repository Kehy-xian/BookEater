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
NUTRITION_POLICY_VERSION = 'growth-nutrition-v1.1'

# Tuned on already-inspected diagnostics. Validate on a new holdout before release.
RESPONSE_PRIMARY_MARGIN = 0.026
WORLD_SEMANTIC_FALLBACK_MARGIN = 0.045

# Pure reading-management metadata should not feed the creature at all. This is intentionally
# conservative: losing one arguable record is preferable to teaching the monster that ISBNs,
# page numbers or borrowing logistics are a reading tendency.
BOOKKEEPING_CUE = re.compile(
    r'(?:ISBN|목차|\d+\s*쪽|쪽수|페이지\s*(?:번호|위치)?|분류(?:표시|기호)|서가|책\s*위치|반납|대출|빌렸|빌렸다|'
    r'좌석|사물함|출판연도|판본|상권|하권|책등|스티커|읽은\s*날짜|화면\s*밝기|책갈피|커버를\s*씌)'
)

# If a world-like word is merely the title/name/category of something, do not mutate the body.
NAMING_OR_LABEL_CUE = re.compile(
    r'(?:(?:이라는|라는)\s*(?:이름|제목)|(?:이름|제목)의|단어.{0,10}제목|제품명|분류(?:표시|기호)|ISBN|출판연도|판본|여행용)'
)
METAPHOR_CUE = re.compile(r'(?:처럼|듯|비유|표현)')

# Trait-specific anchors are not an explanation system. They are a private safety rail that
# prevents a high semantic similarity from inventing visible world mutations too freely.
WORLD_ANCHORS = {
    '상상': re.compile(r'(?:마법|꿈|상상|시간여행|시간.{0,8}(?:거꾸로|멈|백\s*년)|외계|다른\s*행성|가상\s*세계|기억.{0,12}(?:병|옮)|현실에\s*없|비현실)'),
    '모험': re.compile(r'(?:여행|여정|항해|항구|국경|목적지|기차.{0,10}갈아|배로.{0,10}섬|낯선.{0,8}(?:도시|곳)|탐험)'),
    '자연': re.compile(r'(?:숲|바다|갯벌|생물|동물|식물|계절|기후|나비|곤충|산불|철새|고래|습지|빙하|태풍|강(?:을|이|의)?|꽃)'),
    '사회': re.compile(r'(?:임대료|계약(?:직|\s*형태)|휴가|보험|정규직|비정규직|제도|법|규칙|권력|주민|노동|복지|교육|차별|불평등|지원금|재개발|투표|선거|공공)'),
    '어둠': re.compile(r'(?:죽|사라진|상실|공포|무서|불안|섬뜩|감시|카메라.{0,10}기록|폭력|억압|격리|지워지|폐허|전쟁|밀려나|떠나야)'),
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


def project_growth_nutrition(text: str, analysis: Mapping[str, Any] | None) -> GrowthNutrition:
    """Project one private classifier result into hidden cumulative nutrition.

    Ordinary UI must consume only the downstream phenotype/presentation view. Do not expose
    margins, evidence counts, anchors, policy version, numeric nutrition or rejected labels.
    """
    text = str(text or '')
    if BOOKKEEPING_CUE.search(text):
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
    # This removes a major source of long-term drift while preserving cumulative nuance over time.
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
        if named_or_labelled:
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
