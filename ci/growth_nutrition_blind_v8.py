from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.nlp.hybrid_classifier_v31 import HybridE5ClassifierV31
from bookeater.game.nutrition import project_growth_nutrition, NUTRITION_POLICY_VERSION

MODEL = ROOT / 'resources/models/multilingual-e5-small-onnx'
OUT = ROOT / 'tests/growth_nutrition_blind_v8.md'
JSON_OUT = ROOT / 'tests/growth_nutrition_blind_v8.json'
AUTHORED_AFTER = 'growth-nutrition-v1.6.2'


def C(cid, text, response_ok, world_required=(), world_allowed=None, category=''):
    wr = list(world_required)
    wa = list(world_allowed if world_allowed is not None else wr)
    return dict(id=cid, text=text, response_ok=list(response_ok), world_required=wr, world_allowed=wa, category=category)


# Fresh holdout: authored after v1.6.2 was frozen and before any v8 execution.
# The first workflow execution is the blind result. Any later execution is regression/diagnostic only.
CASES = [
    # Reading logistics, purchase/library/app state: absolutely no growth.
    C('n01', '예약한 책이 도착했다는 문자에서 보관 기한만 확인하고 알림을 지웠다.', [], category='neutral'),
    C('n02', '전자책 파일을 새 기기로 내려받고 다운로드 완료 표시만 확인했다.', [], category='neutral'),
    C('n03', '중고책 주문 배송 조회에서 택배가 집하 완료인지 확인했다.', [], category='neutral'),
    C('n04', '도서관 회원증 바코드가 앱에 제대로 뜨는지만 확인했다.', [], category='neutral'),
    C('n05', '개정판과 초판의 ISBN이 다른지 서지정보 화면에서 번호만 대조했다.', [], category='neutral'),
    C('n06', '읽을 책 목록에서 다 읽은 책을 완료 폴더로 옮겼다.', [], category='neutral'),
    C('n07', '오디오북 재생 속도를 1.2배로 바꾸고 이어폰 볼륨을 조절했다.', [], category='neutral'),
    C('n08', '책을 어느 서점에서 샀는지 영수증 날짜와 결제 금액만 기록했다.', [], category='neutral'),
    C('n09', '상호대차 신청이 승인됐는지 상태 표시만 새로고침했다.', [], category='neutral'),
    C('n10', '읽던 책의 남은 대출 기간이 이틀인지 앱에서 확인했다.', [], category='neutral'),
    C('n11', '시리즈 합본판에 몇 권이 들어 있는지 권수 정보만 적어 두었다.', [], category='neutral'),
    C('n12', '표지 커버가 벗겨져 투명 비닐을 다시 씌우고 책장에 꽂았다.', [], category='neutral'),
    C('n13', '전자책 형광펜 동기화가 끝났다는 표시를 보고 설정 창을 닫았다.', [], category='neutral'),
    C('n14', '읽기 목표를 주 4회로 바꾸고 알림 시간을 밤 아홉 시로 설정했다.', [], category='neutral'),

    # Reader response. These should feed body/response traits but no world modifier is required.
    C('r01', '친구를 위한 선택이라도 당사자에게 말하지 않고 결정한 건 옳지 않은 것 같아 오래 생각했다.', ['사유'], category='response'),
    C('r02', '아버지의 편지를 끝내 읽지 못하고 접어 두는 장면에서 마음이 먹먹해졌다.', ['감정'], category='response'),
    C('r03', '책에 나온 통계가 최신 조사에서도 비슷한지 원자료를 찾아 확인해 보고 싶었다.', ['탐구'], category='response'),
    C('r04', '같은 자음이 연달아 반복되는 문장이 혀에 걸리는 느낌까지 의도한 것 같아 재미있었다.', ['감각'], category='response'),
    C('r05', '다수에게 편리하다는 이유로 소수의 불편을 당연하게 여겨도 되는지 의문이 들었다.', ['사유'], category='response'),
    C('r06', '기다리던 사람이 끝내 오지 않았다는 걸 알아차리는 순간이 너무 허전했다.', ['감정'], category='response'),
    C('r07', '저자가 제시한 연도별 수치를 다른 기관 자료와 직접 대조해 보고 싶었다.', ['탐구'], category='response'),
    C('r08', '번역본 두 권의 첫 문장을 소리 내 읽어 보니 리듬이 완전히 달랐다.', ['감각', '탐구'], category='response'),
    C('r09', '잘못을 인정하면 더 큰 피해가 생긴다는 이유로 침묵한 선택을 이해해야 할지 고민됐다.', ['사유', '감정'], category='response'),
    C('r10', '동생에게 괜찮다고 웃어 주면서 혼자 우는 인물이 안쓰러워 마음에 남았다.', ['감정'], category='response'),
    C('r11', '서로 반대되는 주장에 같은 연구가 인용돼 있어서 원문을 확인하고 싶어졌다.', ['탐구'], category='response'),
    C('r12', '짧은 단어가 툭툭 끊기는 문체 때문에 발걸음이 빨라지는 것처럼 읽혔다.', ['감각'], category='response'),
    C('r13', '규칙을 어긴 사람을 무조건 배제하는 게 정말 공정한 해결인지 생각했다.', ['사유'], category='response'),
    C('r14', '마지막 인사를 평범하게 주고받는 장면이라 더 슬프고 오래 기억에 남았다.', ['감정'], category='response'),

    # World-looking words used as labels, surfaces, metadata or figures of speech: world must abstain.
    C('d01', '“달의 숲”은 문구점 노트 제품명이고 나는 종이 두께만 비교했다.', ['감각', '탐구'], category='decoy'),
    C('d02', '앱에서 ‘탐험가’라는 배지를 얻는 조건이 독서 일수인지 확인했다.', ['탐구'], category='decoy'),
    C('d03', '표지에 그려진 행성과 별의 은박이 조명에 반짝여서 예뻤다.', ['감각', '감정'], category='decoy'),
    C('d04', '시험 기간이 전쟁 같았다는 비유가 과장되어 있어서 웃겼다.', ['감각', '감정'], category='decoy'),
    C('d05', '‘감옥’은 방탈출 카페의 테마 이름이고 이용 시간표만 읽었다.', ['탐구'], category='decoy'),
    C('d06', '자연 과목이라는 분류명이 어느 색 라벨로 표시되는지 확인했다.', ['탐구', '감각'], category='decoy'),
    C('d07', '사전에서 ‘혁명’ 표제어가 몇 쪽에 있는지만 찾아 책갈피를 끼웠다.', ['탐구'], category='decoy'),
    C('d08', '바다 무늬 책커버의 파란색이 책상과 잘 어울려 마음에 들었다.', ['감각', '감정'], category='decoy'),
    C('d09', '문장이 파도처럼 밀려온다는 평이 이 작가의 긴 호흡을 잘 표현한 것 같았다.', ['감각'], category='decoy'),
    C('d10', '“마법”이라는 디저트 메뉴 이름의 영어 번역이 매장마다 달라 비교해 봤다.', ['감각', '탐구'], category='decoy'),
    C('d11', '‘빙하’는 우리 독서모임 팀명이고 이번 글은 모임 순서를 정한 기록뿐이다.', ['탐구'], category='decoy'),
    C('d12', '검은 잉크 얼룩이 번지는 면지의 인쇄 질감이 독특했다.', ['감각'], category='decoy'),
    C('d13', '실제 항해 내용은 없고 “항해”라는 장 제목의 글자 디자인만 유난히 컸다.', ['감각', '탐구'], category='decoy'),
    C('d14', '시간이 얼어붙은 것 같다는 표현이 정적을 선명하게 느끼게 했다.', ['감각'], category='decoy'),

    # Genuine fictional world/topic content.
    C('w01', '사람이 잠들 때마다 하루치 기억을 다른 사람에게 전송할 수 있는 마을의 규칙이 신기했다.', ['감정', '사유'], ['상상'], ['상상', '사회'], category='world'),
    C('w02', '주인공이 문을 열 때마다 같은 월요일 아침으로 돌아오는 설정이 답답하면서도 흥미로웠다.', ['감정'], ['상상'], ['상상', '어둠'], category='world'),
    C('w03', '폭풍을 피해 여러 항구를 옮겨 다니며 북쪽 섬을 찾아가는 항해가 긴장됐다.', ['감정'], ['모험'], ['모험', '자연', '어둠'], category='world'),
    C('w04', '기차와 버스를 여섯 번 갈아타며 낯선 국경 도시까지 가는 여정이 기억에 남았다.', ['감정'], ['모험'], ['모험', '사회'], category='world'),
    C('w05', '해안 습지가 줄어들자 철새의 먹이와 이동 시기가 함께 달라졌다는 설명이 인상적이었다.', ['감정', '탐구'], ['자연'], ['자연'], category='world'),
    C('w06', '산호가 죽은 뒤 작은 물고기 종의 수가 줄어드는 과정을 다른 연구와 비교해 보고 싶었다.', ['탐구'], ['자연'], ['자연'], category='world'),
    C('w07', '계약직에게만 병가를 쓰기 어렵게 만든 회사 규정이 왜 유지되는지 이해되지 않았다.', ['사유', '감정'], ['사회'], ['사회'], category='world'),
    C('w08', '공공임대 입주 기준 때문에 같은 형편의 가족들이 서로 다른 결과를 받는 구조가 불공평해 보였다.', ['사유', '감정'], ['사회'], ['사회'], category='world'),
    C('w09', '아무도 없는 방에서 죽은 친구의 목소리가 녹음기에서 다시 들리는 장면이 섬뜩했다.', ['감정'], ['어둠'], ['어둠', '상상'], category='world'),
    C('w10', '폐쇄된 병동의 모든 문에 감시 카메라가 달려 있고 환자는 혼자 나갈 수 없다는 설정이 무서웠다.', ['감정', '사유'], ['어둠'], ['어둠', '사회'], category='world'),
    C('w11', '가상 도시에서는 시민의 기억 점수에 따라 취업과 투표 자격이 달라진다는 제도가 기묘했다.', ['사유', '감정'], ['상상', '사회'], ['상상', '사회', '어둠'], category='world'),
    C('w12', '홍수 뒤 지원금을 받는 기준에서 세입자가 빠지는 정책이 공정한지 생각했다.', ['사유'], ['자연', '사회'], ['자연', '사회'], category='world'),
    C('w13', '다른 행성의 붉은 사막에서 귀환선을 찾기 위해 며칠씩 이동하는 탐사가 신났다.', ['감정'], ['상상', '모험'], ['상상', '모험', '자연'], category='world'),
    C('w14', '수명을 몇 년씩 사고팔 수 있는 사회에서 돈 없는 사람이 먼저 시간을 잃는 설정이 씁쓸했다.', ['사유', '감정'], ['상상', '사회'], ['상상', '사회', '어둠'], category='world'),
    C('w15', '가뭄이 길어지면서 하천 수온이 오르고 물고기 산란지가 줄었다는 자료를 더 확인하고 싶었다.', ['탐구'], ['자연'], ['자연'], category='world'),
    C('w16', '기숙학교에서 학생들의 편지와 통화를 전부 기록한다는 규칙이 소름 끼쳤다.', ['감정', '사유'], ['어둠', '사회'], ['어둠', '사회'], category='world'),
    C('w17', '전쟁을 피해 가족이 야간 열차와 산길을 번갈아 이용해 국경을 넘는 과정이 숨 막혔다.', ['감정'], ['모험', '어둠'], ['모험', '어둠', '사회'], category='world'),
    C('w18', '도로 조명 때문에 밤에 움직이는 곤충이 줄고 박쥐의 먹이 활동도 달라졌다는 연구가 흥미로웠다.', ['탐구', '감정'], ['자연'], ['자연', '사회'], category='world'),
    C('w19', '학교 규칙상 같은 행동인데 장학생에게만 더 무거운 벌을 주는 방식이 납득되지 않았다.', ['사유', '감정'], ['사회'], ['사회'], category='world'),
    C('w20', '실종된 사람을 찾으러 폐허가 된 터널을 지나 지하 도시로 내려가는 장면이 긴장됐다.', ['감정'], ['모험', '어둠'], ['모험', '어둠', '상상'], category='world'),
    C('w21', '한밤중에 이름을 부르면 그림자 속 존재가 대답한다는 마을 전설이 무서웠다.', ['감정'], ['상상', '어둠'], ['상상', '어둠'], category='world'),
    C('w22', '갯벌 매립을 두고 어민의 생계와 철새 서식지 보호가 충돌하는 부분을 더 생각해 보고 싶었다.', ['사유', '탐구'], ['자연', '사회'], ['자연', '사회'], category='world'),

    # Logistics/surface cue plus genuine reading content: the meaningful part must still feed growth.
    C('m01', '대출 기한을 확인하다 표시해 둔 문장을 다시 읽었는데 선한 의도면 거짓말도 괜찮은지 고민됐다.', ['사유'], category='mixed'),
    C('m02', '표지의 꽃 그림보다 도시 개발 뒤 습지 식물이 줄어든 이유를 설명한 부분이 더 궁금했다.', ['탐구', '감각'], ['자연'], ['자연', '사회'], category='mixed'),
    C('m03', '전자책 목차에서 노동 장을 다시 열어 계약직의 휴가 규정이 다른 이유를 생각했다.', ['사유', '탐구'], ['사회'], ['사회'], category='mixed'),
    C('m04', '지도 삽화의 색은 단순했지만 배를 갈아타며 세 개의 섬을 찾아가는 여정은 정말 설렜다.', ['감정', '감각'], ['모험'], ['모험', '자연'], category='mixed'),
    C('m05', '오디오북 속도를 원래대로 돌려 다시 들었는데 마지막 작별 대사가 너무 먹먹했다.', ['감정'], category='mixed'),
    C('m06', '반납 알림을 보고 기후 장을 다시 펼쳐 홍수 통계의 출처가 맞는지 원자료를 확인하고 싶었다.', ['탐구'], ['자연'], ['자연', '사회'], category='mixed'),
    C('m07', '검은 표지보다 주민의 통화를 정부가 모두 녹음하는 제도가 훨씬 더 섬뜩했다.', ['감정', '사유'], ['어둠', '사회'], ['어둠', '사회'], category='mixed'),
    C('m08', '책갈피를 옮기다 다시 읽은 장에서 기억을 사고파는 도시의 계급 제도가 계속 마음에 걸렸다.', ['사유', '감정'], ['상상', '사회'], ['상상', '사회', '어둠'], category='mixed'),
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
        s['neutral'] += 1
        s['neutral_ok'] += not pr and not pw
    if r['category'] == 'mixed':
        s['mixed'] += 1
        s['mixed_survive'] += bool(pr or pw)
    if rok:
        s['response_req'] += 1
        s['response_hit'] += bool(pr and pr[0] in rok)
    s['response_pred'] += len(pr)
    s['response_good'] += sum(x in rok for x in pr)
    s['world_req'] += len(wr)
    s['world_hit'] += len(wr & set(pw))
    s['world_pred'] += len(pw)
    s['world_good'] += sum(x in wa for x in pw)
    if not wr:
        s['world_null'] += 1
        s['world_clean'] += not pw
    response_exact = (not rok and not pr) or (bool(pr) and pr[0] in rok)
    world_exact = wr.issubset(set(pw)) and set(pw).issubset(wa)
    s['exact'] += response_exact and world_exact
    if not (response_exact and world_exact):
        watch.append(r)

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
    'neutral_empty': 96,
    'mixed_survival': 82,
    'response_recall': 74,
    'response_precision': 91,
    'world_required_recall': 84,
    'world_precision': 94,
    'world_null_clean': 97,
}
passed = all(metrics[k] >= target for k, target in targets.items())
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
    '# BookEater hidden growth fresh blind v8', '',
    '- classifier: `e5-hybrid-v3.1.1`',
    f'- growth projector at first run: `{NUTRITION_POLICY_VERSION}`',
    f'- cases authored after `{AUTHORED_AFTER}` was frozen and before any v8 execution',
    '- after the first execution, this set becomes regression/diagnostic only', '',
    '|metric|result|target|', '|---|---:|---:|',
]
for key in metrics:
    target = f">={targets[key]}%" if key in targets else 'diagnostic'
    lines.append(f"|{labels[key]}|{metrics[key]:.1f}%|{target}|")
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
