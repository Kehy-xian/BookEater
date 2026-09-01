from __future__ import annotations
import json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bookeater.nlp.hybrid_classifier_v31 import HybridE5ClassifierV31
from bookeater.game.nutrition import project_growth_nutrition

MODEL=ROOT/'resources/models/multilingual-e5-small-onnx'
OUT=ROOT/'tests/growth_nutrition_blind_v2.md'
JSON_OUT=ROOT/'tests/growth_nutrition_blind_v2.json'

# Fresh holdout authored after growth-nutrition-v1.1 was frozen.
# Do not tune against this set and still call it blind; after first execution it becomes diagnostic.
# Format: id, text, acceptable response traits, acceptable world traits, category.
CASES=[
# Pure logistics / metadata. These should never shape phenotype.
('n01','책에 붙은 청구기호를 사진으로 찍어 두었다.',[],[],'neutral'),
('n02','전자책 진행률이 43퍼센트라서 다음에 그 위치부터 읽으면 된다.',[],[],'neutral'),
('n03','예약 순번이 세 번째라 대출 가능 알림을 기다리고 있다.',[],[],'neutral'),
('n04','초판과 개정판의 ISBN이 달라 어느 판을 읽는지 메모했다.',[],[],'neutral'),
('n05','읽던 곳에 책갈피를 꽂고 침대 옆에 두었다.',[],[],'neutral'),
('n06','도서관 반납함 위치와 운영 시간을 확인했다.',[],[],'neutral'),
('n07','상권은 280쪽이고 하권은 301쪽이라고 적어 두었다.',[],[],'neutral'),
('n08','표지 색이 비슷한 책이 많아 책등의 저자명을 확인했다.',[],[],'neutral'),
('n09','목차 사진만 찍고 오늘은 본문을 읽지 못했다.',[],[],'neutral'),
('n10','읽은 날짜와 시작 페이지를 독서표에 체크했다.',[],[],'neutral'),
('n11','도서관에서 빌린 책의 연장 가능 횟수를 확인했다.',[],[],'neutral'),
('n12','서가 위치를 잘못 찾아 한 층 아래로 내려갔다.',[],[],'neutral'),

# Substantive reflections that happen to mention logistics/page metadata. These SHOULD still feed.
('m01','153쪽에서 아버지가 아무 말 없이 밥그릇을 치우는 장면이 이상하게 서러웠다.',['감정'],[],'metadata-mixed'),
('m02','반납일이 내일이라 급하게 읽었지만 마지막 선택이 정당했는지는 계속 생각하게 된다.',['사유'],[],'metadata-mixed'),
('m03','목차의 ‘공정한 규칙’ 장을 읽고 같은 규칙이 모두에게 정말 공정한지 의문이 들었다.',['사유'],['사회'],'metadata-mixed'),
('m04','책갈피를 꽂아 둔 부분의 문장이 유난히 짧고 리듬이 빨라서 다시 소리 내 읽었다.',['감각'],[],'metadata-mixed'),
('m05','개정판에서는 통계 수치가 바뀌었다고 해서 원자료를 찾아 차이를 확인해 보고 싶다.',['탐구'],[],'metadata-mixed'),
('m06','도서관에서 빌린 책인데도 숲이 계절마다 달라지는 묘사가 좋아 오래 붙잡고 읽었다.',['감각'],['자연'],'metadata-mixed'),
('m07','312쪽의 재개발 장면에서 세입자만 먼저 떠나야 하는 이유가 불공평하게 느껴졌다.',['사유','감정'],['사회'],'metadata-mixed'),
('m08','페이지를 넘길 때마다 같은 복도가 조금씩 달라지는 설정이 마치 꿈속 같아 재미있었다.',['감정'],['상상'],'metadata-mixed'),

# Negation, labels, and figurative traps. World modifiers should abstain unless content is truly about them.
('d01','마법이 나오는 이야기는 아니고, 평범한 가족이 서로 사과하지 못하는 과정이 더 마음에 남았다.',['감정'],[],'decoy'),
('d02','여행 이야기는 거의 없었다. 한 방 안에서 두 사람이 침묵하는 장면이 오히려 긴장됐다.',['감정'],[],'decoy'),
('d03','숲은 단지 카페 이름이고, 실제 내용은 창업 비용을 계산하는 방법에 관한 책이었다.',['탐구'],[],'decoy'),
('d04','프로젝트 이름을 ‘모험’으로 정했다는 대목보다 팀원들이 역할을 나누는 방식이 흥미로웠다.',['감정'],[],'decoy'),
('d05','‘어둠’이라는 전시 제목과 달리 밝은 색을 겹쳐 쓰는 표현 방식이 인상적이었다.',['감각'],[],'decoy'),
('d06','죽음이 아니라 실패를 두려워한다는 문장을 읽고 내가 무엇을 무서워하는지 생각했다.',['사유'],[],'decoy'),
('d07','사회라는 과목명이 적힌 문제집의 설명이 간결해서 공부하기 편했다.',['감각'],[],'decoy'),
('d08','자연이라는 브랜드의 연필을 소개하는 광고 문구가 과장됐는지 비교해 봤다.',['탐구'],[],'decoy'),
('d09','폭풍처럼 몰아친다는 비유보다 쉼표가 반복되는 문장 리듬이 더 좋았다.',['감각'],[],'decoy'),
('d10','탐험대라는 동아리 이름은 거창하지만 실제 활동은 교내 설문 조사였다.',['탐구'],[],'decoy'),

# Reader response only.
('r01','용서한다는 것이 잊는 것과 같은지 쉽게 답하기 어려웠다.',['사유'],[],'response-only'),
('r02','둘이 화해하지 못한 채 헤어지는 장면이 하루 종일 마음에 남았다.',['감정'],[],'response-only'),
('r03','인용된 연구가 실제로 그런 결론을 냈는지 논문 원문을 확인하고 싶었다.',['탐구'],[],'response-only'),
('r04','같은 단어가 세 번 반복되면서 점점 의미가 달라지는 문장이 재미있었다.',['감각'],[],'response-only'),
('r05','선한 의도로 한 거짓말도 정당화될 수 있는지 고민했다.',['사유'],[],'response-only'),
('r06','주인공이 친구의 편지를 끝내 읽지 못하는 장면이 너무 안타까웠다.',['감정'],[],'response-only'),
('r07','도표의 합계가 본문 설명과 맞지 않아 계산을 다시 해 봤다.',['탐구'],[],'response-only'),
('r08','번역이 바뀌자 인물의 말투가 훨씬 차갑게 느껴지는 점이 흥미로웠다.',['감각'],[],'response-only'),
('r09','규칙을 지키는 것과 옳은 일을 하는 것이 항상 같은지 생각하게 됐다.',['사유'],[],'response-only'),
('r10','마지막 장면에서 미안함과 안도감이 동시에 느껴져 복잡했다.',['감정'],[],'response-only'),

# Strong literal world/topic content.
('w01','기억을 다른 사람의 꿈속에 심을 수 있는 도시라는 설정이 기묘하고 재미있었다.',['감정'],['상상'],'world'),
('w02','밤마다 시간이 멈추고 한 사람만 움직일 수 있다는 규칙을 상상하는 재미가 있었다.',['감정'],['상상'],'world'),
('w03','배를 갈아타며 작은 항구들을 지나 북쪽 섬까지 가는 여정을 따라가고 싶었다.',['감정'],['모험'],'world'),
('w04','낯선 산길에서 길을 잃고도 목적지를 찾아 계속 이동하는 과정이 긴장감 있었다.',['감정'],['모험'],'world'),
('w05','갯벌이 사라지자 철새가 쉬어 갈 장소도 줄어드는 과정이 인상적이었다.',['감정'],['자연'],'world'),
('w06','산불 뒤에 어떤 식물이 먼저 돌아오는지 실제 생태 자료를 더 찾아보고 싶었다.',['탐구'],['자연'],'world'),
('w07','학교 규칙이 모든 학생에게 같은 결과를 만드는 것은 아니라는 점이 마음에 걸렸다.',['사유'],['사회'],'world'),
('w08','돌봄 노동을 누가 맡는지에 따라 가족의 시간과 소득이 달라지는 구조가 보였다.',['사유'],['사회'],'world'),
('w09','사라진 사람의 이름을 아무도 기억하지 못하게 되는 장면이 조용해서 더 무서웠다.',['감정'],['어둠'],'world'),
('w10','전쟁이 끝난 뒤 폐허가 된 마을에서 아이들이 빈집을 지나는 장면이 오래 남았다.',['감정'],['어둠'],'world'),
('w11','가상 세계에서는 시민의 감정 점수에 따라 거주 구역이 바뀐다는 설정이 섬뜩했다.',['감정'],['상상','사회'],'world'),
('w12','빙하가 녹아 마을을 옮겨야 하는 사람들의 이야기를 보며 기후 변화가 삶을 어떻게 바꾸는지 생각했다.',['사유'],['자연','사회'],'world'),
('w13','지도에 없는 도시를 찾으러 기차와 배를 번갈아 타는 환상적인 여정이 매력적이었다.',['감정'],['모험','상상'],'world'),
('w14','감시를 피해 국경을 넘는 인물들이 이동할 때마다 들킬까 봐 불안했다.',['감정'],['어둠','모험'],'world'),
('w15','숲을 없애고 지은 공장 때문에 주민과 야생동물이 함께 피해를 입는 구조가 답답했다.',['감정'],['자연','사회'],'world'),

# Multi-signal but still ordinary prose.
('x01','바다 생물의 이동 경로를 지도와 연구 자료로 비교해 실제로 맞는지 확인해 보고 싶었다.',['탐구'],['자연'],'mixed'),
('x02','낯선 도시를 걷는 장면의 비 냄새와 젖은 돌길 묘사가 생생해서 여행 장면이 더 좋았다.',['감각'],['모험'],'mixed'),
('x03','모두가 같은 표정을 해야 하는 가상 도시의 규칙이 우습지만 동시에 섬뜩했다.',['감정'],['상상','사회','어둠'],'mixed'),
('x04','계절이 바뀔 때마다 숲의 색을 다르게 묘사한 문장이 아름다워 소리 내 읽었다.',['감각'],['자연'],'mixed'),
('x05','임대 계약서를 읽지 못한 인물이 불리한 조건을 떠안는 장면을 보고 제도가 누구에게 어려운지 생각했다.',['사유'],['사회'],'mixed'),
]
assert len(CASES)==60

clf=HybridE5ClassifierV31(MODEL)
rows=[]
for cid,text,er,ew,cat in CASES:
    a=clf.analyze(text)
    n=project_growth_nutrition(text,a)
    pr=list(n.response);pw=list(n.world)
    rows.append({'id':cid,'text':text,'category':cat,'expected_response':er,'expected_world':ew,'response':pr,'world':pw,'analysis':a})

s={'neutral':0,'neutral_ok':0,'response_present':0,'response_hit':0,'world_present':0,'world_hit':0,
   'world_null':0,'world_null_ok':0,'metadata_mixed':0,'metadata_mixed_nonempty':0,
   'gold':0,'pred':0,'hit':0,'exact':0}
for r in rows:
    er=set(r['expected_response']);ew=set(r['expected_world']);pr=r['response'];pw=r['world']
    if r['category']=='neutral':
        s['neutral']+=1;s['neutral_ok']+=not pr and not pw
    if r['category']=='metadata-mixed':
        s['metadata_mixed']+=1;s['metadata_mixed_nonempty']+=bool(pr or pw)
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
 'metadata_mixed_nonempty':pct(s['metadata_mixed_nonempty'],s['metadata_mixed']),
 'response_hit':pct(s['response_hit'],s['response_present']),
 'world_hit':pct(s['world_hit'],s['world_present']),
 'world_null':pct(s['world_null_ok'],s['world_null']),
 'precision':pct(s['hit'],s['pred']),
 'recall':pct(s['hit'],s['gold']),
 'exact':pct(s['exact'],len(rows)),
}
targets={
 'neutral_empty':95,
 'metadata_mixed_nonempty':75,
 'response_hit':78,
 'world_hit':82,
 'world_null':92,
 'precision':86,
 'recall':68,
}
passed=all(metrics[k]>=v for k,v in targets.items())

lines=['# BookEater hidden growth nutrition fresh blind v2','',
       '- classifier: `e5-hybrid-v3.1.1`','- growth projector: `growth-nutrition-v1.1` frozen before these 60 records were authored',
       '- special watch: metadata over-blocking, negation/title decoys, mixed world signals',
       '- after this first execution, this set is diagnostic rather than blind','',
       '|metric|result|target|','|---|---:|---:|']
labels={
 'neutral_empty':'neutral adds no nutrition',
 'metadata_mixed_nonempty':'substantive notes survive metadata words',
 'response_hit':'response signal recall',
 'world_hit':'world signal recall',
 'world_null':'world false-modifier abstention',
 'precision':'nutrition label precision',
 'recall':'nutrition label recall',
 'exact':'exact records',
}
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
