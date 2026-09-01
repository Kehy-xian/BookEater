from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.nlp.hybrid_classifier_v31 import HybridE5ClassifierV31
from bookeater.game.nutrition import project_growth_nutrition, NUTRITION_POLICY_VERSION

MODEL = ROOT / 'resources/models/multilingual-e5-small-onnx'
OUT = ROOT / 'tests/growth_nutrition_blind_v9.md'
JSON_OUT = ROOT / 'tests/growth_nutrition_blind_v9.json'
FROZEN_POLICY = 'growth-nutrition-v1.6.3'

# Integrity seal: these cases were authored only after v1.6.3 was frozen. If policy code changes
# before the first run, this script refuses to produce a "fresh" result.
assert NUTRITION_POLICY_VERSION == FROZEN_POLICY, (
    f'v9 freshness invalid: expected {FROZEN_POLICY}, got {NUTRITION_POLICY_VERSION}'
)


def C(cid, text, response_ok, world_required=(), world_allowed=None, category=''):
    wr = list(world_required)
    wa = list(world_allowed if world_allowed is not None else wr)
    return dict(id=cid, text=text, response_ok=list(response_ok), world_required=wr, world_allowed=wa, category=category)


CASES = [
    # Pure library/purchase/device bookkeeping: no nutritional growth.
    C('n01', '서점 앱 쿠폰이 오늘까지인지 유효기간 숫자만 확인했다.', [], category='neutral'),
    C('n02', '배송 조회 화면에서 책이 물류센터에 도착했는지만 봤다.', [], category='neutral'),
    C('n03', '전자책 설정 메뉴에서 화면 밝기와 글자 크기를 바꿨다.', [], category='neutral'),
    C('n04', '도서관 연체료가 천 원으로 표시되는지 결제 화면만 확인했다.', [], category='neutral'),
    C('n05', '읽던 곳을 잊지 않으려고 143쪽에 책갈피를 끼웠다.', [], category='neutral'),
    C('n06', '오디오북 목소리를 남성 음성으로 바꾸고 재생 속도를 1배로 돌렸다.', [], category='neutral'),
    C('n07', '예약 도서 수령 가능 날짜를 휴대폰 달력에 옮겨 적었다.', [], category='neutral'),
    C('n08', '두 판본의 출판사와 발행연도만 표로 정리했다.', [], category='neutral'),
    C('n09', '시리즈 다섯 권 중 세 번째 권을 이미 샀는지 구매 목록에서 확인했다.', [], category='neutral'),
    C('n10', '도서관 좌석 예약 시간이 끝나서 앱에서 퇴실 버튼을 눌렀다.', [], category='neutral'),
    C('n11', '전자책 메모 백업이 완료됐다는 알림을 확인하고 닫았다.', [], category='neutral'),
    C('n12', '읽고 싶은 책 폴더에서 품절된 책을 다른 목록으로 옮겼다.', [], category='neutral'),
    C('n13', '책 표지에 묻은 먼지를 닦고 투명 커버 모서리를 다시 붙였다.', [], category='neutral'),
    C('n14', '상호대차 신청 번호를 복사해 메모 앱에 저장했다.', [], category='neutral'),

    # Reader-response traits only.
    C('r01', '상대가 싫다고 했는데도 좋은 일이라는 이유로 밀어붙인 선택이 옳은지 생각했다.', ['사유'], category='response'),
    C('r02', '돌아올 자리를 계속 비워 두는 가족의 모습이 쓸쓸해서 마음이 오래 무거웠다.', ['감정'], category='response'),
    C('r03', '저자가 말한 실업률 변화가 실제 통계 원자료와 일치하는지 찾아보고 싶었다.', ['탐구'], category='response'),
    C('r04', '쉼표가 거의 없는 긴 문장을 소리 내 읽으니 숨이 차는 느낌이 강하게 났다.', ['감각'], category='response'),
    C('r05', '모두가 찬성했다고 해서 반대할 기회를 주지 않은 절차까지 정당해지는 건지 의문이다.', ['사유'], category='response'),
    C('r06', '아이가 아무렇지 않은 척 선물을 돌려주는 장면이 너무 짠했다.', ['감정'], category='response'),
    C('r07', '두 기사에서 같은 조사 결과를 서로 다르게 요약해서 보고서 원문을 대조해 봤다.', ['탐구'], category='response'),
    C('r08', '반복되는 ㅅ 소리가 비 내리는 소리처럼 들려 문장의 리듬이 인상적이었다.', ['감각'], category='response'),
    C('r09', '누군가를 살리기 위해 다른 사람의 비밀을 공개해도 되는지 쉽게 판단하기 어려웠다.', ['사유', '감정'], category='response'),
    C('r10', '마지막까지 이름을 불러 주지 못한 장면이 안타까워 계속 기억에 남았다.', ['감정'], category='response'),
    C('r11', '각주에 적힌 연구가 정말 같은 결론을 냈는지 논문을 직접 확인해 보고 싶다.', ['탐구'], category='response'),
    C('r12', '짧은 대사가 한 줄씩 떨어져 있어서 화면이 아니라 종이 위에서도 속도가 느려지는 느낌이었다.', ['감각'], category='response'),
    C('r13', '약속을 지키는 것과 더 큰 피해를 막는 것 중 무엇을 우선해야 할지 고민됐다.', ['사유'], category='response'),
    C('r14', '헤어진 뒤 평범하게 출근하는 인물의 모습이 오히려 더 먹먹하게 다가왔다.', ['감정'], category='response'),

    # Fantasy/social/dark words used only as names, UI labels, titles, design, or metaphor.
    C('d01', '“별의 바다”라는 향수 제품 설명에서 병 디자인과 글자 배치만 봤다.', ['감각', '탐구'], category='decoy'),
    C('d02', '‘개척자’는 독서 앱의 월간 배지 이름이고 획득 조건만 확인했다.', ['탐구'], category='decoy'),
    C('d03', '우주선 그림이 들어간 책갈피의 은색 인쇄가 예뻐 사진을 찍었다.', ['감각', '감정'], category='decoy'),
    C('d04', '회의실 분위기가 감옥 같았다는 표현이 답답함을 과장한 비유로 느껴졌다.', ['감각', '감정'], category='decoy'),
    C('d05', '“유령 도시”는 전시 구역 제목이고 나는 안내판 위치만 확인했다.', ['탐구'], category='decoy'),
    C('d06', '자연이라는 과목명이 시간표에서 초록색으로 표시돼 있었다.', ['탐구', '감각'], category='decoy'),
    C('d07', '사전의 ‘계급’ 표제어 옆에 붙은 발음 기호를 확인했다.', ['탐구', '감각'], category='decoy'),
    C('d08', '붉은 사막 사진을 쓴 표지가 다른 판본보다 더 마음에 들었다.', ['감각', '감정'], category='decoy'),
    C('d09', '문장이 미로처럼 꼬여 있다는 평이 복잡한 문체를 잘 설명했다.', ['감각'], category='decoy'),
    C('d10', '카페의 “시간 여행” 세트 메뉴가 영어판에는 다른 이름으로 적혀 있어 비교했다.', ['감각', '탐구'], category='decoy'),
    C('d11', '‘산불’은 우리 퀴즈 팀의 별명이고 이 기록은 점수 계산 방식만 적은 것이다.', ['탐구'], category='decoy'),
    C('d12', '표지의 검은 문 모양이 빛에 따라 반짝이는 인쇄 효과가 독특했다.', ['감각'], category='decoy'),
    C('d13', '여행 내용은 없고 “국경”이라는 장 제목만 다른 글꼴로 인쇄돼 있었다.', ['감각', '탐구'], category='decoy'),
    C('d14', '마음이 얼어붙은 것 같다는 표현이 감정을 짧게 보여 줘 인상적이었다.', ['감각', '감정'], category='decoy'),

    # Genuine world/topic content.
    C('w01', '잠들기 전에 기억 한 조각을 팔면 다음 날 그 일을 완전히 잊게 되는 시장이 등장했다.', ['사유', '감정'], ['상상'], ['상상', '사회', '어둠'], category='world'),
    C('w02', '자정이 지나면 도시 전체가 전날 아침으로 돌아오고 단 한 명만 변화를 기억한다.', ['사유', '감정'], ['상상'], ['상상', '어둠'], category='world'),
    C('w03', '사막의 우물을 따라 며칠씩 이동하며 지도에 없는 오아시스를 찾는 여정이 흥미로웠다.', ['감정'], ['모험'], ['모험', '자연'], category='world'),
    C('w04', '배가 고장 난 뒤 작은 섬들을 옮겨 다니며 귀환 항구를 찾는 과정이 긴장됐다.', ['감정'], ['모험'], ['모험', '자연', '어둠'], category='world'),
    C('w05', '봄 기온이 빨리 오르면서 꽃이 피는 시기와 벌의 활동 시기가 어긋난다는 설명이 인상적이었다.', ['감정', '탐구'], ['자연'], ['자연'], category='world'),
    C('w06', '산호 백화가 심한 구역에서 어린 물고기의 수가 줄었다는 자료를 다른 조사와 비교하고 싶었다.', ['탐구'], ['자연'], ['자연'], category='world'),
    C('w07', '휠체어 이용자는 출입할 수 없는 주민센터를 그대로 두는 행정이 공정한지 생각했다.', ['사유'], ['사회'], ['사회'], category='world'),
    C('w08', '같은 일을 해도 파견 노동자에게만 안전교육 시간을 임금에서 빼는 규정이 이상했다.', ['사유', '감정'], ['사회'], ['사회'], category='world'),
    C('w09', '사라진 아이의 방에서 매일 밤 발자국 소리만 반복해서 들리는 장면이 무서웠다.', ['감정'], ['어둠'], ['어둠', '상상'], category='world'),
    C('w10', '감시 요원이 주민의 통화 기록을 매주 검사하는 도시라니 숨이 막히는 느낌이었다.', ['감정', '사유'], ['어둠', '사회'], ['어둠', '사회'], category='world'),
    C('w11', '꿈을 다른 사람에게 빌려주고 이자를 받는 가상 국가의 은행 제도가 기묘했다.', ['사유', '감정'], ['상상', '사회'], ['상상', '사회'], category='world'),
    C('w12', '가뭄 때 농업용수를 기업에 먼저 배분하는 정책 때문에 작은 농가가 피해를 보는 구조를 생각했다.', ['사유'], ['자연', '사회'], ['자연', '사회'], category='world'),
    C('w13', '외계 위성의 얼음 동굴에서 통신 기지를 찾아 이동하는 탐사 장면이 신났다.', ['감정'], ['상상', '모험'], ['상상', '모험', '자연'], category='world'),
    C('w14', '사람의 남은 수명을 화폐처럼 교환할 수 있어 가난한 사람이 시간을 파는 설정이 씁쓸했다.', ['사유', '감정'], ['상상', '사회'], ['상상', '사회', '어둠'], category='world'),
    C('w15', '폭염이 길어지자 하천의 산소량이 줄고 물고기 폐사가 늘었다는 연구를 더 확인하고 싶었다.', ['탐구'], ['자연'], ['자연'], category='world'),
    C('w16', '학교가 학생의 개인 메시지를 허락 없이 열람하는 규칙을 두고 있다는 설정이 불편했다.', ['사유', '감정'], ['사회'], ['사회', '어둠'], category='world'),
    C('w17', '검문소를 피해 화물열차에 숨어 국경을 건너는 남매의 이동이 너무 긴장됐다.', ['감정'], ['모험'], ['모험', '어둠', '사회'], category='world'),
    C('w18', '야간 조명이 해변 거북 새끼가 바다 방향을 찾는 데 방해가 된다는 연구가 흥미로웠다.', ['탐구', '감정'], ['자연'], ['자연', '사회'], category='world'),
    C('w19', '채용 알고리즘이 특정 지역 우편번호 지원자를 자동 탈락시키는 제도가 차별적이라고 느꼈다.', ['사유', '감정'], ['사회'], ['사회'], category='world'),
    C('w20', '무너진 광산 안으로 실종된 동료를 찾으러 내려가 탈출로를 찾는 장면이 숨 막혔다.', ['감정'], ['모험', '어둠'], ['모험', '어둠'], category='world'),
    C('w21', '거울 속 사람이 밤마다 현실의 주인공과 자리를 바꾸려 한다는 설정이 섬뜩했다.', ['감정'], ['상상', '어둠'], ['상상', '어둠'], category='world'),
    C('w22', '해안 방조제 건설을 두고 어촌 주민의 생계와 습지 보전이 충돌하는 부분을 더 생각해 보고 싶었다.', ['사유', '탐구'], ['자연', '사회'], ['자연', '사회'], category='world'),

    # Real content survives surrounding logistics/surface cues.
    C('m01', '143쪽에 책갈피를 옮기다 다시 읽었는데 모두를 위한 결정이라는 말로 한 사람의 선택을 무시해도 되는지 고민됐다.', ['사유'], category='mixed'),
    C('m02', '표지의 바다 사진보다 산호 백화 뒤 생물 종이 줄어드는 설명이 더 궁금해 원자료를 찾아보고 싶었다.', ['탐구', '감각'], ['자연'], ['자연'], category='mixed'),
    C('m03', '전자책 목차에서 주거 장을 다시 열어 임대료 지원 기준에서 빠지는 사람이 생기는 이유를 생각했다.', ['사유', '탐구'], ['사회'], ['사회'], category='mixed'),
    C('m04', '지도 그림의 색은 평범했지만 폭풍을 피해 섬에서 섬으로 이동하는 항해는 오래 기억에 남았다.', ['감정', '감각'], ['모험'], ['모험', '자연', '어둠'], category='mixed'),
    C('m05', '오디오북 재생 위치를 다시 맞춰 들었는데 헤어지는 장면의 마지막 한마디가 너무 쓸쓸했다.', ['감정'], category='mixed'),
    C('m06', '반납 날짜를 확인하다 기후 장을 다시 읽고 폭염 통계의 원자료까지 대조해 보고 싶어졌다.', ['탐구'], ['자연'], ['자연'], category='mixed'),
    C('m07', '검은 삽화보다 주민의 위치를 매일 추적하는 감시 제도가 훨씬 더 무섭게 느껴졌다.', ['감정', '사유'], ['어둠', '사회'], ['어둠', '사회'], category='mixed'),
    C('m08', '책갈피를 정리하다 다시 읽은 장에서 기억을 돈 주고 살 수 있는 도시의 규칙이 계속 마음에 걸렸다.', ['사유', '감정'], ['상상'], ['상상', '사회'], category='mixed'),
]
assert len(CASES) == 72

clf = HybridE5ClassifierV31(MODEL)
rows = []
for c in CASES:
    analysis = clf.analyze(c['text'])
    nutrition = project_growth_nutrition(c['text'], analysis)
    rows.append({**c, 'response': list(nutrition.response), 'world': list(nutrition.world), 'analysis': analysis})

s = dict(neutral=0, neutral_ok=0, response_req=0, response_hit=0, response_pred=0, response_good=0,
         world_req=0, world_hit=0, world_pred=0, world_good=0, world_null=0, world_clean=0,
         mixed=0, mixed_survive=0, exact=0)
watch = []
for r in rows:
    pr, pw = list(r['response']), list(r['world'])
    rok, wr, wa = set(r['response_ok']), set(r['world_required']), set(r['world_allowed'])
    if r['category'] == 'neutral':
        s['neutral'] += 1; s['neutral_ok'] += not pr and not pw
    if r['category'] == 'mixed':
        s['mixed'] += 1; s['mixed_survive'] += bool(pr or pw)
    if rok:
        s['response_req'] += 1; s['response_hit'] += bool(pr and pr[0] in rok)
    s['response_pred'] += len(pr); s['response_good'] += sum(x in rok for x in pr)
    s['world_req'] += len(wr); s['world_hit'] += len(wr & set(pw))
    s['world_pred'] += len(pw); s['world_good'] += sum(x in wa for x in pw)
    if not wr:
        s['world_null'] += 1; s['world_clean'] += not pw
    response_exact = (not rok and not pr) or (bool(pr) and pr[0] in rok)
    world_exact = wr.issubset(set(pw)) and set(pw).issubset(wa)
    s['exact'] += response_exact and world_exact
    if not (response_exact and world_exact): watch.append(r)

pct = lambda a, b: 100 * a / b if b else 100.0
metrics = {
    'neutral_empty': pct(s['neutral_ok'], s['neutral']),
    'mixed_survival': pct(s['mixed_survive'], s['mixed']),
    'response_recall': pct(s['response_hit'], s['response_req']),
    'response_precision': pct(s['response_good'], s['response_pred']),
    'world_required_recall': pct(s['world_hit'], s['world_req']),
    'world_precision': pct(s['world_good'], s['world_pred']),
    'world_null_clean': pct(s['world_clean'], s['world_null']),
    'exact_records': pct(s['exact'], len(rows)),
}
targets = {
    'neutral_empty': 96, 'mixed_survival': 82,
    'response_recall': 74, 'response_precision': 91,
    'world_required_recall': 84, 'world_precision': 94,
    'world_null_clean': 97,
}
passed = all(metrics[k] >= v for k, v in targets.items())
labels = {
    'neutral_empty': 'neutral adds no nutrition',
    'mixed_survival': 'mixed substantive notes survive',
    'response_recall': 'response recall',
    'response_precision': 'response precision',
    'world_required_recall': 'required world recall',
    'world_precision': 'world modifier precision',
    'world_null_clean': 'no-world abstention',
    'exact_records': 'product-exact records',
}
lines = [
    '# BookEater hidden growth fresh blind v9', '',
    '- classifier: `e5-hybrid-v3.1.1`',
    f'- sealed growth projector: `{FROZEN_POLICY}`',
    '- cases authored after that policy was frozen; script aborts if the policy changes before first run',
    '- after the first execution, this set becomes regression/diagnostic only', '',
    '|metric|result|target|', '|---|---:|---:|',
]
for k in metrics:
    target = f">={targets[k]}%" if k in targets else 'diagnostic'
    lines.append(f"|{labels[k]}|{metrics[k]:.1f}%|{target}|")
lines += ['', f"**release-style gate: {'PASS' if passed else 'FAIL'}**", '', '## Watchlist', '']
for r in watch:
    lines.append(
        f"- {r['id']} [{r['category']}] response={r['response']} ok={r['response_ok']} "
        f"world={r['world']} required={r['world_required']} allowed={r['world_allowed']} :: {r['text']}"
    )

OUT.parent.mkdir(exist_ok=True)
OUT.write_text('\n'.join(lines), encoding='utf-8')
JSON_OUT.write_text(json.dumps({'metrics': metrics, 'targets': targets, 'passed': passed, 'rows': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
print('\n'.join(lines))
if not passed:
    raise SystemExit(2)
