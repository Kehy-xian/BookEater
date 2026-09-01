from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bookeater.nlp.hybrid_classifier_v3 import HybridE5ClassifierV3

MODEL=ROOT/'resources/models/multilingual-e5-small-onnx'
OUT=ROOT/'tests/e5_v3_calibration_seen.md'

# Every case below is already inspected diagnostic material. This file is for tuning only, never a blind claim.
CASES=[
('c01','좋은 의도로 한 행동이라도 상대에게 상처가 되면 책임이 없는 건지 생각했다.',['사유','감정'],[]),
('c02','학교가 학생의 머리 길이까지 정하는 장면을 보며 규칙의 범위가 어디까지여야 하는지 궁금했다.',['사유'],['사회']),
('c03','아르바이트생에게만 휴게시간을 제대로 주지 않는 가게 이야기가 화가 났다.',['감정'],['사회']),
('c04','지역마다 병원 수가 다른 이유를 인구 자료와 함께 더 찾아보고 싶었다.',['탐구'],['사회']),
('c05','재개발 뒤 같은 동네에 살던 사람들이 임대료 때문에 떠나야 하는 과정이 씁쓸했다.',['감정','사유'],['사회','어둠']),
('c06','선거 결과보다 누가 투표소에 가기 어려운 조건에 놓이는지가 더 눈에 들어왔다.',['사유'],['사회']),
('c07','회사 규정은 모두에게 같지만 육아 중인 사람에게 훨씬 불리하게 작동하는 것 같았다.',['사유','감정'],['사회']),
('c08','달의 뒷면에 거대한 도서관이 숨어 있다는 설정만으로 계속 읽고 싶어졌다.',['감정'],['상상']),
('c09','사람의 기억을 다른 몸에 옮길 수 있다면 그 사람이 여전히 같은 사람인지 생각하게 됐다.',['사유'],['상상']),
('c10','모든 꿈이 중앙 서버에 저장되는 도시에서 삭제 권한을 가진 사람만 특권층이 되는 설정이 무서웠다.',['사유','감정'],['상상','사회','어둠']),
('c11','산양이 절벽을 오르는 장면을 보고 발굽 구조가 어떻게 버티는지 찾아봤다.',['탐구'],['자연']),
('c12','봄이 늦어지자 꽃 피는 시기와 곤충의 활동 시기가 어긋난다는 설명이 인상적이었다.',['탐구'],['자연']),
('c13','비 냄새와 젖은 나무껍질의 질감을 묘사한 부분이 실제 숲처럼 느껴졌다.',['감각'],['자연']),
('c14','누구도 비명을 지르지 않는데 복도 끝의 빈 신발만 반복해서 나와 더 무서웠다.',['감각','감정'],['어둠']),
('c15','주인공의 이름이 대화에서 조금씩 사라지다가 마지막에는 번호로만 불리는 과정이 섬뜩했다.',['감정','사유'],['사회','어둠']),
('c16','밝은 음악이 흐르는 동안 화면 밖에서 폭력이 일어나는 듯한 묘사가 오히려 더 불편했다.',['감각','감정'],['어둠']),
('c17','감염된 사람을 보호한다는 명목으로 가족과 연락하지 못하게 하는 규칙이 무서웠다.',['사유','감정'],['사회','어둠']),
('c18','별자리 관측 기록을 이용해 옛 항해자의 실제 이동 경로를 확인해보고 싶었다.',['탐구'],['모험']),
('c19','미래 인구 감소를 예측한 통계 보고서를 읽고 지역별 자료도 더 찾아봤다.',['탐구'],['사회']),
('c20','어두운 초록색 표지와 거친 종이 질감이 책 분위기와 잘 어울렸다.',['감각'],[]),
('c21','동물처럼 빠르게 움직인다는 비유가 많지만 실제 내용은 주식 거래 전략을 설명하는 책이었다.',['감각'],[]),
('c22','폭풍 같은 박수라는 표현이 공연장의 열기를 잘 살렸다.',['감각','감정'],[]),
('c23','자연스럽게 웃는 법을 연습하라는 자기계발서의 조언은 오히려 어색하게 느껴졌다.',['감정','사유'],[]),
('c24','가난한 구역만 정전이 반복되는 미래 도시에서 전기를 배급하는 회사가 권력을 갖는 설정이 현실적으로 무서웠다.',['사유','감정'],['상상','사회','어둠']),
('c25','거대한 산불을 피해 다른 도시로 이동하는 가족의 여정에서 재난보다 서로를 챙기는 모습이 더 마음에 남았다.',['감정'],['모험','자연','어둠']),
('c26','왕이 세금을 걷어 마법을 쓸 수 있는 사람에게만 교육을 제공하는 세계가 불공평하게 느껴졌다.',['감정','사유'],['상상','사회']),
('c27','해수면 상승으로 섬을 떠나는 주민들의 이야기를 읽고 실제 이주 사례가 있는지 찾아봤다.',['탐구','감정'],['모험','자연','사회']),
('c28','친구가 떠난 뒤 방 안의 시계 소리만 커졌다는 문장이 외로움을 직접 말하지 않아도 마음에 남았다.',['감각','감정'],['어둠']),
('c29','모두가 칭찬하는 주인공에게만 의자가 없는 장면이 집단의 배제를 보여주는 것 같았다.',['사유','감정'],['사회','어둠']),
('c30','미래 노동시장을 예측한 보고서라서 소설 같은 상상보다 근거가 얼마나 탄탄한지가 궁금했다.',['탐구'],['사회']),
]

def metrics(rows):
    gold=hit=pred=exact=0;rn=rno=wn=wno=0
    for r in rows:
        g=set(('r',x) for x in r['er'])|set(('w',x) for x in r['ew']);p=set(('r',x) for x in r['pr'])|set(('w',x) for x in r['pw'])
        gold+=len(g);hit+=len(g&p);pred+=len(p);exact+=g==p
        if not r['er']:rn+=1;rno+=not r['pr']
        if not r['ew']:wn+=1;wno+=not r['pw']
    return {'recall':hit/gold if gold else 0,'precision':hit/pred if pred else 0,'exact':exact/len(rows),'r_null':rno/rn if rn else 1,'w_null':wno/wn if wn else 1}

m=HybridE5ClassifierV3(MODEL);rows=[]
for cid,text,er,ew in CASES:
    p=m.analyze(text);rows.append({'id':cid,'text':text,'er':er,'ew':ew,'pr':p['response'],'pw':p['world']})
s=metrics(rows)
lines=['# E5 hybrid v3 calibration (seen diagnostic cases)','',f"- label recall: {s['recall']*100:.1f}%",f"- label precision: {s['precision']*100:.1f}%",f"- exact records: {s['exact']*100:.1f}%",f"- response NULL: {s['r_null']*100:.1f}%",f"- world NULL: {s['w_null']*100:.1f}%",'','## Mismatches']
for r in rows:
    g=set(('r',x) for x in r['er'])|set(('w',x) for x in r['ew']);p=set(('r',x) for x in r['pr'])|set(('w',x) for x in r['pw'])
    if g!=p:lines.append(f"- {r['id']} gold R={r['er'] or ['NULL']} W={r['ew'] or ['NULL']} / pred R={r['pr'] or ['NULL']} W={r['pw'] or ['NULL']} :: {r['text']}")
OUT.parent.mkdir(exist_ok=True);OUT.write_text('\n'.join(lines),encoding='utf-8');print('\n'.join(lines))
