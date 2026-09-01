from __future__ import annotations
import json,sys
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bookeater.nlp.hybrid_classifier_v31 import HybridE5ClassifierV31, MODEL_VERSION

MODEL=ROOT/'resources/models/multilingual-e5-small-onnx'
OUT=ROOT/'tests/e5_v311_blind_report.md'
JSON_OUT=ROOT/'tests/e5_v311_blind_results.json'

# IMPORTANT: These 64 records were authored after v3.1.1 was frozen (commit 621b6de...).
# Once this workflow is run, this set becomes inspected diagnostic data and MUST NOT be used
# to tune v3.1.1 while continuing to call the same result 'blind'.
CASES=[
# NULL/logistics — neither reading reaction nor one of the five world axes.
('n01','책갈피가 빠져서 마지막으로 읽은 페이지를 다시 찾아 표시했다.',[],[],'null'),
('n02','전자책 글자 크기를 한 단계 키우고 야간 모드로 바꿨다.',[],[],'null'),
('n03','이번 주 금요일이 반납일이라 휴대폰 달력에 알림을 넣었다.',[],[],'null'),
('n04','상권과 하권 중에서 상권부터 읽기 시작했다.',[],[],'null'),
('n05','저자 이름 철자가 헷갈려 책 뒤표지에서 다시 확인해 적었다.',[],[],'null'),
('n06','오늘은 서문까지 읽었고 내일 첫 장부터 이어 읽을 예정이다.',[],[],'null'),

# Out-of-grid themes: response may exist but world should abstain.
('o01','찻잎을 우리는 시간을 달리하면 떫은맛이 왜 달라지는지 직접 비교해보고 싶다.',['탐구'],[],'out-grid'),
('o02','수비수가 공간을 좁히는 방식이 경기 흐름을 어떻게 바꾸는지 다른 경기 영상도 찾아보고 싶었다.',['탐구'],[],'out-grid'),
('o03','기도가 원하는 결과를 얻는 기술이 아니라 기다리는 마음을 다루는 방식이라는 대목을 오래 생각했다.',['사유'],[],'out-grid'),
('o04','같은 선율을 반복하면서 마지막 한 음만 바꾸는 부분이 귀에 오래 남았다.',['감각'],[],'out-grid'),
('o05','계단의 폭과 천장 높이만 달라져도 공간이 전혀 다르게 느껴지는 점이 신기했다.',['감각'],[],'out-grid'),
('o06','한 문장을 두 번역가가 전혀 다른 높임말로 옮겨 인물의 거리가 달라 보였다.',['감각','사유'],[],'out-grid'),
('o07','코를 뜨는 순서를 그림과 대조하면서 어디서 무늬가 어긋났는지 확인했다.',['탐구'],[],'out-grid'),
('o08','양파를 먼저 볶는 것과 나중에 넣는 것이 향에 어떤 차이를 만드는지 해보고 싶었다.',['탐구','감각'],[],'out-grid'),

# Response-only, including ambiguous-looking phrases that must not invent a world label.
('r01','주인공을 미워했는데 마지막 편지를 읽고 나니 그 마음을 조금 이해하게 됐다.',['감정'],[],'response-only'),
('r02','결말이 행복하다고 말할 수 있는지 기준부터 다시 생각하게 됐다.',['사유'],[],'response-only'),
('r03','앞부분에서 제시한 사례가 정말 대표적인지 원문 자료를 찾아 확인하고 싶다.',['탐구'],[],'response-only'),
('r04','문장이 한없이 길어졌다가 마지막에 한 단어로 끝나는 리듬이 강하게 남았다.',['감각'],[],'response-only'),
('r05','친구를 돕기 위해 거짓말한 행동을 좋은 선택이라고 할 수 있는지 모르겠다.',['사유'],[],'response-only'),
('r06','인물이 웃으면서 미안하다고 말하는 장면이 오히려 더 서글펐다.',['감정'],[],'response-only'),
('r07','같은 사건을 설명하는 세 사람의 진술이 달라 앞 장면을 다시 비교해봤다.',['탐구'],[],'response-only'),
('r08','‘바스락’ 같은 소리가 반복돼 종이를 넘기는 장면이 실제처럼 들렸다.',['감각'],[],'response-only'),
('r09','내가 그 말을 들었다면 왜 그렇게 화가 났을지 바로 이해됐다.',['감정'],[],'response-only'),
('r10','문제의 답보다 질문을 어떤 순서로 던졌는지가 더 흥미로웠다.',['사유'],[],'response-only'),

# Social: several are intentionally implicit, without obvious 사회/정치 keywords.
('s01','같은 건물인데 꼭대기층 주민 카드가 있어야만 사용할 수 있는 엘리베이터가 있다는 설정이 불공평하게 느껴졌다.',['감정','사유'],['사회'],'social'),
('s02','점심시간에 줄을 서도 정규직 직원이 오면 계약직이 뒤로 물러나야 하는 장면이 이상했다.',['사유','감정'],['사회'],'social'),
('s03','아이의 성적보다 부모가 살고 있는 동네에 따라 선택할 수 있는 학교가 달라지는 점이 마음에 걸렸다.',['사유','감정'],['사회'],'social'),
('s04','같은 범죄인데 가진 돈에 따라 재판을 준비할 시간이 달라지는 이유를 더 알아보고 싶었다.',['탐구','사유'],['사회'],'social'),
('s05','마을 회의에서 말을 할 수 있는 사람과 듣기만 해야 하는 사람이 처음부터 정해져 있는 구조가 답답했다.',['감정','사유'],['사회'],'social'),
('s06','야간 버스가 끊긴 뒤 늦게 퇴근하는 사람들이 어떻게 이동하는지 실제 교통 자료를 찾아봤다.',['탐구'],['사회'],'social'),
('s07','같은 회사에서 비슷한 일을 하는데 고용 형태에 따라 휴가 일수가 다른 이유가 궁금했다.',['탐구','사유'],['사회'],'social'),
('s08','재난 지원금을 신청하려면 온라인 인증이 꼭 필요해서 휴대폰이 없는 노인이 제외되는 장면이 불편했다.',['감정','사유'],['사회'],'social'),

# Nature/adventure confounds.
('a01','연어가 강을 거슬러 올라가는 경로를 지도에 표시하며 어느 지류를 선택하는지 찾아봤다.',['탐구'],['자연'],'nature-vs-adventure'),
('a02','사막여우가 먹이를 찾아 밤마다 움직이는 범위를 연구한 부분이 흥미로워 실제 자료를 더 보고 싶었다.',['탐구'],['자연'],'nature-vs-adventure'),
('a03','낯선 섬들을 배로 옮겨 다니며 오래된 등대를 찾아가는 여정이 좋았다.',['감정'],['모험'],'nature-vs-adventure'),
('a04','산맥을 넘는 열차에서 매일 다른 마을에 내려 걷는 장면을 보니 나도 그런 여행을 해보고 싶었다.',['감정'],['모험','자연'],'nature-vs-adventure'),
('a05','태풍 때문에 항로를 바꾸고 작은 항구에 피신하는 과정이 긴장감 있었다.',['감정'],['모험','자연','어둠'],'nature-vs-adventure'),
('a06','바다거북의 이동을 위성 자료로 추적한 그래프를 보고 어느 계절에 경로가 달라지는지 확인했다.',['탐구'],['자연'],'nature-vs-adventure'),
('a07','배낭 하나만 들고 국경 도시를 차례로 지나가는 장면에서 길을 잃는 순간까지 재미있었다.',['감정'],['모험'],'nature-vs-adventure'),
('a08','빙하 위를 횡단하는 탐험대가 갈라진 얼음을 피해 우회하는 장면이 무서우면서도 흥미로웠다.',['감정'],['모험','자연','어둠'],'nature-vs-adventure'),

# Imagination, including nonfiction future decoys elsewhere below.
('i01','사람의 그림자가 밤마다 주인보다 먼저 집을 나간다는 설정이 묘하게 재미있었다.',['감정'],['상상'],'imagination'),
('i02','도시 전체가 거대한 고래의 등에 세워져 있다는 세계를 머릿속으로 그려보게 됐다.',['감정'],['상상'],'imagination'),
('i03','어제의 기억을 돈처럼 사고팔 수 있다면 가난한 사람은 무엇을 잃게 될지 생각했다.',['사유'],['상상','사회'],'imagination'),
('i04','죽은 사람에게 하루 동안만 편지를 보낼 수 있는 우체국 설정 때문에 이별을 다르게 생각하게 됐다.',['사유','감정'],['상상','어둠'],'imagination'),
('i05','시간이 멈춘 도시에서 혼자만 늙어가는 인물이 두려웠다.',['감정'],['상상','어둠'],'imagination'),
('i06','달빛을 모아 겨울 난방비로 쓰는 마을이라는 설정이 따뜻하고 기발했다.',['감정'],['상상'],'imagination'),

# Metaphoric darkness / implicit loss.
('d01','식탁에는 네 사람의 접시가 그대로 놓이는데 아무도 네 번째 사람의 이름을 말하지 않아 더 쓸쓸했다.',['감정'],['어둠'],'metaphor-dark'),
('d02','대화가 이어질수록 한 인물의 말만 괄호 속으로 들어가다가 마지막에는 빈 괄호만 남는 장면이 섬뜩했다.',['감각','감정'],['어둠'],'metaphor-dark'),
('d03','아버지가 떠난 뒤 집 안의 모든 시계가 유난히 크게 들린다는 문장이 상실을 직접 말하는 것보다 슬펐다.',['감각','감정'],['어둠'],'metaphor-dark'),
('d04','사람들이 그를 바라보고는 있지만 누구도 질문에 대답하지 않아 방 한가운데 구멍이 난 것처럼 느껴졌다.',['감정'],['어둠'],'metaphor-dark'),
('d05','매일 아침 게시판에서 한 사람의 사진만 조금씩 흐려지는 장면이 무서웠다.',['감정','감각'],['어둠'],'metaphor-dark'),
('d06','축하 파티인데 주인공에게만 빈 잔이 놓여 있는 장면이 관계에서 밀려난 느낌을 줬다.',['감정','사유'],['어둠'],'metaphor-dark'),

# Multi-axis world/topic cases.
('m01','홍수 뒤 보험이 없는 주민들만 집을 떠나고 높은 지대의 새 주택은 부유한 사람에게 먼저 배정되는 과정이 답답했다.',['감정','사유'],['자연','사회','어둠'],'multi'),
('m02','마법학교에서 귀족 가문 아이들만 금지된 주문을 배울 수 있다는 규칙이 불공평했다.',['감정','사유'],['상상','사회'],'multi'),
('m03','전쟁이 끝난 행성을 순회하는 우주선이 폐허가 된 도시마다 생존자를 찾는 여정이 무거웠다.',['감정'],['상상','모험','어둠'],'multi'),
('m04','가뭄 때문에 목장을 떠난 가족이 다른 지역에서 일자리를 구하는 과정이 개인의 선택만은 아닌 것 같았다.',['사유','감정'],['자연','사회','모험'],'multi'),
('m05','사라진 숲을 되살리기 위해 주민들이 관광 수입을 포기할지 투표하는 장면에서 어느 쪽도 쉽게 고르기 어려웠다.',['사유'],['자연','사회'],'multi'),
('m06','미래 도시에서 깨끗한 공기를 사는 구역과 무료 배급을 기다리는 구역이 나뉘어 있는 설정이 섬뜩했다.',['감정','사유'],['상상','사회','어둠'],'multi'),
('m07','빙하가 녹아 새 항로가 열리자 여러 나라가 그 길을 차지하려는 장면이 복잡하게 느껴졌다.',['사유'],['자연','모험','사회'],'multi'),
('m08','괴물에게 쫓겨 숲을 건너는 아이들이 서로 먹을 것을 나누는 장면에서 공포보다 관계가 더 크게 남았다.',['감정'],['상상','모험','자연','어둠'],'multi'),

# Lexical/semantic traps.
('c01','2045년 인구 전망 보고서에서 청년 인구가 줄어드는 수치를 보고 지역별 통계도 비교해봤다.',['탐구'],['사회'],'confound'),
('c02','진한 검은색 잉크와 어두운 남색 면지가 차분해서 표지 디자인이 마음에 들었다.',['감각'],[],'confound'),
('c03','문제를 푸는 과정을 미로를 탐험하듯 설명한 비유가 재미있었다.',['감각','감정'],[],'confound'),
('c04','‘폭풍이 몰아치는 박수’라는 표현이 무대의 열기를 과장해서 보여주는 것 같았다.',['감각'],[],'confound'),
('c05','자연스럽게 말하는 법을 알려주는 발표 안내서라 실제로 문장을 소리 내 연습해봤다.',['감각','탐구'],[],'confound'),
('c06','AI 산업의 10년 뒤 전망을 다룬 보고서에서 직종별 고용 변화 근거를 더 확인하고 싶었다.',['탐구'],['사회'],'confound'),
]

# 64 cases exactly.
assert len(CASES)==64, len(CASES)

def evaluate(rows):
    s={'r_present':0,'r_top1':0,'r_null':0,'r_null_ok':0,'w_present':0,'w_top1':0,'w_null':0,'w_null_ok':0,'gold':0,'hit':0,'pred':0,'exact':0}
    by=defaultdict(lambda:{'n':0,'gold':0,'hit':0,'pred':0,'exact':0})
    for r in rows:
        er,ew,pr,pw=r['expected_response'],r['expected_world'],r['response'],r['world']
        if er:s['r_present']+=1;s['r_top1']+=int(bool(pr) and pr[0] in er)
        else:s['r_null']+=1;s['r_null_ok']+=int(not pr)
        if ew:s['w_present']+=1;s['w_top1']+=int(bool(pw) and pw[0] in ew)
        else:s['w_null']+=1;s['w_null_ok']+=int(not pw)
        g=set(('r',x) for x in er)|set(('w',x) for x in ew);p=set(('r',x) for x in pr)|set(('w',x) for x in pw)
        s['gold']+=len(g);s['hit']+=len(g&p);s['pred']+=len(p);s['exact']+=int(g==p)
        z=by[r['category']];z['n']+=1;z['gold']+=len(g);z['hit']+=len(g&p);z['pred']+=len(p);z['exact']+=int(g==p)
    return s,dict(by)

def pct(a,b): return 100*a/b if b else 0.0

model=HybridE5ClassifierV31(MODEL);rows=[]
for cid,text,er,ew,cat in CASES:
    p=model.analyze(text);rows.append({'id':cid,'text':text,'category':cat,'expected_response':er,'expected_world':ew,'response':p['response'],'world':p['world'],'scores':p['scores'],'null':p['null'],'evidence':p['evidence']})
s,by=evaluate(rows)
lines=['# BookEater E5 hybrid v3.1.1 fresh blind validation','',f'- frozen model: `{MODEL_VERSION}`','- This is the first run on these 64 records. After this run they are diagnostic, not blind.','',
'|metric|result|target|','|---|---:|---:|',
f"|response Top-1|{pct(s['r_top1'],s['r_present']):.1f}%|>=80%|",f"|response NULL|{pct(s['r_null_ok'],s['r_null']):.1f}%|>=95%|",f"|world Top-1|{pct(s['w_top1'],s['w_present']):.1f}%|>=80%|",f"|world NULL|{pct(s['w_null_ok'],s['w_null']):.1f}%|>=90%|",f"|label recall|{pct(s['hit'],s['gold']):.1f}%|>=75%|",f"|label precision|{pct(s['hit'],s['pred']):.1f}%|>=75%|",f"|exact records|{pct(s['exact'],len(rows)):.1f}%|diagnostic|",'',
'## Category summary','', '|category|n|label recall|label precision|exact records|','|---|---:|---:|---:|---:|']
for cat,z in sorted(by.items()):lines.append(f"|{cat}|{z['n']}|{pct(z['hit'],z['gold']):.1f}%|{pct(z['hit'],z['pred']):.1f}%|{pct(z['exact'],z['n']):.1f}%|")
lines += ['','## Sample inspection (first two per category)','']
for cat in sorted(by):
    lines.append(f'### {cat}')
    for r in [x for x in rows if x['category']==cat][:2]:
        lines += [f"- **{r['id']}** {r['text']}",f"  - gold R={r['expected_response'] or ['NULL']} / W={r['expected_world'] or ['NULL']}",f"  - pred R={r['response'] or ['NULL']} / W={r['world'] or ['NULL']}"]
lines += ['','## Unexpected-error watchlist','']
for r in rows:
    g=set(('r',x) for x in r['expected_response'])|set(('w',x) for x in r['expected_world']);p=set(('r',x) for x in r['response'])|set(('w',x) for x in r['world'])
    if g!=p:
        miss=sorted(f'{a}:{b}' for a,b in g-p);extra=sorted(f'{a}:{b}' for a,b in p-g)
        lines.append(f"- {r['id']} [{r['category']}] missing={miss or '-'} extra={extra or '-'} :: {r['text']}")
OUT.parent.mkdir(exist_ok=True);OUT.write_text('\n'.join(lines),encoding='utf-8');JSON_OUT.write_text(json.dumps({'model_version':MODEL_VERSION,'stats':s,'categories':by,'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8');print('\n'.join(lines))
