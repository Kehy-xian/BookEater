from __future__ import annotations
import json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bookeater.nlp.hybrid_classifier_v31 import HybridE5ClassifierV31
from bookeater.game.nutrition import project_growth_nutrition

MODEL=ROOT/'resources/models/multilingual-e5-small-onnx'
OUT=ROOT/'tests/growth_nutrition_blind_v4.md'
JSON_OUT=ROOT/'tests/growth_nutrition_blind_v4.json'

# Fresh product-oriented holdout authored after growth-nutrition-v1.3 was frozen.
# response_ok = acceptable single dominant response readings; [] means response may abstain.
# world_required = modifiers whose absence would materially under-represent the note.
# world_allowed = required plus arguable secondary modifiers that must not count as false growth.
# category is diagnostic only.
def C(cid,text,response_ok,world_required=(),world_allowed=None,category=''):
    wr=list(world_required); wa=list(world_allowed if world_allowed is not None else wr)
    return dict(id=cid,text=text,response_ok=list(response_ok),world_required=wr,world_allowed=wa,category=category)

CASES=[
# Pure administration / reading logistics: no phenotype signal.
C('n01','예약한 책이 도착했다는 알림이 와서 수령 가능 날짜를 확인했다.',[],category='neutral'),
C('n02','오늘 46쪽부터 71쪽까지 읽었다고 독서표에 적었다.',[],category='neutral'),
C('n03','전자책 동기화가 안 돼 마지막 읽은 위치를 직접 맞췄다.',[],category='neutral'),
C('n04','도서관 스티커가 가려서 책의 ISBN을 뒤표지에서 다시 찾았다.',[],category='neutral'),
C('n05','다 읽은 책은 반납함에 넣고 다음 권을 대출했다.',[],category='neutral'),
C('n06','글자 크기를 키우니 한 화면에 보이는 줄 수가 줄었다.',[],category='neutral'),
C('n07','초판 2쇄인지 개정판인지 판권 페이지를 확인했다.',[],category='neutral'),
C('n08','가방 무게를 줄이려고 오늘 읽을 한 권만 챙겼다.',[],category='neutral'),
C('n09','책갈피가 빠져서 어제 읽던 페이지를 다시 찾았다.',[],category='neutral'),
C('n10','목차를 사진으로 찍어 다음에 읽을 장만 표시해 두었다.',[],category='neutral'),

# Meaningful reflection coexisting with metadata/logistics vocabulary.
C('m01','46쪽에서 아이가 혼자 식탁을 치우는 장면이 괜히 짠하고 마음에 남았다.',['감정'],category='metadata-mixed'),
C('m02','반납 전에 마지막 장을 다시 읽었는데 그 선택을 용기라고 불러도 되는지 고민됐다.',['사유'],category='metadata-mixed'),
C('m03','목차의 복지 제도 부분을 읽고 지원 기준에서 빠지는 사람은 왜 생기는지 궁금했다.',['사유','탐구'],['사회'],category='metadata-mixed'),
C('m04','책갈피를 꽂아 둔 문단은 문장이 짧게 끊겨서 실제 숨이 차는 듯한 리듬이 느껴졌다.',['감각'],category='metadata-mixed'),
C('m05','개정판의 그래프가 달라진 이유가 궁금해서 원자료와 조사 방식을 비교해 보고 싶다.',['탐구'],category='metadata-mixed'),
C('m06','대출한 책에서 갯벌 생물이 물이 빠질 때 숨는 모습을 읽고 실제 생태도 찾아보고 싶었다.',['탐구'],['자연'],category='metadata-mixed'),
C('m07','278쪽의 재판에서 같은 절차인데 돈이 있는 사람만 더 쉽게 대응하는 점이 공정하지 않다고 느꼈다.',['사유'],['사회'],category='metadata-mixed'),
C('m08','페이지 아래쪽에 반복되는 푸른빛 묘사가 장면의 쓸쓸한 분위기를 더 선명하게 만들었다.',['감각','감정'],category='metadata-mixed'),
C('m09','반납일 때문에 빨리 읽었지만 마지막 편지를 읽는 장면에서는 결국 울컥했다.',['감정'],category='metadata-mixed'),
C('m10','목차에서 기후 장을 골라 읽었는데 해수 온도와 산호 감소의 관계를 더 확인해 보고 싶었다.',['탐구'],['자연'],category='metadata-mixed'),

# Titles, product names, metaphor, decorative words, and substring traps.
C('d01','“별빛 여행”이라는 향수 제품의 광고 문장을 비교해 어느 표현이 과장됐는지 살펴봤다.',['탐구'],category='decoy'),
C('d02','숲이라는 이름의 독서 모임은 실제로는 추리소설 번역을 비교하는 모임이었다.',['감각','탐구'],category='decoy'),
C('d03','설명 방법이 단순해서 처음 배우는 사람도 따라 하기 쉬웠다.',['감각'],category='decoy'),
C('d04','죽순을 오래 삶으면 식감이 어떻게 달라지는지 조리 순서를 확인했다.',['탐구'],category='decoy'),
C('d05','이 문장은 파도처럼 밀려온다는 비유 덕분에 소리의 리듬이 살아났다.',['감각'],category='decoy'),
C('d06','전쟁이라는 이름의 보드게임 규칙 설명이 복잡해서 예시를 다시 읽었다.',['탐구','감각'],category='decoy'),
C('d07','사회 과목 참고서인데 표와 제목 배치가 깔끔해서 내용을 찾기 편했다.',['감각'],category='decoy'),
C('d08','“마법”은 카페 메뉴 이름일 뿐이고 이 글은 원두 보관법을 설명한다.',['탐구'],category='decoy'),
C('d09','여행을 다루는 장은 없고 한 가족이 오래된 오해를 풀어가는 이야기였다.',['감정'],category='decoy'),
C('d10','자연스럽게 말하는 법을 연습하라는 조언에서 발음 예시를 여러 번 따라 했다.',['탐구','감각'],category='decoy'),
C('d11','조금 우습지만 문장 구조는 명확해서 핵심을 금방 이해했다.',['감각'],category='decoy'),
C('d12','“어둠의 숲”이라는 공연 제목보다 무대 조명의 색 대비가 더 인상적이었다.',['감각'],category='decoy'),

# Pure response axis: no world modifier should be invented.
C('r01','좋은 의도라면 상대에게 사실을 숨겨도 되는지 계속 생각하게 됐다.',['사유'],category='response'),
C('r02','아이가 엄마를 기다리다 잠드는 장면이 너무 안쓰러웠다.',['감정'],category='response'),
C('r03','저자가 인용한 통계의 표본이 충분한지 원문을 찾아 확인하고 싶다.',['탐구'],category='response'),
C('r04','긴 문장 뒤에 한 단어만 놓인 문장이 이어져 리듬이 확 달라졌다.',['감각'],category='response'),
C('r05','규칙을 지킨 행동과 책임 있는 행동이 항상 같은 것은 아닌 것 같다.',['사유'],category='response'),
C('r06','둘 다 미안해하면서도 먼저 연락하지 못하는 마음이 이해돼서 씁쓸했다.',['감정'],category='response'),
C('r07','설명의 근거가 한 연구에만 의존하는지 다른 자료도 비교해 보고 싶다.',['탐구'],category='response'),
C('r08','같은 대사가 번역에 따라 다정하게도 차갑게도 들리는 점이 흥미롭다.',['감각'],category='response'),
C('r09','결말이 행복하다고 단정하는 기준 자체가 누구의 것인지 의문이 들었다.',['사유'],category='response'),
C('r10','주인공이 아무 말 없이 떠난 뒤 남은 사람의 표정이 오래 기억났다.',['감정'],category='response'),
C('r11','도표의 두 수치를 더하면 본문의 합계와 달라서 계산 과정을 다시 확인했다.',['탐구'],category='response'),
C('r12','쉼표가 거의 없는 문장을 소리 내 읽으니 속도가 빨라지는 느낌이 재미있었다.',['감각'],category='response'),

# Literal world/topic signals. Some secondary readings are allowed but not required.
C('w01','사람의 꿈을 다른 사람에게 빌려줄 수 있는 도서관이라는 설정이 신기했다.',['감정'],['상상'],['상상'],category='world'),
C('w02','매일 자정이 되면 하루가 거꾸로 흐르는 도시를 상상하는 재미가 있었다.',['감정'],['상상'],['상상','어둠'],category='world'),
C('w03','작은 범선을 타고 지도에 없는 섬을 찾아가는 항해가 흥미진진했다.',['감정'],['모험'],['모험','상상'],category='world'),
C('w04','국경을 여러 번 넘으며 낯선 마을을 지나 목적지까지 가는 여정이 긴장됐다.',['감정'],['모험'],['모험','어둠'],category='world'),
C('w05','철새가 쉬던 습지가 줄자 이동 경로까지 달라지는 과정을 더 알아보고 싶었다.',['탐구'],['자연'],['자연'],category='world'),
C('w06','해수 온도가 높아질수록 산호가 하얗게 변하는 원리가 궁금했다.',['탐구'],['자연'],['자연'],category='world'),
C('w07','계약직에게만 병가가 보장되지 않는 회사 규정이 왜 가능한지 생각했다.',['사유','탐구'],['사회'],['사회'],category='world'),
C('w08','재개발 뒤 임대료가 올라 원래 살던 주민이 떠나는 구조가 개인 선택처럼 보이지 않았다.',['사유'],['사회'],['사회','어둠'],category='world'),
C('w09','사라진 아이의 방에서 시계 소리만 반복되는 장면이 조용해서 더 무서웠다.',['감정'],['어둠'],['어둠'],category='world'),
C('w10','감시 카메라를 피하려고 매일 다른 길로 다니는 인물이 들킬까 봐 불안했다.',['감정'],['어둠'],['어둠','모험'],category='world'),
C('w11','가상 도시에서 시민의 점수에 따라 투표권이 달라진다는 제도가 섬뜩했다.',['감정','사유'],['상상','사회'],['상상','사회','어둠'],category='world'),
C('w12','홍수 위험 때문에 마을 이전 정책이 정해지는 과정을 보며 기후와 주거 문제가 연결돼 있다고 느꼈다.',['사유'],['자연','사회'],['자연','사회','어둠'],category='world'),
C('w13','전쟁이 끝난 폐허에서 가족을 잃은 인물이 고향을 떠나는 장면이 마음 아팠다.',['감정'],['어둠'],['어둠','모험'],category='world'),
C('w14','숲을 베어 공장을 세운 뒤 주민의 물과 야생동물 서식지가 함께 줄어드는 내용이 답답했다.',['감정','사유'],['자연','사회'],['자연','사회','어둠'],category='world'),
C('w15','다른 행성의 바다 아래 도시를 탐험하는 장면을 보며 그곳을 직접 걸어보고 싶었다.',['감정'],['상상','모험'],['상상','모험','자연'],category='world'),
C('w16','시간을 멈출 수 있는 능력을 국가가 허가제로 관리한다는 설정이 자유와 권력을 생각하게 했다.',['사유'],['상상','사회'],['상상','사회'],category='world'),

# Visual language plus genuine content: surface guards must not erase the actual topic.
C('x01','삽화의 초록빛도 예뻤지만 산불 뒤 숲의 생태가 회복되는 과정이 더 궁금했다.',['탐구','감각'],['자연'],['자연'],category='mixed'),
C('x02','지도 디자인이 멋졌고 주인공이 그 지도를 따라 국경을 넘는 여행도 흥미로웠다.',['감정','감각'],['모험'],['모험'],category='mixed'),
C('x03','차가운 색의 그림이 인상적이었는데 감시 제도 때문에 사람들이 서로를 피하는 내용과 잘 어울렸다.',['감각','사유'],['사회'],['사회','어둠'],category='mixed'),
C('x04','바다를 그린 삽화보다 해수 온도 변화가 생물의 번식에 미치는 설명이 더 기억에 남았다.',['탐구'],['자연'],['자연'],category='mixed'),
]
assert len(CASES)==64

clf=HybridE5ClassifierV31(MODEL)
rows=[]
for c in CASES:
    a=clf.analyze(c['text']); n=project_growth_nutrition(c['text'],a)
    rows.append({**c,'response':list(n.response),'world':list(n.world),'analysis':a})

s=dict(neutral=0,neutral_ok=0,meta=0,meta_survive=0,response_req=0,response_hit=0,response_pred=0,response_good=0,
       world_req=0,world_req_hit=0,world_pred=0,world_good=0,world_null=0,world_null_clean=0,exact=0)
watch=[]
for r in rows:
    pr=list(r['response']); pw=list(r['world']); rok=set(r['response_ok']); wr=set(r['world_required']); wa=set(r['world_allowed'])
    if r['category']=='neutral':
        s['neutral']+=1; s['neutral_ok']+=not pr and not pw
    if r['category']=='metadata-mixed':
        s['meta']+=1; s['meta_survive']+=bool(pr or pw)
    if rok:
        s['response_req']+=1; s['response_hit']+=bool(pr and pr[0] in rok)
    s['response_pred']+=len(pr); s['response_good']+=sum(x in rok for x in pr)
    s['world_req']+=len(wr); s['world_req_hit']+=len(wr & set(pw))
    s['world_pred']+=len(pw); s['world_good']+=sum(x in wa for x in pw)
    if not wr:
        s['world_null']+=1; s['world_null_clean']+=not pw
    response_ok=(not rok and not pr) or (bool(pr) and pr[0] in rok)
    world_ok=wr.issubset(set(pw)) and set(pw).issubset(wa)
    s['exact']+=response_ok and world_ok
    if not (response_ok and world_ok):
        watch.append((r,response_ok,world_ok))

pct=lambda a,b:100*a/b if b else 100.0
metrics={
 'neutral_empty':pct(s['neutral_ok'],s['neutral']),
 'metadata_survival':pct(s['meta_survive'],s['meta']),
 'response_recall':pct(s['response_hit'],s['response_req']),
 'response_precision':pct(s['response_good'],s['response_pred']),
 'world_required_recall':pct(s['world_req_hit'],s['world_req']),
 'world_precision':pct(s['world_good'],s['world_pred']),
 'world_null_clean':pct(s['world_null_clean'],s['world_null']),
 'exact_records':pct(s['exact'],len(rows)),
}
targets={'neutral_empty':95,'metadata_survival':80,'response_recall':75,'response_precision':88,
         'world_required_recall':80,'world_precision':90,'world_null_clean':92}
passed=all(metrics[k]>=v for k,v in targets.items())
labels={'neutral_empty':'neutral adds no nutrition','metadata_survival':'substantive metadata-mixed notes survive',
        'response_recall':'response recall','response_precision':'response precision',
        'world_required_recall':'required world recall','world_precision':'world modifier precision',
        'world_null_clean':'no-world abstention','exact_records':'product-exact records'}
lines=['# BookEater hidden growth fresh blind v4','',
       '- classifier: `e5-hybrid-v3.1.1`','- growth projector: `growth-nutrition-v1.3` frozen before these 64 records were authored',
       '- scoring distinguishes required modifiers from acceptable ambiguous secondary readings',
       '- after this first execution, this set becomes diagnostic','',
       '|metric|result|target|','|---|---:|---:|']
for k,v in metrics.items():
    t=f">={targets[k]}%" if k in targets else 'diagnostic'
    lines.append(f"|{labels[k]}|{v:.1f}%|{t}|")
lines += ['',f"**release-style gate: {'PASS' if passed else 'FAIL'}**",'', '## Watchlist','']
for r,response_ok,world_ok in watch:
    lines.append(
        f"- {r['id']} [{r['category']}] response={r['response']} ok={r['response_ok']} "
        f"world={r['world']} required={r['world_required']} allowed={r['world_allowed']} :: {r['text']}"
    )
OUT.parent.mkdir(exist_ok=True)
OUT.write_text('\n'.join(lines),encoding='utf-8')
JSON_OUT.write_text(json.dumps({'metrics':metrics,'targets':targets,'passed':passed,'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
print('\n'.join(lines))
if not passed: raise SystemExit(2)
