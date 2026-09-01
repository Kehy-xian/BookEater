from __future__ import annotations
import json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bookeater.nlp.hybrid_classifier_v31 import HybridE5ClassifierV31
from bookeater.game.nutrition import project_growth_nutrition

MODEL=ROOT/'resources/models/multilingual-e5-small-onnx'
OUT=ROOT/'tests/growth_nutrition_blind_v6.md'; JSON_OUT=ROOT/'tests/growth_nutrition_blind_v6.json'

def C(cid,text,response_ok,world_required=(),world_allowed=None,category=''):
    wr=list(world_required); wa=list(world_allowed if world_allowed is not None else wr)
    return dict(id=cid,text=text,response_ok=list(response_ok),world_required=wr,world_allowed=wa,category=category)

# Fresh holdout authored only after growth-nutrition-v1.5 was frozen.
# Once this file is executed for the first time, it becomes diagnostic rather than blind.
CASES=[
# Administrative / device / library logistics. No hidden growth should be added.
C('n01','예약한 책이 준비됐다는 문자만 확인하고 찾으러 갈 시간을 메모했다.',[],category='neutral'),
C('n02','전자책 앱에서 글자 크기를 두 단계 키우고 야간 모드를 켰다.',[],category='neutral'),
C('n03','오디오북이 2시간 14분에서 멈춰 있어서 재생 지점을 적어 두었다.',[],category='neutral'),
C('n04','분실할까 봐 책 안쪽에 이름표를 붙이고 가방에 넣었다.',[],category='neutral'),
C('n05','같은 제목의 책이 두 권 떠서 저자와 출판사를 보고 원하는 판을 골랐다.',[],category='neutral'),
C('n06','읽을 책 목록에서 완료 표시를 지우고 다시 읽는 중으로 바꿨다.',[],category='neutral'),
C('n07','도서관 홈페이지에서 상호대차 신청이 접수됐는지만 확인했다.',[],category='neutral'),
C('n08','책이 너무 두꺼워 오늘 읽은 범위를 41~63쪽으로 적었다.',[],category='neutral'),
C('n09','이어폰 연결이 끊겨 오디오북을 잠시 멈추고 블루투스를 다시 연결했다.',[],category='neutral'),
C('n10','개정판과 초판의 ISBN이 다른지 서지정보 화면에서 대조했다.',[],category='neutral'),
C('n11','책을 책상 왼쪽 칸에 꽂아 두었다는 위치만 메모했다.',[],category='neutral'),
C('n12','읽기 알림 시간을 밤 9시에서 10시로 변경했다.',[],category='neutral'),

# Reader response/body signals without required world modifier.
C('r01','용서하지 않기로 한 선택이 꼭 나쁜 것인지 쉽게 답을 못 내리겠다.',['사유'],category='response'),
C('r02','아이에게 끝내 진실을 말하지 못하는 장면에서 괜히 마음이 먹먹해졌다.',['감정'],category='response'),
C('r03','본문의 통계가 어떤 조사에서 나온 값인지 출처 원문을 확인해 보고 싶다.',['탐구'],category='response'),
C('r04','같은 문장이 세 번 반복되면서 점점 짧아지는 리듬이 묘하게 긴장감을 만들었다.',['감각'],category='response'),
C('r05','좋은 결과가 나왔다고 과정까지 정당했다고 말할 수 있는지 고민됐다.',['사유'],category='response'),
C('r06','둘이 아무 말 없이 식탁을 치우는 마지막 장면이 유난히 쓸쓸했다.',['감정'],category='response'),
C('r07','주석에서 인용한 연구가 실제로 같은 결론인지 논문 초록과 비교해 봤다.',['탐구'],category='response'),
C('r08','번역문에서 쉼표 위치 하나로 호흡이 달라지는 게 재미있어 소리 내 읽었다.',['감각','탐구'],category='response'),
C('r09','주인공을 비겁하다고 단정하기 전에 당시 선택지가 정말 있었는지 생각해 봤다.',['사유'],category='response'),
C('r10','오랫동안 기다렸던 편지가 결국 도착하지 않는 장면이 너무 허전했다.',['감정'],category='response'),
C('r11','그래프 축 범위를 바꾸면 인상이 달라지는 이유를 직접 수치로 다시 계산했다.',['탐구'],category='response'),
C('r12','거친 자음이 연달아 나오는 문장이 장면의 답답함과 잘 어울렸다.',['감각'],category='response'),

# Labels, names, dictionary/language, visual surface and metaphor traps. World must abstain.
C('d01','“항해”라는 이름의 카페 메뉴판에서 글자 크기와 배치를 비교했다.',['감각','탐구'],category='decoy'),
C('d02','‘사회적 거리’라는 표현의 사전 뜻과 실제 예문 차이를 찾아봤다.',['탐구','감각'],category='decoy'),
C('d03','꽃 모양 책갈피가 표지 색과 잘 맞아서 사진을 찍어 두었다.',['감각','감정'],category='decoy'),
C('d04','문장이 파도처럼 밀려온다는 비유가 리듬을 잘 보여준다고 느꼈다.',['감각'],category='decoy'),
C('d05','“전쟁의 신”은 보드게임 카드 이름이고 이 문단은 점수 규칙 설명이었다.',['탐구'],category='decoy'),
C('d06','자연스럽게 말하는 법을 설명한 발음 연습 부분을 여러 번 따라 읽었다.',['감각','탐구'],category='decoy'),
C('d07','검은 숲이라는 향수 제품명이 왜 붙었는지 광고 문구만 확인했다.',['탐구','감각'],category='decoy'),
C('d08','여행은 하지 않는 인물이 지도라는 단어를 농담처럼 반복해서 번역 차이만 살폈다.',['감각','탐구'],category='decoy'),
C('d09','‘감시’라는 과목 활동명 아래 체크리스트 작성 방법만 설명돼 있었다.',['탐구'],category='decoy'),
C('d10','무대 배경의 바다 그림과 조명 색이 예뻐서 시각적인 부분만 기억났다.',['감각','감정'],category='decoy'),
C('d11','문제를 숲에서 길 찾기처럼 풀라는 표현이 이해를 돕는 비유였다.',['탐구','감각'],category='decoy'),
C('d12','‘미래 도시’라는 전시 섹션 제목의 글꼴이 다른 섹션보다 읽기 편했다.',['감각'],category='decoy'),

# Strong world/topic signals. Structural world traits are required where clear.
C('w01','눈을 감으면 아직 태어나지 않은 사람의 꿈을 볼 수 있다는 설정이 신선했다.',['감정','감각'],['상상'],['상상'],category='world'),
C('w02','매일 자정이 되면 마을의 하루가 처음부터 다시 시작되고 한 사람만 기억을 유지한다.',['사유','감정'],['상상'],['상상','어둠'],category='world'),
C('w03','사막을 건너 여러 오아시스를 거쳐 오래된 도시를 찾아가는 여정이 흥미로웠다.',['감정'],['모험'],['모험','자연'],category='world'),
C('w04','폭풍 때문에 배가 우회 항로를 택하고 낯선 항구에 머무는 과정이 긴장됐다.',['감정'],['모험'],['모험','자연','어둠'],category='world'),
C('w05','해수 온도가 오르면서 산호 군락이 줄어드는 원인을 다른 연구에서도 찾아보고 싶었다.',['탐구'],['자연'],['자연'],category='world'),
C('w06','철새가 예전보다 북쪽에서 겨울을 나는 이유가 기온 변화와 연결되는지 궁금했다.',['탐구'],['자연'],['자연'],category='world'),
C('w07','같은 일을 해도 고용 형태에 따라 병가를 쓸 수 없는 구조가 공정한지 생각했다.',['사유'],['사회'],['사회'],category='world'),
C('w08','재개발 뒤 원래 살던 세입자들이 다시 들어오지 못하는 과정이 개인 선택의 문제로만 보이지 않았다.',['사유','감정'],['사회'],['사회','어둠'],category='world'),
C('w09','죽은 사람의 메시지가 매년 같은 날 휴대전화에 도착하는 장면이 섬뜩했다.',['감정'],['어둠'],['어둠','상상'],category='world'),
C('w10','전쟁이 끝났는데도 실종된 가족을 기다리는 인물의 시간이 멈춘 것 같아 먹먹했다.',['감정'],['어둠'],['어둠','사회'],category='world'),
C('w11','가상 도시에서 시민의 신용 점수가 낮으면 대중교통도 탈 수 없는 제도가 무서웠다.',['사유','감정'],['상상','사회'],['상상','사회','어둠'],category='world'),
C('w12','기후 재난으로 집을 잃은 주민에게 지원금 기준이 어떻게 적용되는지 궁금했다.',['탐구','사유'],['자연','사회'],['자연','사회','어둠'],category='world'),
C('w13','다른 행성의 바다를 조사하려고 잠수정을 타고 미지의 해역으로 떠나는 장면이 설렜다.',['감정'],['상상','모험'],['상상','모험','자연'],category='world'),
C('w14','기억을 사고팔 수 있는 나라에서 부자만 과거를 지울 수 있다는 제도가 불공평하게 느껴졌다.',['사유','감정'],['상상','사회'],['상상','사회','어둠'],category='world'),
C('w15','빙하가 녹아 강의 유량이 달라지고 농촌 마을의 물 사용까지 영향을 받는 과정이 인상적이었다.',['탐구','사유'],['자연'],['자연','사회'],category='world'),
C('w16','감옥이 아닌 평범한 아파트인데 모든 방의 소리가 기록되는 설정이 소름 끼쳤다.',['감정','사유'],['어둠'],['어둠','사회'],category='world'),
C('w17','국경을 넘기 위해 산길을 밤새 걷고 여러 검문소를 피해가는 여정이 숨 막혔다.',['감정'],['모험'],['모험','어둠','사회'],category='world'),
C('w18','멸종 위기 동물이 도로 때문에 서식지를 오가지 못한다는 설명을 더 확인해 보고 싶었다.',['탐구'],['자연'],['자연','사회'],category='world'),
C('w19','학교 규칙이 같은 행동을 한 학생들에게 다르게 적용되는 이유가 납득되지 않았다.',['사유','감정'],['사회'],['사회'],category='world'),
C('w20','주인공이 사라진 친구를 찾다가 폐허가 된 지하 도시의 비밀 통로를 발견하는 장면이 흥미로웠다.',['감정'],['어둠','모험'],['어둠','모험','상상'],category='world'),

# Metadata/surface language mixed with substantive content: must not be over-blocked.
C('m01','전자책에서 203쪽을 다시 펼쳤는데 친구에게 책임을 떠넘기는 선택이 정말 정당했는지 계속 생각났다.',['사유'],category='mixed'),
C('m02','표지의 고래 그림도 예뻤지만 해수 온도 때문에 먹이터가 바뀐다는 설명이 더 궁금했다.',['탐구','감각'],['자연'],['자연'],category='mixed'),
C('m03','목차에서 노동 파트를 찾아 읽고 계약직에게만 휴가가 없는 기준이 공정한지 고민했다.',['사유'],['사회'],['사회'],category='mixed'),
C('m04','지도 삽화보다 여러 국경 도시를 기차로 옮겨 다니는 주인공의 여정이 더 기억에 남았다.',['감정','감각'],['모험'],['모험'],category='mixed'),
C('m05','오디오북 3시간쯤에서 들은 마지막 대화가 너무 서늘해서 그 장면을 다시 찾아 들었다.',['감정','감각'],category='mixed'),
C('m06','반납하기 전에 기후 장을 다시 읽었는데 홍수 빈도가 높아진 자료의 출처를 확인하고 싶었다.',['탐구'],['자연'],['자연'],category='mixed'),
C('m07','삽화의 어두운 색보다 감시 카메라 때문에 주민들이 서로를 의심하는 설정이 더 불편했다.',['감정','사유'],['어둠','사회'],['어둠','사회'],category='mixed'),
C('m08','책갈피를 꽂아 둔 부분에서 가상 세계의 투표 제도가 계급마다 다른 이유를 다시 생각했다.',['사유'],['상상','사회'],['상상','사회','어둠'],category='mixed'),
]
assert len(CASES)==64

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
targets={
 'neutral_empty':95,
 'mixed_survival':80,
 'response_recall':72,
 'response_precision':90,
 'world_required_recall':84,
 'world_precision':93,
 'world_null_clean':96,
}
passed=all(metrics[k]>=v for k,v in targets.items())
labels={
 'neutral_empty':'neutral adds no nutrition',
 'mixed_survival':'mixed substantive notes survive',
 'response_recall':'response recall',
 'response_precision':'response precision',
 'world_required_recall':'required world recall',
 'world_precision':'world modifier precision',
 'world_null_clean':'no-world abstention',
 'exact_records':'product-exact records',
}
lines=['# BookEater hidden growth fresh blind v6','',
       '- classifier: `e5-hybrid-v3.1.1`',
       '- growth projector: `growth-nutrition-v1.5` frozen before these 64 records were authored',
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
