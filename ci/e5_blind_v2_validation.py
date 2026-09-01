from __future__ import annotations
import json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bookeater.nlp import HybridE5Classifier

MODEL=ROOT/'resources/models/multilingual-e5-small-onnx'
OUT=ROOT/'tests/e5_blind_v2_report.md'
JSON_OUT=ROOT/'tests/e5_blind_v2_results.json'

# Written after v2 rules were frozen. Do not modify v2 based on this set and still call these numbers blind.
CASES=[
('b01','책을 다 읽고 반납함에 넣었다.',[],[],'null'),
('b02','어제 읽은 곳부터 이어서 열다섯 쪽을 더 읽었다.',[],[],'null'),
('b03','책 표지에 붙은 띠지를 버리고 책장 두 번째 칸에 꽂았다.',[],[],'null'),
('b04','등장인물 관계를 헷갈리지 않으려고 이름만 따로 적었다.',[],[],'null'),
('b05','빵 반죽의 발효 시간을 다르게 했을 때 식감이 왜 달라지는지 실험해보고 싶었다.',['탐구'],[],'out-grid'),
('b06','피아노 페달을 밟는 위치에 따라 같은 곡의 분위기가 어떻게 달라지는지 비교해보고 싶다.',['탐구','감각'],[],'out-grid'),
('b07','명상할 때 떠오르는 생각을 억지로 없애지 말라는 부분이 내가 감정을 대하는 방식과 닮았다고 느꼈다.',['감정','사유'],[],'out-grid'),
('b08','외국어의 존댓말을 한국어로 옮기면 인물 관계가 달라 보이는 점이 흥미롭다.',['감각','사유'],[],'out-grid'),
('b09','주인공이 사과를 받고도 바로 용서하지 못하는 마음이 너무 이해됐다.',['감정'],[],'response-only'),
('b10','마지막 선택이 최선이었는지 모르겠다. 다른 선택도 충분히 가능했을 것 같다.',['사유'],[],'response-only'),
('b11','앞 장의 주장과 뒤 장의 수치가 맞지 않는 것 같아 원자료를 확인해보고 싶었다.',['탐구'],[],'response-only'),
('b12','짧은 문장을 연달아 놓아서 장면이 빠르게 잘리는 영화처럼 느껴졌다.',['감각'],[],'response-only'),
('b13','좋은 의도로 한 행동이라도 상대에게 상처가 되면 책임이 없는 건지 생각했다.',['사유','감정'],[],'response-only'),
('b14','설명 순서를 바꿔 놓으니 같은 정보인데 훨씬 이해하기 편해 보였다.',['감각'],[],'response-only'),
('b15','학교가 학생의 머리 길이까지 정하는 장면을 보며 규칙의 범위가 어디까지여야 하는지 궁금했다.',['사유'],['사회'],'social'),
('b16','아르바이트생에게만 휴게시간을 제대로 주지 않는 가게 이야기가 화가 났다.',['감정'],['사회'],'social'),
('b17','지역마다 병원 수가 다른 이유를 인구 자료와 함께 더 찾아보고 싶었다.',['탐구'],['사회'],'social'),
('b18','재개발 뒤 같은 동네에 살던 사람들이 임대료 때문에 떠나야 하는 과정이 씁쓸했다.',['감정','사유'],['사회','어둠'],'social'),
('b19','선거 결과보다 누가 투표소에 가기 어려운 조건에 놓이는지가 더 눈에 들어왔다.',['사유'],['사회'],'social'),
('b20','회사 규정은 모두에게 같지만 육아 중인 사람에게 훨씬 불리하게 작동하는 것 같았다.',['사유','감정'],['사회'],'social'),
('b21','달의 뒷면에 거대한 도서관이 숨어 있다는 설정만으로 계속 읽고 싶어졌다.',['감정'],['상상'],'imagination'),
('b22','사람의 기억을 다른 몸에 옮길 수 있다면 그 사람이 여전히 같은 사람인지 생각하게 됐다.',['사유'],['상상'],'imagination'),
('b23','모든 꿈이 중앙 서버에 저장되는 도시에서 삭제 권한을 가진 사람만 특권층이 되는 설정이 무서웠다.',['사유','감정'],['상상','사회','어둠'],'multi'),
('b24','신화 속 바다 괴물을 찾아 섬을 옮겨 다니는 항해 장면이 신났다.',['감정'],['상상','모험'],'multi'),
('b25','눈이 내리지 않게 된 마을에서 농사를 포기하는 사람들이 늘어난 이유를 기후 자료와 함께 보고 싶었다.',['탐구'],['자연','사회'],'multi'),
('b26','산호초가 사라지면서 물고기와 어민의 생활이 함께 달라지는 부분이 복잡하게 느껴졌다.',['사유'],['자연','사회'],'multi'),
('b27','산양이 절벽을 오르는 장면을 보고 발굽 구조가 어떻게 버티는지 찾아봤다.',['탐구'],['자연'],'nature'),
('b28','봄이 늦어지자 꽃 피는 시기와 곤충의 활동 시기가 어긋난다는 설명이 인상적이었다.',['탐구'],['자연'],'nature'),
('b29','비 냄새와 젖은 나무껍질의 질감을 묘사한 부분이 실제 숲처럼 느껴졌다.',['감각'],['자연'],'nature'),
('b30','사막을 횡단하면서 물을 나눠 쓰는 장면에서 목적지보다 동료들의 관계가 더 기억에 남았다.',['감정'],['모험','자연'],'adventure'),
('b31','기차를 갈아타며 여러 나라를 지나가는 과정이 좋아 실제 노선을 지도에서 찾아봤다.',['탐구','감정'],['모험'],'adventure'),
('b32','길을 잃은 뒤 계획에 없던 마을에서 며칠 머무는 장면이 여행의 재미처럼 느껴졌다.',['감정'],['모험'],'adventure'),
('b33','누구도 비명을 지르지 않는데 복도 끝의 빈 신발만 반복해서 나와 더 무서웠다.',['감각','감정'],['어둠'],'metaphor'),
('b34','주인공의 이름이 대화에서 조금씩 사라지다가 마지막에는 번호로만 불리는 과정이 섬뜩했다.',['감정','사유'],['사회','어둠'],'metaphor'),
('b35','밝은 음악이 흐르는 동안 화면 밖에서 폭력이 일어나는 듯한 묘사가 오히려 더 불편했다.',['감각','감정'],['어둠'],'dark'),
('b36','감염된 사람을 보호한다는 명목으로 가족과 연락하지 못하게 하는 규칙이 무서웠다.',['사유','감정'],['사회','어둠'],'dark'),
('b37','별자리 관측 기록을 이용해 옛 항해자의 실제 이동 경로를 확인해보고 싶었다.',['탐구'],['모험'],'confound'),
('b38','미래 인구 감소를 예측한 통계 보고서를 읽고 지역별 자료도 더 찾아봤다.',['탐구'],['사회'],'confound'),
('b39','어두운 초록색 표지와 거친 종이 질감이 책 분위기와 잘 어울렸다.',['감각'],[],'confound'),
('b40','동물처럼 빠르게 움직인다는 비유가 많지만 실제 내용은 주식 거래 전략을 설명하는 책이었다.',['감각'],[],'confound'),
('b41','폭풍 같은 박수라는 표현이 공연장의 열기를 잘 살렸다.',['감각','감정'],[],'confound'),
('b42','자연스럽게 웃는 법을 연습하라는 자기계발서의 조언은 오히려 어색하게 느껴졌다.',['감정','사유'],[],'confound'),
('b43','가난한 구역만 정전이 반복되는 미래 도시에서 전기를 배급하는 회사가 권력을 갖는 설정이 현실적으로 무서웠다.',['사유','감정'],['상상','사회','어둠'],'multi'),
('b44','거대한 산불을 피해 다른 도시로 이동하는 가족의 여정에서 재난보다 서로를 챙기는 모습이 더 마음에 남았다.',['감정'],['모험','자연','어둠'],'multi'),
('b45','왕이 세금을 걷어 마법을 쓸 수 있는 사람에게만 교육을 제공하는 세계가 불공평하게 느껴졌다.',['감정','사유'],['상상','사회'],'multi'),
('b46','해수면 상승으로 섬을 떠나는 주민들의 이야기를 읽고 실제 이주 사례가 있는지 찾아봤다.',['탐구','감정'],['모험','자연','사회'],'multi'),
('b47','친구가 떠난 뒤 방 안의 시계 소리만 커졌다는 문장이 외로움을 직접 말하지 않아도 마음에 남았다.',['감각','감정'],['어둠'],'metaphor'),
('b48','모두가 칭찬하는 주인공에게만 의자가 없는 장면이 집단의 배제를 보여주는 것 같았다.',['사유','감정'],['사회','어둠'],'metaphor'),
]


def metrics(rows):
    d={'r_present':0,'r_top1':0,'r_null':0,'r_null_ok':0,'w_present':0,'w_top1':0,'w_null':0,'w_null_ok':0,'gold':0,'hit':0,'pred':0,'exact':0}
    for row in rows:
        er,ew,pr,pw=row['expected_response'],row['expected_world'],row['response'],row['world']
        if er:d['r_present']+=1;d['r_top1']+=int(bool(pr) and pr[0] in er)
        else:d['r_null']+=1;d['r_null_ok']+=int(not pr)
        if ew:d['w_present']+=1;d['w_top1']+=int(bool(pw) and pw[0] in ew)
        else:d['w_null']+=1;d['w_null_ok']+=int(not pw)
        g=set(('r',x) for x in er)|set(('w',x) for x in ew);p=set(('r',x) for x in pr)|set(('w',x) for x in pw)
        d['gold']+=len(g);d['hit']+=len(g&p);d['pred']+=len(p);d['exact']+=int(g==p)
    return d

def pct(a,b):return 100*a/b if b else 0.0

model=HybridE5Classifier(MODEL);rows=[]
for cid,text,er,ew,cat in CASES:
    r=model.analyze(text)
    rows.append({'id':cid,'text':text,'category':cat,'expected_response':er,'expected_world':ew,'response':r['response'],'world':r['world'],'scores':r['scores'],'null':r['null'],'evidence':r['evidence']})
s=metrics(rows)
lines=['# BookEater hybrid E5 v2 blind check','',
       'Rules were frozen before these records were run. After reading this report, this set becomes diagnostic and must not be reused as a blind claim for v3.','',
       '|metric|result|','|---|---:|',
       f"|response Top-1|{pct(s['r_top1'],s['r_present']):.1f}%|",f"|response NULL|{pct(s['r_null_ok'],s['r_null']):.1f}%|",
       f"|world Top-1|{pct(s['w_top1'],s['w_present']):.1f}%|",f"|world NULL|{pct(s['w_null_ok'],s['w_null']):.1f}%|",
       f"|label recall|{pct(s['hit'],s['gold']):.1f}%|",f"|label precision|{pct(s['hit'],s['pred']):.1f}%|",f"|exact records|{pct(s['exact'],len(rows)):.1f}%|",'',
       '## Random/sample-by-category inspection','']
for cat in sorted(set(x[-1] for x in CASES)):
    lines.append(f'### {cat}')
    for r in [x for x in rows if x['category']==cat][:2]:
        lines += [f"- **{r['id']}** {r['text']}",f"  - gold R={r['expected_response'] or ['NULL']} W={r['expected_world'] or ['NULL']}",f"  - pred R={r['response'] or ['NULL']} W={r['world'] or ['NULL']}"]
lines += ['','## Unexpected-error watchlist','']
for r in rows:
    g=set(('r',x) for x in r['expected_response'])|set(('w',x) for x in r['expected_world']);p=set(('r',x) for x in r['response'])|set(('w',x) for x in r['world'])
    if g!=p:
        miss=sorted(f'{a}:{b}' for a,b in g-p);extra=sorted(f'{a}:{b}' for a,b in p-g)
        lines.append(f"- {r['id']} [{r['category']}] missing={miss or '-'} extra={extra or '-'} :: {r['text']}")
OUT.parent.mkdir(exist_ok=True);OUT.write_text('\n'.join(lines),encoding='utf-8');JSON_OUT.write_text(json.dumps({'stats':s,'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
print('\n'.join(lines))
