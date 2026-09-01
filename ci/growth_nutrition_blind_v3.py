from __future__ import annotations
import json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bookeater.nlp.hybrid_classifier_v31 import HybridE5ClassifierV31
from bookeater.game.nutrition import project_growth_nutrition

MODEL=ROOT/'resources/models/multilingual-e5-small-onnx'
OUT=ROOT/'tests/growth_nutrition_blind_v3.md'
JSON_OUT=ROOT/'tests/growth_nutrition_blind_v3.json'

# Fresh holdout authored only after growth-nutrition-v1.2 was frozen.
CASES=[
# Pure logistics / neutral notes.
('n01','대출 연장을 한 번 더 할 수 있는지 앱에서 확인했다.',[],[],'neutral'),
('n02','4장은 88쪽부터 시작해서 다음에는 거기서 읽기로 했다.',[],[],'neutral'),
('n03','전자책 글자 크기를 두 단계 키우고 야간 모드로 바꿨다.',[],[],'neutral'),
('n04','책 무게가 생각보다 무거워 작은 가방 대신 큰 가방에 넣었다.',[],[],'neutral'),
('n05','읽던 권을 반납하고 같은 시리즈 다음 권을 예약했다.',[],[],'neutral'),
('n06','표지 비닐이 벗겨져 테이프로 임시로 붙여 두었다.',[],[],'neutral'),
('n07','저자 이름 철자가 맞는지 책등과 검색 결과를 대조했다.',[],[],'neutral'),
('n08','오늘은 독서 시간만 25분으로 기록하고 감상은 쓰지 않았다.',[],[],'neutral'),

# Meaningful notes containing metadata/logistics words.
('m01','88쪽에서 언니가 동생의 편지를 몰래 버리는 장면이 너무 속상했다.',['감정'],[],'metadata-mixed'),
('m02','반납하기 전에 다시 읽은 결말에서 주인공의 거짓말이 정말 정당했는지 고민했다.',['사유'],[],'metadata-mixed'),
('m03','목차의 노동 장을 읽고 같은 일을 해도 계약에 따라 대우가 달라지는 이유를 생각했다.',['사유'],['사회'],'metadata-mixed'),
('m04','책갈피를 꽂은 문단은 같은 소리가 반복돼 리듬이 유난히 또렷했다.',['감각'],[],'metadata-mixed'),
('m05','개정판에서 인용 통계가 달라져 원자료의 조사 연도를 직접 확인해 보고 싶었다.',['탐구'],[],'metadata-mixed'),
('m06','도서관에서 빌려 온 책인데 해안 습지의 새들이 계절마다 바뀌는 부분이 흥미로웠다.',['감정','탐구'],['자연'],'metadata-mixed'),
('m07','201쪽 재판 장면에서 돈이 없는 사람에게 같은 법 절차가 더 어렵게 느껴지는 점이 마음에 걸렸다.',['사유'],['사회'],'metadata-mixed'),
('m08','페이지 번호를 확인하려다 다시 읽은 문장이 빛과 그림자를 대비시키는 방식이 아름다웠다.',['감각'],[],'metadata-mixed'),

# Decoys, negations, labels, and Korean substring traps.
('d01','건강 관리 방법을 설명한 책이라 운동 시간을 표로 정리해 봤다.',['탐구'],[],'decoy'),
('d02','설명이 조금 우습지만 예시가 명확해서 이해하기 쉬웠다.',['감각'],[],'decoy'),
('d03','정리 방법이 복잡한지 단계별 절차를 다시 비교했다.',['탐구'],[],'decoy'),
('d04','죽순 손질법을 설명하는 부분에서 삶는 시간을 메모했다.',['탐구'],[],'decoy'),
('d05','‘항해’라는 이름의 카페가 등장하지만 이야기는 두 친구의 오해와 화해가 중심이었다.',['감정'],[],'decoy'),
('d06','숲 이야기는 전혀 아니고, 회사에서 업무를 나누는 방식만 다룬 책이었다.',['탐구'],[],'decoy'),
('d07','공포 소설은 아니었다. 오히려 평범한 일상에서 생기는 작은 질투가 더 현실적이었다.',['감정'],[],'decoy'),
('d08','전시 프로젝트 제목이 ‘미래 도시’였지만 실제 글은 포스터 인쇄 방식에 대한 설명이었다.',['탐구'],[],'decoy'),

# Response-only notes.
('r01','누군가를 돕기 위해 약속을 어기는 선택도 옳을 수 있는지 생각했다.',['사유'],[],'response-only'),
('r02','친구가 끝까지 기다려 주는 장면에서 갑자기 울컥했다.',['감정'],[],'response-only'),
('r03','책에 인용된 실험 결과가 다른 연구에서도 반복되는지 찾아보고 싶었다.',['탐구'],[],'response-only'),
('r04','짧은 단어가 끊어지듯 이어지는 문체가 긴장감을 만들었다.',['감각'],[],'response-only'),
('r05','미안하다는 말을 하지 않는 것이 배려인지 회피인지 판단하기 어려웠다.',['사유'],[],'response-only'),
('r06','마지막에 혼자 남은 아이가 아무렇지 않은 척하는 모습이 마음 아팠다.',['감정'],[],'response-only'),
('r07','저자가 말한 비율을 표의 숫자로 다시 계산해 보니 맞지 않았다.',['탐구'],[],'response-only'),
('r08','같은 문장을 번역본 두 권에서 읽으니 말투의 온도가 다르게 느껴졌다.',['감각'],[],'response-only'),

# Strong world/topic notes.
('w01','사람의 기억을 책장에 꽂아 두었다가 다른 사람이 꺼내 읽을 수 있다는 설정이 기묘했다.',['감정'],['상상'],'world'),
('w02','하루가 끝날 때마다 도시의 시간이 처음으로 되감긴다는 규칙을 상상하는 재미가 있었다.',['감정'],['상상'],'world'),
('w03','낡은 배를 타고 섬들을 돌며 사라진 등대를 찾는 여정이 흥미로웠다.',['감정'],['모험'],'world'),
('w04','낯선 국경 마을을 지나 목적지까지 걷는 과정이 긴장되면서도 설렜다.',['감정'],['모험'],'world'),
('w05','산불 뒤 숲에 곤충과 작은 식물이 어떤 순서로 돌아오는지 더 알아보고 싶었다.',['탐구'],['자연'],'world'),
('w06','해수 온도가 오르면서 산호가 사라지는 과정을 보니 기후 변화가 실감났다.',['감정'],['자연'],'world'),
('w07','정규직과 계약직이 같은 일을 해도 휴가 기준이 다른 제도가 왜 유지되는지 궁금했다.',['사유','탐구'],['사회'],'world'),
('w08','재개발 뒤 임대료가 올라 오래 살던 주민이 떠나는 과정을 보며 구조의 힘을 생각했다.',['사유'],['사회'],'world'),
('w09','아무도 없는 집에서 전화벨만 계속 울리는 장면이 설명보다 더 무서웠다.',['감정'],['어둠'],'world'),
('w10','감시를 피해 이름을 바꿔 살아가는 인물이 언제 들킬지 몰라 불안했다.',['감정'],['어둠'],'world'),
('w11','가상 도시에서 투표권을 점수로 사고팔 수 있다는 설정이 섬뜩했다.',['감정'],['상상','사회'],'world'),
('w12','홍수 때문에 마을을 옮기는 가족을 보며 기후와 주거 정책이 한 사람의 삶에 함께 영향을 준다는 생각이 들었다.',['사유'],['자연','사회'],'world'),

# Decorative/linguistic uses that should not become world modifiers.
('v01','표지의 꽃무늬와 금색 글자가 잘 어울려서 디자인이 예뻤다.',['감각'],[],'visual-decoy'),
('v02','삽화 속 바다색 배경과 주황색 글씨의 대비가 인상적이었다.',['감각'],[],'visual-decoy'),
('v03','교육용 카드라는 제품 설명보다 그림 배치가 보기 편했다.',['감각'],[],'visual-decoy'),
('v04','전쟁 같은 회의라는 과장된 비유가 문장의 유머를 살렸다.',['감각'],[],'visual-decoy'),
]
assert len(CASES)==48

clf=HybridE5ClassifierV31(MODEL)
rows=[]
for cid,text,er,ew,cat in CASES:
    a=clf.analyze(text)
    n=project_growth_nutrition(text,a)
    pr=list(n.response);pw=list(n.world)
    rows.append({'id':cid,'text':text,'category':cat,'expected_response':er,'expected_world':ew,'response':pr,'world':pw,'analysis':a})

s={'neutral':0,'neutral_ok':0,'metadata_mixed':0,'metadata_nonempty':0,'response_present':0,'response_hit':0,
   'world_present':0,'world_hit':0,'world_null':0,'world_null_ok':0,'gold':0,'pred':0,'hit':0,'exact':0}
for r in rows:
    er=set(r['expected_response']);ew=set(r['expected_world']);pr=r['response'];pw=r['world']
    if r['category']=='neutral':
        s['neutral']+=1;s['neutral_ok']+=not pr and not pw
    if r['category']=='metadata-mixed':
        s['metadata_mixed']+=1;s['metadata_nonempty']+=bool(pr or pw)
    if er:
        s['response_present']+=1;s['response_hit']+=bool(set(pr)&er)
    if ew:
        s['world_present']+=1;s['world_hit']+=bool(set(pw)&ew)
    else:
        s['world_null']+=1;s['world_null_ok']+=not pw
    g=set(('r',x) for x in er)|set(('w',x) for x in ew);p=set(('r',x) for x in pr)|set(('w',x) for x in pw)
    s['gold']+=len(g);s['pred']+=len(p);s['hit']+=len(g&p);s['exact']+=g==p

pct=lambda a,b:100*a/b if b else 0.0
metrics={
 'neutral_empty':pct(s['neutral_ok'],s['neutral']),
 'metadata_mixed_nonempty':pct(s['metadata_nonempty'],s['metadata_mixed']),
 'response_hit':pct(s['response_hit'],s['response_present']),
 'world_hit':pct(s['world_hit'],s['world_present']),
 'world_null':pct(s['world_null_ok'],s['world_null']),
 'precision':pct(s['hit'],s['pred']),
 'recall':pct(s['hit'],s['gold']),
 'exact':pct(s['exact'],len(rows)),
}
targets={'neutral_empty':95,'metadata_mixed_nonempty':75,'response_hit':75,'world_hit':80,'world_null':92,'precision':86,'recall':68}
passed=all(metrics[k]>=v for k,v in targets.items())
labels={
 'neutral_empty':'neutral adds no nutrition','metadata_mixed_nonempty':'substantive notes survive metadata words',
 'response_hit':'response signal recall','world_hit':'world signal recall','world_null':'world false-modifier abstention',
 'precision':'nutrition label precision','recall':'nutrition label recall','exact':'exact records'}
lines=['# BookEater hidden growth nutrition fresh blind v3','',
       '- classifier: `e5-hybrid-v3.1.1`','- growth projector: `growth-nutrition-v1.2` frozen before these 48 records were authored',
       '- special watch: Korean substring traps, metadata+reflection coexistence, label/negation decoys, decorative nature/social words',
       '- after this first execution, this set is diagnostic rather than blind','',
       '|metric|result|target|','|---|---:|---:|']
for k in metrics:
    t=f">={targets[k]}%" if k in targets else 'diagnostic'
    lines.append(f"|{labels[k]}|{metrics[k]:.1f}%|{t}|")
lines += ['',f"**release-style gate: {'PASS' if passed else 'FAIL'}**",'', '## Unexpected-error watchlist','']
for r in rows:
    g=set(('r',x) for x in r['expected_response'])|set(('w',x) for x in r['expected_world']);p=set(('r',x) for x in r['response'])|set(('w',x) for x in r['world'])
    if g!=p:
        miss=sorted(f'{a}:{b}' for a,b in g-p);extra=sorted(f'{a}:{b}' for a,b in p-g)
        lines.append(f"- {r['id']} [{r['category']}] missing={miss or '-'} extra={extra or '-'} :: {r['text']}")
OUT.parent.mkdir(exist_ok=True)
OUT.write_text('\n'.join(lines),encoding='utf-8')
JSON_OUT.write_text(json.dumps({'metrics':metrics,'targets':targets,'passed':passed,'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
print('\n'.join(lines))
if not passed: raise SystemExit(2)
