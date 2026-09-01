from __future__ import annotations
import json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bookeater.nlp.hybrid_classifier_v31 import HybridE5ClassifierV31
from bookeater.game.nutrition import project_growth_nutrition

MODEL=ROOT/'resources/models/multilingual-e5-small-onnx'
OUT=ROOT/'tests/growth_nutrition_blind_v7.md'; JSON_OUT=ROOT/'tests/growth_nutrition_blind_v7.json'

def C(cid,text,response_ok,world_required=(),world_allowed=None,category=''):
    wr=list(world_required); wa=list(world_allowed if world_allowed is not None else wr)
    return dict(id=cid,text=text,response_ok=list(response_ok),world_required=wr,world_allowed=wa,category=category)

# Fresh holdout authored only after growth-nutrition-v1.6.1 was frozen.
# First execution is the only blind run; every rerun afterwards is diagnostic.
CASES=[
# Pure reading logistics / device state / bibliography: no growth.
C('n01','대출 연장 버튼을 눌렀고 새 반납 예정일만 달력에 적었다.',[],category='neutral'),
C('n02','전자책 줄 간격을 넓히고 글꼴을 바꾼 뒤 설정 창을 닫았다.',[],category='neutral'),
C('n03','오디오북 다운로드가 74퍼센트에서 멈춰 와이파이를 다시 연결했다.',[],category='neutral'),
C('n04','희망도서 신청 상태가 주문 중으로 바뀌었는지만 확인했다.',[],category='neutral'),
C('n05','책 뒤 판권면에서 2쇄 발행일과 출판사 주소를 확인했다.',[],category='neutral'),
C('n06','상하권을 헷갈리지 않게 책등에 작은 메모지를 붙였다.',[],category='neutral'),
C('n07','서가 위치가 813.7에서 813.6으로 바뀌어 청구기호를 다시 적었다.',[],category='neutral'),
C('n08','읽기 앱 통계에서 이번 주 독서 시간이 3시간인지 확인했다.',[],category='neutral'),
C('n09','예약 순번이 5번에서 4번으로 줄었다는 알림을 확인했다.',[],category='neutral'),
C('n10','종이책에 끼워 둔 영수증을 빼고 책갈피를 새로 꽂았다.',[],category='neutral'),
C('n11','같은 저자의 책 두 권을 구분하려고 표지 사진 파일명을 바꿨다.',[],category='neutral'),
C('n12','도서관 앱 로그인이 풀려 비밀번호를 다시 입력했다.',[],category='neutral'),
C('n13','읽던 위치가 초기화돼 216쪽으로 이동해 놓고 앱을 종료했다.',[],category='neutral'),
C('n14','시리즈 네 번째 권이 맞는지 권차 정보만 확인했다.',[],category='neutral'),

# Reader-response/body signals; no world modifier required.
C('r01','누군가를 보호하려고 거짓말한 행동을 어디까지 정당화할 수 있는지 고민됐다.',['사유'],category='response'),
C('r02','마지막에 혼자 밥을 먹는 아이가 너무 안쓰러워 한동안 마음이 무거웠다.',['감정'],category='response'),
C('r03','저자가 인용한 실험 결과가 원 논문에서도 같은 수치인지 찾아보고 싶었다.',['탐구'],category='response'),
C('r04','짧고 딱딱한 문장 뒤에 긴 문장이 이어져 호흡이 확 달라지는 느낌이 좋았다.',['감각'],category='response'),
C('r05','규칙을 지킨 사람만 손해 보는 상황이라면 규칙을 지키는 게 옳은지 생각했다.',['사유'],category='response'),
C('r06','둘이 다시 만났는데도 예전처럼 말하지 못하는 장면이 서글펐다.',['감정'],category='response'),
C('r07','도표의 비율을 직접 다시 계산해 보니 본문의 설명과 조금 달랐다.',['탐구'],category='response'),
C('r08','같은 대사가 번역본마다 말투가 달라서 소리 내 읽으며 비교했다.',['감각','탐구'],category='response'),
C('r09','결과가 좋았다는 이유만으로 상대의 동의를 무시해도 되는지 납득되지 않았다.',['사유','감정'],category='response'),
C('r10','문을 닫고 돌아서는 마지막 모습이 오래 마음에 남아서 괜히 씁쓸했다.',['감정'],category='response'),
C('r11','서로 다른 두 자료가 같은 사건의 날짜를 다르게 적은 이유를 더 확인하고 싶었다.',['탐구'],category='response'),
C('r12','낮은 음이 반복되는 문장을 읽는데 정말 북소리처럼 울리는 기분이 들었다.',['감각'],category='response'),
C('r13','도와준다는 명분이 상대의 선택권을 빼앗을 수도 있다는 생각이 들었다.',['사유'],category='response'),
C('r14','아무도 울지 않는 장례식 장면이 오히려 더 슬프게 느껴졌다.',['감정'],category='response'),

# Names, titles, design, dictionaries and metaphors: world must abstain.
C('d01','“숲의 편지”라는 노트 제품의 종이 질감과 줄 간격을 비교했다.',['감각','탐구'],category='decoy'),
C('d02','‘모험가’는 앱의 사용자 등급 이름이고 이번 설명은 포인트 적립 방식이었다.',['탐구'],category='decoy'),
C('d03','표지의 우주 그림과 은색 글자가 잘 어울려 디자인이 마음에 들었다.',['감각','감정'],category='decoy'),
C('d04','회의가 전쟁 같았다는 표현이 과장된 비유라는 점이 재미있었다.',['감각','감정'],category='decoy'),
C('d05','“감시자”라는 영화관 좌석 구역 이름이 표에 어떻게 표시되는지만 확인했다.',['탐구'],category='decoy'),
C('d06','자연스럽게 이어 읽는 발음법을 설명한 부분에서 호흡 위치를 따라 해 봤다.',['감각','탐구'],category='decoy'),
C('d07','‘사회’라는 단어가 들어간 사전 표제어의 가나다순 위치를 찾았다.',['탐구'],category='decoy'),
C('d08','바다색 표지와 모래색 책등의 색 조합이 예뻐서 사진을 찍었다.',['감각','감정'],category='decoy'),
C('d09','문장을 산길처럼 굽이치게 썼다는 평론가의 표현이 문체를 잘 설명했다.',['감각'],category='decoy'),
C('d10','마법이라는 이름의 칵테일이 등장했지만 나는 번역된 메뉴 이름만 비교했다.',['감각','탐구'],category='decoy'),
C('d11','‘기후’는 동아리 프로젝트 팀명이고 본문은 발표 순서 정하는 방법뿐이었다.',['탐구'],category='decoy'),
C('d12','검은 그림자 무늬가 반복되는 면지 디자인이 독특했다.',['감각'],category='decoy'),
C('d13','여행 장면은 전혀 없고 “여행”이라는 제목이 왜 붙었는지만 편집자 후기에 적혀 있었다.',['탐구','사유'],category='decoy'),
C('d14','시간이 멈춘 듯 조용했다는 한 문장의 비유가 장면의 정적을 잘 살렸다.',['감각'],category='decoy'),

# Strong world/topic content.
C('w01','사람의 기억을 복사해 다른 몸에 넣을 수 있는 도시의 규칙이 기묘했다.',['사유','감정'],['상상'],['상상','사회'],category='world'),
C('w02','매일 해가 뜨면 전날 일어난 사건이 모두 되감기고 주인공만 기억한다.',['감정','사유'],['상상'],['상상','어둠'],category='world'),
C('w03','지도에 없는 섬을 찾아 작은 범선으로 몇 달 동안 항해하는 과정이 설렜다.',['감정'],['모험'],['모험','자연'],category='world'),
C('w04','폭설 속에서 산맥을 넘어 다음 마을까지 식량을 운반하는 여정이 긴장됐다.',['감정'],['모험'],['모험','자연','어둠'],category='world'),
C('w05','도시의 야간 조명이 철새 이동 경로에 어떤 영향을 주는지 다른 자료도 찾아보고 싶었다.',['탐구'],['자연'],['자연','사회'],category='world'),
C('w06','해수면 상승으로 섬의 식생 범위가 줄어드는 과정을 지도 자료와 비교해 봤다.',['탐구'],['자연'],['자연'],category='world'),
C('w07','육아휴직을 썼다는 이유로 승진 심사에서 불이익을 받는 제도가 공정한지 생각했다.',['사유','감정'],['사회'],['사회'],category='world'),
C('w08','동네 재개발 투표에서 세입자는 의사결정에 참여할 수 없는 구조가 이상했다.',['사유'],['사회'],['사회'],category='world'),
C('w09','사망한 사람의 목소리를 흉내 내는 전화가 밤마다 걸려오는 장면이 무서웠다.',['감정'],['어둠'],['어둠','상상'],category='world'),
C('w10','전쟁터에서 실종된 사람들의 이름이 기록에서 하나씩 지워지는 설정이 섬뜩했다.',['감정'],['어둠'],['어둠','사회'],category='world'),
C('w11','가상 국가에서 세금을 더 낸 사람에게만 투표권을 주는 제도가 등장해 불공평하게 느껴졌다.',['사유','감정'],['상상','사회'],['상상','사회','어둠'],category='world'),
C('w12','산불 뒤 임시주택 지원 기준 때문에 같은 마을 주민들의 처지가 갈리는 과정이 마음에 걸렸다.',['사유','감정'],['자연','사회'],['자연','사회','어둠'],category='world'),
C('w13','외계 행성의 얼음 바다를 조사하기 위해 탐사선이 미지의 해협으로 들어가는 장면이 신났다.',['감정'],['상상','모험'],['상상','모험','자연'],category='world'),
C('w14','기억을 담보로 돈을 빌릴 수 있는 사회에서 가난한 사람부터 과거를 잃는 설정이 씁쓸했다.',['사유','감정'],['상상','사회'],['상상','사회','어둠'],category='world'),
C('w15','빙하가 줄면서 하류의 농업용수가 부족해지는 원인을 강수량 자료와 함께 확인하고 싶었다.',['탐구'],['자연'],['자연','사회'],category='world'),
C('w16','평범한 기숙사인데 복도와 방 안의 대화가 모두 녹음되는 규칙이 소름 끼쳤다.',['감정','사유'],['어둠'],['어둠','사회'],category='world'),
C('w17','검문을 피해 밤마다 다른 길로 국경을 넘는 가족의 이동 과정이 숨 막혔다.',['감정'],['모험'],['모험','어둠','사회'],category='world'),
C('w18','멸종 위기 개구리가 도로 때문에 번식지로 이동하지 못한다는 연구가 인상적이었다.',['탐구','감정'],['자연'],['자연','사회'],category='world'),
C('w19','회사 규정이 같은 실수를 한 정규직과 계약직에게 다르게 적용되는 이유가 납득되지 않았다.',['사유','감정'],['사회'],['사회'],category='world'),
C('w20','폐허가 된 지하역에서 비밀 출구를 찾으며 사라진 동료를 추적하는 장면이 흥미로웠다.',['감정'],['모험','어둠'],['모험','어둠','상상'],category='world'),
C('w21','꿈에서 본 장소가 다음 날 현실에 그대로 생겨나는 설정이 신기했다.',['감정'],['상상'],['상상'],category='world'),
C('w22','습지 개발 허가를 둘러싸고 주민 생계와 철새 보호가 충돌하는 부분을 더 생각해 보고 싶었다.',['사유','탐구'],['자연','사회'],['자연','사회'],category='world'),

# Mixed metadata/surface + genuine content: substantive signal must survive.
C('m01','317쪽에 표시해 둔 장면을 다시 읽었는데 선의를 이유로 상대의 선택을 무시한 행동이 정당한지 고민됐다.',['사유'],category='mixed'),
C('m02','표지의 나무 그림보다 산불 이후 숲 생태가 회복되는 속도를 설명한 자료가 더 궁금했다.',['탐구','감각'],['자연'],['자연'],category='mixed'),
C('m03','목차에서 복지 장을 다시 찾아 읽고 지원금 기준에서 빠지는 가족이 생기는 이유를 생각했다.',['사유','탐구'],['사회'],['사회'],category='mixed'),
C('m04','지도 삽화는 단순했지만 사막의 여러 국경을 버스로 건너는 여정 자체가 오래 기억에 남았다.',['감정','감각'],['모험'],['모험'],category='mixed'),
C('m05','오디오북 재생 위치를 되돌려 들었는데 마지막 작별 인사가 너무 쓸쓸했다.',['감정'],category='mixed'),
C('m06','반납 전에 기후 부분을 다시 읽고 해수면 자료의 출처를 원문에서 확인하고 싶었다.',['탐구'],['자연'],['자연'],category='mixed'),
C('m07','삽화의 검은 배경보다 감시 카메라가 주민의 이동을 기록하는 제도가 더 섬뜩했다.',['감정','사유'],['어둠','사회'],['어둠','사회'],category='mixed'),
C('m08','책갈피를 꽂은 장에서 가상 도시의 선거권이 계급에 따라 달라지는 설정을 다시 생각했다.',['사유'],['상상','사회'],['상상','사회','어둠'],category='mixed'),
]
assert len(CASES)==72

clf=HybridE5ClassifierV31(MODEL); rows=[]
for c in CASES:
    a=clf.analyze(c['text']); n=project_growth_nutrition(c['text'],a)
    rows.append({**c,'response':list(n.response),'world':list(n.world),'analysis':a})

s=dict(neutral=0,neutral_ok=0,response_req=0,response_hit=0,response_pred=0,response_good=0,
       world_req=0,world_hit=0,world_pred=0,world_good=0,world_null=0,world_clean=0,
       mixed=0,mixed_survive=0,exact=0)
watch=[]
for r in rows:
    pr=list(r['response']); pw=list(r['world']); rok=set(r['response_ok']); wr=set(r['world_required']); wa=set(r['world_allowed'])
    if r['category']=='neutral': s['neutral']+=1; s['neutral_ok']+=not pr and not pw
    if r['category']=='mixed': s['mixed']+=1; s['mixed_survive']+=bool(pr or pw)
    if rok: s['response_req']+=1; s['response_hit']+=bool(pr and pr[0] in rok)
    s['response_pred']+=len(pr); s['response_good']+=sum(x in rok for x in pr)
    s['world_req']+=len(wr); s['world_hit']+=len(wr&set(pw)); s['world_pred']+=len(pw); s['world_good']+=sum(x in wa for x in pw)
    if not wr: s['world_null']+=1; s['world_clean']+=not pw
    ro=(not rok and not pr) or (bool(pr) and pr[0] in rok)
    wo=wr.issubset(set(pw)) and set(pw).issubset(wa)
    s['exact']+=ro and wo
    if not(ro and wo): watch.append(r)

pct=lambda a,b:100*a/b if b else 100.0
metrics={
 'neutral_empty':pct(s['neutral_ok'],s['neutral']),
 'mixed_survival':pct(s['mixed_survive'],s['mixed']),
 'response_recall':pct(s['response_hit'],s['response_req']),
 'response_precision':pct(s['response_good'],s['response_pred']),
 'world_required_recall':pct(s['world_hit'],s['world_req']),
 'world_precision':pct(s['world_good'],s['world_pred']),
 'world_null_clean':pct(s['world_clean'],s['world_null']),
 'exact_records':pct(s['exact'],len(rows)),
}
targets={'neutral_empty':96,'mixed_survival':82,'response_recall':74,'response_precision':91,'world_required_recall':84,'world_precision':94,'world_null_clean':97}
passed=all(metrics[k]>=v for k,v in targets.items())
labels={'neutral_empty':'neutral adds no nutrition','mixed_survival':'mixed substantive notes survive','response_recall':'response recall','response_precision':'response precision','world_required_recall':'required world recall','world_precision':'world modifier precision','world_null_clean':'no-world abstention','exact_records':'product-exact records'}
lines=['# BookEater hidden growth fresh blind v7','',
       '- classifier: `e5-hybrid-v3.1.1`',
       '- growth projector: `growth-nutrition-v1.6.1` frozen before these 72 records were authored',
       '- after this first execution, this set becomes diagnostic','',
       '|metric|result|target|','|---|---:|---:|']
for k in metrics:
    t=f">={targets[k]}%" if k in targets else 'diagnostic'
    lines.append(f"|{labels[k]}|{metrics[k]:.1f}%|{t}|")
lines += ['',f"**release-style gate: {'PASS' if passed else 'FAIL'}**",'', '## Watchlist','']
for r in watch:
    lines.append(f"- {r['id']} [{r['category']}] response={r['response']} ok={r['response_ok']} world={r['world']} required={r['world_required']} allowed={r['world_allowed']} :: {r['text']}")
OUT.parent.mkdir(exist_ok=True)
OUT.write_text('\n'.join(lines),encoding='utf-8')
JSON_OUT.write_text(json.dumps({'metrics':metrics,'targets':targets,'passed':passed,'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
print('\n'.join(lines))
if not passed: raise SystemExit(2)
