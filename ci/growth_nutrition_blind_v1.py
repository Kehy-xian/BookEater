from __future__ import annotations
import json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bookeater.nlp.hybrid_classifier_v31 import HybridE5ClassifierV31
from bookeater.game.nutrition import project_growth_nutrition

MODEL=ROOT/'resources/models/multilingual-e5-small-onnx'
OUT=ROOT/'tests/growth_nutrition_blind_v1.md'
JSON_OUT=ROOT/'tests/growth_nutrition_blind_v1.json'

# Authored after the growth projector was frozen. Once executed, these become diagnostic.
# Format: id, text, expected response traits, expected world traits, category.
CASES=[
# Neutral reading logistics: should add no hidden nutrition.
('n01','책 표지가 구겨져서 투명 커버를 씌웠다.',[],[],'neutral'),
('n02','목차에서 다음 장이 127쪽에 시작하는지 확인했다.',[],[],'neutral'),
('n03','제목에 여행이라는 단어가 들어가서 검색 결과의 ISBN이 같은 책인지 대조했다.',[],[],'neutral'),
('n04','밤에 읽기 편하도록 전자책 화면 밝기를 낮췄다.',[],[],'neutral'),
('n05','도서관 좌석을 연장하고 읽던 책은 잠시 사물함에 넣었다.',[],[],'neutral'),
('n06','상상편과 현실편 두 권 중 상상편을 먼저 빌렸다.',[],[],'neutral'),
('n07','자연과 사회라는 분류표시가 붙은 서가를 잘못 찾아가 책 위치를 다시 확인했다.',[],[],'neutral'),
('n08','오늘은 읽은 날짜와 쪽수만 기록하고 감상은 나중에 쓰기로 했다.',[],[],'neutral'),
('n09','책등 스티커가 떨어져 제목과 저자만 다시 적어 붙였다.',[],[],'neutral'),
('n10','하권을 집에 두고 와서 상권의 마지막 페이지 번호만 메모했다.',[],[],'neutral'),

# Strong reader response without one of the five world modifiers.
('r01','주인공이 사과를 받아주지 않은 선택이 너무 현실적으로 느껴져 마음이 무거웠다.',['감정'],[],'response-only'),
('r02','행복한 결말이라는 말이 누구의 기준인지 오래 생각했다.',['사유'],[],'response-only'),
('r03','작가가 제시한 숫자의 출처를 직접 찾아보고 싶었다.',['탐구'],[],'response-only'),
('r04','짧은 문장이 연달아 이어져 숨이 가빠지는 느낌이 인상적이었다.',['감각'],[],'response-only'),
('r05','친구를 위해 침묵한 행동이 배려인지 회피인지 판단하기 어려웠다.',['사유'],[],'response-only'),
('r06','마지막 대화에서 둘의 거리감이 느껴져 오래 씁쓸했다.',['감정'],[],'response-only'),
('r07','번역본마다 같은 농담의 말맛이 달라지는 점이 흥미로웠다.',['감각'],[],'response-only'),
('r08','앞 장의 주장과 뒤 장의 예시가 실제로 맞물리는지 다시 비교해봤다.',['탐구'],[],'response-only'),
('r09','그 선택을 비난하기 전에 내가 같은 처지였다면 어땠을지 생각했다.',['사유'],[],'response-only'),
('r10','마지막 한 문장이 유난히 짧아서 장면이 갑자기 멈춘 것처럼 느껴졌다.',['감각'],[],'response-only'),

# Strong world signals. Missing a secondary response is acceptable; wrong world nutrition is not.
('w01','사람의 꿈을 병에 담아 보관하는 도시에서 병이 깨지면 기억도 사라진다는 설정이 기발했다.',['감정'],['상상'],'world'),
('w02','문을 열 때마다 백 년 전이나 백 년 뒤의 방으로 이어지는 집을 상상하는 재미가 있었다.',['감정'],['상상'],'world'),
('w03','작은 배로 여러 섬을 옮겨 다니며 지도에 없는 항구를 찾는 여정이 흥미로웠다.',['감정'],['모험'],'world'),
('w04','국경 도시마다 기차를 갈아타며 목적지 없이 이동하는 여행을 나도 해보고 싶었다.',['감정'],['모험'],'world'),
('w05','갯벌에 사는 작은 생물들이 물때에 따라 숨는 위치가 달라지는 이유를 더 찾아보고 싶었다.',['탐구'],['자연'],'world'),
('w06','봄 기온이 올라가면서 나비가 나타나는 시기가 어떻게 달라졌는지 실제 관찰 자료를 보고 싶었다.',['탐구'],['자연'],'world'),
('w07','임대료가 오른 뒤 오래 장사한 가게부터 동네를 떠나는 과정이 개인의 선택만은 아닌 것 같았다.',['사유'],['사회'],'world'),
('w08','같은 업무를 하는데 계약 형태에 따라 휴가와 보험이 달라지는 이유가 불공평하게 느껴졌다.',['사유','감정'],['사회'],'world'),
('w09','사라진 가족의 방만 매일 깨끗하게 정리되는 장면이 오히려 더 불안하고 무서웠다.',['감정'],['어둠'],'world'),
('w10','주민의 모든 이동을 카메라가 기록하고 규칙을 어기면 이름이 명단에서 지워지는 설정이 섬뜩했다.',['감정'],['어둠','사회'],'world'),

# Lexical/metaphoric decoys: response may feed, but named world keyword must not mutate the creature.
('d01','발표 순서를 미로를 탐험하듯 구성하라는 조언이 재미있었다.',['감정'],[],'decoy'),
('d02','어두운 초록색 표지와 거친 종이 질감의 조합이 마음에 들었다.',['감각'],[],'decoy'),
('d03','폭풍 같은 드럼 소리라는 표현이 공연장의 열기를 잘 살렸다.',['감각'],[],'decoy'),
('d04','사진을 찍을 때 자연스럽게 웃는 방법을 단계별로 설명한 부분을 따라 해봤다.',['탐구'],[],'decoy'),
('d05','마법이라는 이름의 디저트가 왜 인기인지 재료와 조리법을 비교해봤다.',['탐구'],[],'decoy'),
('d06','‘숲’이라는 제목의 피아노곡은 낮은 음이 반복되는 리듬이 특히 좋았다.',['감각'],[],'decoy'),
('d07','여행용 목베개를 접는 방법이 그림으로 잘 설명돼 있어 그대로 따라 해봤다.',['탐구'],[],'decoy'),
('d08','사회의 창이라는 이름의 신문 코너가 어느 면에 실리는지 목차에서 확인했다.',[],[],'decoy'),
('d09','미래라는 단어를 제목에 쓴 에세이의 판본이 여러 개라 출판연도를 대조했다.',[],[],'decoy'),
('d10','검은 밤이라는 향수 이름이 본문에 반복돼서 실제 제품명인지 검색해봤다.',['탐구'],[],'decoy'),
]
assert len(CASES)==40

clf=HybridE5ClassifierV31(MODEL)
rows=[]
for cid,text,er,ew,cat in CASES:
    a=clf.analyze(text)
    n=project_growth_nutrition(text,a)
    pr=list(n.response);pw=list(n.world)
    rows.append({'id':cid,'text':text,'category':cat,'expected_response':er,'expected_world':ew,'response':pr,'world':pw,'analysis':a})

s={'neutral':0,'neutral_ok':0,'response_present':0,'response_top1':0,'world_present':0,'world_top1':0,
   'world_null':0,'world_null_ok':0,'gold':0,'pred':0,'hit':0,'exact':0}
for r in rows:
    er=set(r['expected_response']);ew=set(r['expected_world']);pr=r['response'];pw=r['world']
    if r['category']=='neutral':
        s['neutral']+=1;s['neutral_ok']+=not pr and not pw
    if er:
        s['response_present']+=1;s['response_top1']+=bool(pr and pr[0] in er)
    if ew:
        s['world_present']+=1;s['world_top1']+=bool(pw and pw[0] in ew)
    else:
        s['world_null']+=1;s['world_null_ok']+=not pw
    g=set(('r',x) for x in er)|set(('w',x) for x in ew);p=set(('r',x) for x in pr)|set(('w',x) for x in pw)
    s['gold']+=len(g);s['pred']+=len(p);s['hit']+=len(g&p);s['exact']+=g==p

pct=lambda a,b:100*a/b if b else 0.0
metrics={
 'neutral_empty':pct(s['neutral_ok'],s['neutral']),
 'response_top1':pct(s['response_top1'],s['response_present']),
 'world_top1':pct(s['world_top1'],s['world_present']),
 'world_null':pct(s['world_null_ok'],s['world_null']),
 'precision':pct(s['hit'],s['pred']),
 'recall':pct(s['hit'],s['gold']),
 'exact':pct(s['exact'],len(rows)),
}
targets={'neutral_empty':90,'response_top1':80,'world_top1':80,'world_null':90,'precision':85,'recall':65}
passed=all(metrics[k]>=v for k,v in targets.items())

lines=['# BookEater hidden growth nutrition fresh blind v1','',
       '- classifier: `e5-hybrid-v3.1.1`','- growth projector: frozen before these 40 records were authored',
       '- after this first execution, this set is diagnostic rather than blind','',
       '|metric|result|target|','|---|---:|---:|']
for k,label in [('neutral_empty','neutral adds no nutrition'),('response_top1','response nutrition Top-1'),('world_top1','world nutrition Top-1'),('world_null','world false-modifier abstention'),('precision','nutrition label precision'),('recall','nutrition label recall'),('exact','exact records')]:
    t=f">={targets[k]}%" if k in targets else 'diagnostic'
    lines.append(f"|{label}|{metrics[k]:.1f}%|{t}|")
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
