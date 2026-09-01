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
NUTRITION_POLICY_VERSION = 'growth-nutrition-v1.6.2'

RESPONSE_UNANCHORED_MARGIN = 0.035
RESPONSE_ANCHORED_MARGIN = 0.010
WORLD_SEMANTIC_FALLBACK_MARGIN = 0.055
WORLD_ANCHORED_MARGIN = 0.010
STRONG_NATURE_MARGIN = 0.005
STRONG_DARK_MARGIN = -0.030

BOOKKEEPING_CUE = re.compile(
    r'(?:ISBN|목차|\d+\s*쪽|쪽수|페이지\s*(?:번호|위치)?|분류(?:표시|기호)|서가|책\s*위치|반납|대출|빌렸|빌렸다|'
    r'예약|수령|수령일|도착\s*(?:알림|예정)|전자책\s*동기화|동기화|오디오북\s*재생\s*위치|재생\s*위치|'
    r'마지막\s*읽은\s*위치|읽던\s*페이지|읽은\s*위치|시리즈\s*순서|권수|권차(?:\s*정보)?|도서관\s*검색|상호대차|'
    r'희망도서\s*(?:신청\s*)?(?:상태|주문)|주문\s*중|앱\s*새로고침|새로고침|좌석|사물함|출판연도|발행일|판권면|판본|상권|하권|책등|스티커|'
    r'읽은\s*날짜|독서\s*시간|읽기\s*알림|화면\s*밝기|야간\s*모드|글자\s*크기|글꼴|줄\s*간격|'
    r'블루투스|이어폰\s*연결|책갈피|커버를\s*씌)'
)
SUBSTANTIVE_CUE = re.compile(
    r'(?:장면|문장|리듬|묘사|설정|공감|마음|생각|고민|의문|궁금|왜\s|정당|공정|불공평|'
    r'서럽|속상|짠하|짠했|슬프|안타깝|안쓰럽|무섭|섬뜩|불안|울컥|답답|쓸쓸|허전|먹먹|'
    r'설레|긴장|소름|신기|재미|흥미|좋았|좋아|인상|원자료|근거|의미|선택|책임|느껴|기억나|'
    r'기억났|기억에\s*남|해석|비교해|찾아보|찾아\s*보|확인해\s*보|확인하고\s*싶|계산해)'
)

RESPONSE_ANCHORS = {
    '사유': re.compile(r'(?:생각|고민|판단|정당|공정|옳|의미|책임|기준|배려|회피|의문)'),
    '탐구': re.compile(r'(?:원자료|연구\s*원문|찾아\s*보|찾아보|확인해\s*보|비교해|계산해|대조해|근거)'),
    '감정': re.compile(r'(?:마음|속상|서럽|짠하|짠했|슬프|안타깝|안쓰럽|울컥|불안|무서|섬뜩|씁쓸|답답|쓸쓸|허전|먹먹|설레|긴장|소름|신기|화가|공감|흥미|재미|기억나|기억났|기억에\s*남)'),
    '감각': re.compile(r'(?:문장|리듬|문체|표현|번역|묘사|말투|발음|입\s*모양|소리|빛|색|대비|삽화|그림|배치|보기\s*편)'),
}

NAMING_OR_LABEL_CUE = re.compile(
    r'(?:(?:이라는|라는)\s*(?:(?:카페|동아리|프로젝트|제품|메뉴|곡|공연|전시|보드게임)\s*)?(?:이름|제목)|'
    r'(?:카페|동아리|프로젝트|제품|메뉴|향수|곡|공연|전시|보드게임|신문\s*코너)\s*(?:의\s*)?(?:이름|제목)|'
    r'(?:게임\s*)?캐릭터(?:\s*직업)?\s*(?:의\s*)?(?:이름|직업\s*이름)|직업\s*이름|'
    r'(?:이라는|라는)\s*(?:브랜드|과목명)|제품명|활동명|카드\s*이름|팀명|등급\s*이름|구역\s*이름|표제어|분류(?:표시|기호)|ISBN|출판연도|판본|여행용)'
)
QUOTED_SPAN = re.compile(r'["“‘][^"”’\n]{1,60}["”’]')
QUOTED_LABEL_CONTEXT = re.compile(
    r'["“‘][^"”’\n]{1,60}["”’].{0,35}(?:이름|제목|활동명|과목명|카드\s*이름|메뉴명|직업명|제품명|전시명|코너명|팀명|등급\s*이름|구역\s*이름|표제어)'
)
# Unquoted labels such as "마법이라는 이름의 디저트" need the same protection as quoted labels.
# Strip only the short value + "이라는/라는 이름/제목" phrase for the content check; do not
# suppress a later genuine world topic in the same note.
UNQUOTED_LABEL_VALUE = re.compile(
    r'(?<!\S)[가-힣A-Za-z0-9_-]{1,24}(?:이라는|라는)\s*(?:이름|제목)(?:의)?'
)
METAPHOR_CUE = re.compile(r'(?:처럼|듯|비유|표현)')
IMAGINATION_METAPHOR_CUE = re.compile(r'시간.{0,12}멈[^.!?\n]{0,12}(?:것\s*같|듯)')

VISUAL_SURFACE_CUE = re.compile(
    r'(?:표지|삽화|그림|무늬|배경|글자|글씨|디자인|색(?:상|감)?|카드|포스터).{0,35}'
    r'(?:예쁘|아름답|대비|배치|보기\s*편|어울|질감|색|디자인|인상)'
    r'|(?:예쁘|아름답|대비|배치|보기\s*편|어울|질감|색|디자인|인상).{0,35}'
    r'(?:표지|삽화|그림|무늬|배경|글자|글씨|카드|포스터)'
)
WORLD_CONTENT_CUE = re.compile(
    r'(?:생태|기후|멸종|산불|철새|고래|갯벌|습지|산호|해수|빙하|홍수|제도|정책|재판|'
    r'법\s*(?:절차|제도|체계)|고용\s*형태|병가|노동|임대료|재개발|투표|선거|감시\s*카메라|'
    r'전쟁|폭력|억압|폐허|실종|여행|여정|항해|탐험|국경|목적지|비밀\s*통로|미지의\s*(?:해역|섬|땅)|'
    r'마법|가상\s*(?:세계|도시|국가)|시간여행|(?:하루|아침|날짜|마을|도시).{0,24}(?:되돌아|반복|다시\s*시작|처음부터)|'
    r'기억.{0,16}(?:사고팔|거래|팔\s*수|살\s*수|지우|삭제))'
)

NEGATED_ANCHORS = {
    '상상': re.compile(r'(?<![가-힣])(?:마법|꿈|상상|시간여행|외계|가상).{0,12}(?:이야기|내용|설정|요소)?\s*(?:은|는|이|가)?\s*(?:아니|없(?:었|다|고))'),
    '모험': re.compile(r'(?<![가-힣])(?:여행|여정|항해|탐험).{0,12}(?:장면|내용|이야기|요소)?\s*(?:은|는|이|가)?\s*(?:아니|없(?:었|다|고))'),
    '자연': re.compile(r'(?<![가-힣])(?:숲|바다|생태|자연|동물|식물).{0,12}(?:장면|내용|이야기|주제)?\s*(?:은|는|이|가)?\s*(?:아니|없(?:었|다|고))'),
    '사회': re.compile(r'(?<![가-힣])(?:사회|정치|제도|노동).{0,10}(?:문제|이야기|내용|주제)\s*(?:은|는|이|가)?\s*(?:아니|없(?:었|다|고))'),
    '어둠': re.compile(r'(?<![가-힣])(?:죽음|공포|폭력|감시|상실).{0,12}(?:장면|내용|이야기|요소)?\s*(?:은|는|이|가)?\s*(?:아니|없(?:었|다|고))'),
}

WORLD_ANCHORS = {
    '상상': re.compile(r'(?<![가-힣])(?:마법|꿈|상상|시간여행|시간.{0,8}(?:거꾸로|되감|멈|백\s*년)|외계|다른\s*행성|가상\s*(?:세계|도시|국가)|(?:하루|아침|날짜|마을|도시).{0,24}(?:되돌아|반복|다시\s*시작|처음부터)|기억.{0,16}(?:병|옮|사고팔|거래|팔\s*수|살\s*수|지우|삭제)|현실에\s*없|비현실)'),
    '모험': re.compile(r'(?<![가-힣])(?:여행|여정|항해|항구|국경|목적지|기차.{0,10}갈아|배로.{0,10}섬|낯선.{0,8}(?:도시|곳)|탐험|등대|미지의\s*(?:해역|섬|땅)|비밀\s*통로|탐사|수색)'),
    '자연': re.compile(r'(?<![가-힣])(?:숲|바다|갯벌|생태|생물|동물|식물|계절|기후|나비|곤충|산불|철새|고래|습지|빙하|태풍|홍수|해수|산호|강물|하천|꽃)'),
    '사회': re.compile(r'(?<![가-힣])(?:임대료|계약(?:직|\s*형태)|고용\s*형태|병가|휴가|보험|정규직|비정규직|제도|정책|주거|재판|법\s*(?:절차|제도|체계)|법률|법원|법안|학교\s*규칙|회사\s*규정|권력|주민|노동|복지|교육|차별|불평등|지원금|재개발|투표|선거|공공)'),
    '어둠': re.compile(r'(?<![가-힣])(?:죽음|죽었|죽는|죽어|사망|사라진|실종|상실|공포|무서|불안|섬뜩|소름|감시|카메라.{0,10}기록|폭력|억압|격리|지워지|폐허|전쟁|밀려나|떠나야|들킬)')
}
STRONG_NATURE_ANCHOR = re.compile(r'(?<![가-힣])(?:기후|멸종|산불|철새|갯벌|습지|산호|해수|빙하|홍수)')
STRONG_DARK_ANCHOR = re.compile(r'(?<![가-힣])(?:감시\s*카메라|전쟁|폭력|폐허|사망|죽음|실종)')
STRUCTURAL_WORLD = ('상상','모험','자연','사회')


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


def _required_world_anchor_margin(trait: str, text: str) -> float:
    if trait == '자연' and STRONG_NATURE_ANCHOR.search(text):
        return STRONG_NATURE_MARGIN
    if trait == '어둠' and STRONG_DARK_ANCHOR.search(text):
        return STRONG_DARK_MARGIN
    return WORLD_ANCHORED_MARGIN


def _label_only_context(text: str) -> bool:
    has_label = bool(NAMING_OR_LABEL_CUE.search(text) or QUOTED_LABEL_CONTEXT.search(text))
    if not has_label:
        return False
    without_labels = QUOTED_SPAN.sub(' ', text)
    without_labels = UNQUOTED_LABEL_VALUE.sub(' ', without_labels)
    return not bool(WORLD_CONTENT_CUE.search(without_labels))


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
        required = RESPONSE_ANCHORED_MARGIN if RESPONSE_ANCHORS[trait].search(text) else RESPONSE_UNANCHORED_MARGIN
        if margin >= required:
            response[trait] = 1.0

    label_only = _label_only_context(text)
    metaphorical = bool(METAPHOR_CUE.search(text))
    visual_surface_only = bool(VISUAL_SURFACE_CUE.search(text)) and not bool(WORLD_CONTENT_CUE.search(text))

    predicted_anchored = [
        trait for trait in predicted_w
        if trait in STRUCTURAL_WORLD
        and WORLD_ANCHORS[trait].search(text)
        and (_as_float(scores, trait) - wn) >= _required_world_anchor_margin(trait, text)
    ]
    predicted_anchored.sort(key=lambda t: _as_float(scores, t), reverse=True)

    predicted_unanchored = [
        trait for trait in predicted_w
        if trait in STRUCTURAL_WORLD
        and trait not in predicted_anchored
        and not WORLD_ANCHORS[trait].search(text)
        and (_as_float(scores, trait) - wn) >= WORLD_SEMANTIC_FALLBACK_MARGIN
    ]
    predicted_unanchored.sort(key=lambda t: _as_float(scores, t), reverse=True)

    anchored_extras = [
        trait for trait in STRUCTURAL_WORLD
        if trait not in predicted_w
        and WORLD_ANCHORS[trait].search(text)
        and (_as_float(scores, trait) - wn) >= _required_world_anchor_margin(trait, text)
    ]
    anchored_extras.sort(key=lambda t: _as_float(scores, t), reverse=True)

    dark_candidates: list[str] = []
    if '어둠' in predicted_w:
        dark_candidates.append('어둠')
    elif WORLD_ANCHORS['어둠'].search(text) and (_as_float(scores,'어둠') - wn) >= _required_world_anchor_margin('어둠', text):
        dark_candidates.append('어둠')

    candidates = predicted_anchored + predicted_unanchored + anchored_extras + dark_candidates

    accepted: list[str] = []
    for trait in candidates:
        margin = _as_float(scores, trait) - wn
        anchor = bool(WORLD_ANCHORS[trait].search(text))
        if trait in accepted or label_only or NEGATED_ANCHORS[trait].search(text):
            continue
        if visual_surface_only:
            continue
        if trait == '상상' and IMAGINATION_METAPHOR_CUE.search(text):
            continue
        if anchor:
            if margin < _required_world_anchor_margin(trait, text):
                continue
            if metaphorical and margin < WORLD_SEMANTIC_FALLBACK_MARGIN:
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
