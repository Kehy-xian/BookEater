from __future__ import annotations
import json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bookeater.nlp.hybrid_classifier_v31 import HybridE5ClassifierV31
from bookeater.game.nutrition import project_growth_nutrition

MODEL=ROOT/'resources/models/multilingual-e5-small-onnx'
OUT=ROOT/'tests/growth_nutrition_blind_v5.md'; JSON_OUT=ROOT/'tests/growth_nutrition_blind_v5.json'

def C(cid,text,response_ok,world_required=(),world_allowed=None,category=''):
    wr=list(world_required);wa=list(world_allowed if world_allowed is not None else wr)
    return dict(id=cid,text=text,response_ok=list(response_ok),world_required=wr,world_allowed=wa,category=category)

# Fresh holdout authored only after growth-nutrition-v1.4 was frozen.
CASES=[
# Administrative notes should never define the creature.
C('n01','도착 예정 알림을 보고 예약 도서 수령일을 달력에 적었다.',[],category='neutral'),
C('n02','오디오북 재생 위치가 초기화돼 어제 듣던 시간을 다시 찾았다.',[],category='neutral'),
C('n03','반납 기한을 일주일 연장하고 알림을 켰다.',[],category='neutral'),
C('n04','읽은 분량을 35쪽으로 기록하고 책을 서랍에 넣었다.',[],category='neutral'),
C('n05','개정 3판인지 확인하려고 판권면의 발행일을 봤다.',[],category='neutral'),
C('n06','전자책 글꼴을 바꾸고 줄 간격을 한 단계 넓혔다.',[],category='neutral'),
C('n07','시리즈 순서를 헷갈려 도서관 검색에서 권수를 확인했다.',[],category='neutral'),
C('n08','읽던 책을 학교 사물함에 두고 집에는 다른 책을 가져왔다.',[],category='neutral'),
C('n09','책갈피 대신 메모지를 94쪽에 끼워 두었다.',[],category='neutral'),
C('n10','대출 상태가 처리 중이라 앱을 새로고침했다.',[],category='neutral'),

# Reader response. Multiple reasonable readings are allowed where appropriate.
C('r01','친구를 보호하려고 사실을 숨긴 행동이 정말 배려였는지 생각하게 됐다.',['사유'],category='response'),
C('r02','아버지가 빈 의자만 바라보는 장면이 이상하게 짠했다.',['감정'],category='response'),
C('r03','인용된 설문이 어느 연령대를 조사했는지 원자료를 찾아보고 싶었다.',['탐구'],category='response'),
C('r04','짧은 문장이 연달아 나오니 발걸음이 빨라지는 것처럼 리듬이 느껴졌다.',['감각'],category='response'),
C('r05','둘 중 누구의 선택이 더 책임 있는지 쉽게 결론 내리기 어려웠다.',['사유'],category='response'),
C('r06','헤어진 뒤에도 매일 편지를 쓰는 인물의 마음이 이해돼서 먹먹했다.',['감정'],category='response'),
C('r07','저자의 설명과 표의 값이 같은 결론을 가리키는지 계산해 비교했다.',['탐구'],category='response'),
C('r08','번역본마다 농담의 말투가 달라 어느 쪽이 더 자연스러운지 소리 내 읽어봤다.',['감각','탐구'],category='response'),
C('r09','마지막 선택을 실패라고 부르는 기준이 무엇인지 의문이 남았다.',['사유'],category='response'),
C('r10','아이가 괜찮은 척 웃는 장면이 오히려 더 마음 아팠다.',['감정'],category='response'),

# Instructional / naming / figurative decoys: response may be broad, but world must abstain.
C('d01','“우주 항해”라는 노트 제품의 문구와 실제 종이 질감을 비교했다.',['감각','탐구'],category='decoy'),
C('d02','자연 발음이라는 수업 용어를 따라 읽으며 입 모양을 연습했다.',['감각','탐구'],category='decoy'),
C('d03','죽 한 그릇을 만드는 조리법에서 불 조절 순서를 다시 확인했다.',['탐구'],category='decoy'),
C('d04','숲처럼 촘촘하다는 비유가 문장의 이미지를 선명하게 만들었다.',['감각'],category='decoy'),
C('d05','“감시자”는 게임 캐릭터 직업 이름이고 설명은 점수 계산 방식에 관한 것이었다.',['탐구'],category='decoy'),
C('d06','사회성이라는 단어의 사전적 정의와 예문을 비교해 봤다.',['탐구','감각'],category='decoy'),
C('d07','바다색 표지와 은색 제목 글씨가 잘 어울려 표지가 마음에 들었다.',['감각','감정'],category='decoy'),
C('d08','여행 장면은 전혀 없고 서로 다른 번역 표현만 비교하는 글이었다.',['감각','탐구'],category='decoy'),
C('d09','“마법 도시”라는 전시 이름보다 안내문의 문장 구성이 더 읽기 편했다.',['감각'],category='decoy'),
C('d10','전쟁처럼 치열했다는 표현은 과장 같아서 다른 비유와 비교해 봤다.',['감각','탐구'],category='decoy'),

# Strong world signals; dark tone is allowed secondarily but structural content is required.
C('w01','잠들면 다른 사람의 기억 속 방으로 들어갈 수 있다는 설정이 재미있었다.',['감정'],['상상'],['상상'],category='world'),
C('w02','도시 전체가 매주 월요일 아침으로 되돌아간다는 규칙이 기묘했다.',['감정','사유'],['상상'],['상상','어둠'],category='world'),
C('w03','낡은 배로 여러 항구를 거쳐 미지의 섬을 찾는 여정이 설렜다.',['감정'],['모험'],['모험','상상'],category='world'),
C('w04','눈보라 속 산길을 지나 구조 지점까지 가는 탐험 과정이 긴장됐다.',['감정'],['모험'],['모험','자연','어둠'],category='world'),
C('w05','철새가 머물던 갯벌이 줄면서 먹이와 이동 시기가 바뀌는 원리가 궁금했다.',['탐구'],['자연'],['자연'],category='world'),
C('w06','산호가 수온 변화에 스트레스를 받는 과정을 다른 자료에서도 확인해 보고 싶다.',['탐구'],['자연'],['자연'],category='world'),
C('w07','육아휴직 제도가 계약 형태에 따라 다르게 적용되는 이유를 생각했다.',['사유','탐구'],['사회'],['사회'],category='world'),
C('w08','임대료 상승으로 오래 살던 주민들이 동네를 떠나는 과정이 개인의 문제만은 아닌 것 같다.',['사유'],['사회'],['사회','어둠'],category='world'),
C('w09','사라진 사람의 목소리만 녹음기에 남아 반복되는 장면이 섬뜩했다.',['감정','감각'],['어둠'],['어둠'],category='world'),
C('w10','검문을 피해 숨어 지내는 가족이 언제 발견될지 몰라 불안했다.',['감정'],['어둠'],['어둠'],category='world'),
C('w11','가상 국가에서 시민 등급에 따라 투표 자격이 정해지는 제도가 무서웠다.',['감정','사유'],['상상','사회'],['상상','사회','어둠'],category='world'),
C('w12','가뭄 때문에 이주해야 하는 마을을 보며 기후와 공공 지원이 함께 중요하다는 생각이 들었다.',['사유'],['자연','사회'],['자연','사회','어둠'],category='world'),
C('w13','다른 행성의 얼음 동굴을 탐험하며 신호를 찾는 장면이 신기했다.',['감정'],['상상','모험'],['상상','모험','자연'],category='world'),
C('w14','감시 제도가 있는 미래 도시에서 기억을 숨기는 설정이 자유를 생각하게 했다.',['사유'],['상상','사회'],['상상','사회','어둠'],category='world'),
C('w15','산불로 숲이 사라진 뒤 주민의 식수까지 부족해지는 과정이 답답했다.',['감정','사유'],['자연','사회'],['자연','사회','어둠'],category='world'),
C('w16','전쟁 뒤 폐허가 된 도시에서 가족을 잃은 사람이 혼자 살아가는 장면이 오래 남았다.',['감정'],['어둠'],['어둠','사회'],category='world'),

# Metadata or surface language plus real content.
C('m01','반납 전에 다시 읽은 120쪽에서 친구가 대신 책임을 지는 선택이 옳았는지 고민했다.',['사유'],category='mixed'),
C('m02','삽화의 푸른 색보다 해수 온도 상승이 산호에 미치는 설명이 더 궁금했다.',['탐구','감각'],['자연'],['자연'],category='mixed'),
C('m03','목차의 주거 정책 장을 읽고 지원 기준 밖의 사람들은 어디로 가는지 생각했다.',['사유','탐구'],['사회'],['사회'],category='mixed'),
C('m04','지도 그림도 멋졌지만 주인공이 배를 갈아타며 여러 항구를 지나는 여정이 더 재미있었다.',['감정','감각'],['모험'],['모험'],category='mixed'),
]
assert len(CASES)==50

clf=HybridE5ClassifierV31(MODEL);rows=[]
for c in CASES:
    a=clf.analyze(c['text']);n=project_growth_nutrition(c['text'],a)
    rows.append({**c,'response':list(n.response),'world':list(n.world),'analysis':a})

s=dict(neutral=0,neutral_ok=0,response_req=0,response_hit=0,response_pred=0,response_good=0,world_req=0,world_hit=0,world_pred=0,world_good=0,world_null=0,world_clean=0,mixed=0,mixed_survive=0,exact=0)
watch=[]
for r in rows:
    pr=list(r['response']);pw=list(r['world']);rok=set(r['response_ok']);wr=set(r['world_required']);wa=set(r['world_allowed'])
    if r['category']=='neutral':s['neutral']+=1;s['neutral_ok']+=not pr and not pw
    if r['category']=='mixed':s['mixed']+=1;s['mixed_survive']+=bool(pr or pw)
    if rok:s['response_req']+=1;s['response_hit']+=bool(pr and pr[0] in rok)
    s['response_pred']+=len(pr);s['response_good']+=sum(x in rok for x in pr)
    s['world_req']+=len(wr);s['world_hit']+=len(wr&set(pw));s['world_pred']+=len(pw);s['world_good']+=sum(x in wa for x in pw)
    if not wr:s['world_null']+=1;s['world_clean']+=not pw
    ro=(not rok and not pr) or (bool(pr) and pr[0] in rok);wo=wr.issubset(set(pw)) and set(pw).issubset(wa)
    s['exact']+=ro and wo
    if not(ro and wo):watch.append(r)
pct=lambda a,b:100*a/b if b else 100.0
metrics={'neutral_empty':pct(s['neutral_ok'],s['neutral']),'mixed_survival':pct(s['mixed_survive'],s['mixed']),
         'response_recall':pct(s['response_hit'],s['response_req']),'response_precision':pct(s['response_good'],s['response_pred']),
         'world_required_recall':pct(s['world_hit'],s['world_req']),'world_precision':pct(s['world_good'],s['world_pred']),
         'world_null_clean':pct(s['world_clean'],s['world_null']),'exact_records':pct(s['exact'],len(rows))}
targets={'neutral_empty':95,'mixed_survival':75,'response_recall':70,'response_precision':88,'world_required_recall':82,'world_precision':92,'world_null_clean':95}
passed=all(metrics[k]>=v for k,v in targets.items())
labels={'neutral_empty':'neutral adds no nutrition','mixed_survival':'mixed substantive notes survive','response_recall':'response recall','response_precision':'response precision','world_required_recall':'required world recall','world_precision':'world modifier precision','world_null_clean':'no-world abstention','exact_records':'product-exact records'}
lines=['# BookEater hidden growth fresh blind v5','', '- classifier: `e5-hybrid-v3.1.1`','- growth projector: `growth-nutrition-v1.4` frozen before these 50 records were authored','- after this first execution, this set becomes diagnostic','', '|metric|result|target|','|---|---:|---:|']
for k,v in metrics.items():lines.append(f"|{labels[k]}|{v:.1f}%|{('>='+str(targets[k])+'%') if k in targets else 'diagnostic'}|")
lines+=['',f"**release-style gate: {'PASS' if passed else 'FAIL'}**",'','## Watchlist','']
for r in watch:lines.append(f"- {r['id']} [{r['category']}] response={r['response']} ok={r['response_ok']} world={r['world']} required={r['world_required']} allowed={r['world_allowed']} :: {r['text']}")
OUT.parent.mkdir(exist_ok=True);OUT.write_text('\n'.join(lines),encoding='utf-8');JSON_OUT.write_text(json.dumps({'metrics':metrics,'targets':targets,'passed':passed,'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
print('\n'.join(lines))
if not passed:raise SystemExit(2)
