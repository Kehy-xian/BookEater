from __future__ import annotations
import json, math, re
from collections import Counter
from pathlib import Path
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/'resources/models/multilingual-e5-small-onnx'
OUT=ROOT/'tests/e5_targeted_windows_report.md'
JSON_OUT=ROOT/'tests/e5_targeted_windows_results.json'

RESPONSE=['사유','탐구','감정','감각']
WORLD=['상상','모험','자연','사회','어둠']
PROT={
'사유':['옳고 그름과 가치의 의미를 생각하게 되었다','내가 같은 상황이라면 어떤 선택을 했을지 고민했다','당연하게 믿던 기준을 다시 생각하게 했다','자유와 책임이 무엇인지 질문하게 되었다'],
'탐구':['왜 그런 결과가 나오는지 원리를 더 찾아보고 싶었다','실제 자료와 통계를 확인해보고 싶었다','역사적 배경을 더 조사했다','과정과 원인이 궁금해서 정보를 찾아봤다'],
'감정':['인물의 외로움과 상처가 마음에 남았다','가족 사이의 감정 변화가 슬펐다','내 경험이 떠올라 공감했다','사람들 속에서도 혼자인 느낌이 안타까웠다'],
'감각':['문장의 리듬과 소리가 아름다웠다','색과 빛의 묘사가 그림처럼 남았다','비유와 이미지가 인상적이었다','뜻보다 문체와 표현 방식이 좋았다'],
'상상':['현실에 없는 세계와 마법적 설정이 흥미로웠다','다른 행성과 미래 세계를 상상하게 했다','신화적 존재와 비현실적 세계관이 좋았다','불가능한 설정인데 그 세계에서 살아보고 싶었다'],
'모험':['낯선 곳으로 떠나는 여행과 탐험이 좋았다','항해하며 새로운 장소에 도착하는 과정이 재미있었다','길 위에서 벌어지는 사건과 도전이 흥미로웠다','지도를 따라 여행하고 싶었다'],
'자연':['숲과 바다와 계절의 변화가 오래 남았다','동물과 식물의 생태가 인상적이었다','기후와 환경 문제를 생각하게 했다','자연의 냄새와 바람을 느끼는 장면이 좋았다'],
'사회':['법과 제도가 누구에게 유리한지 생각했다','노동과 계급과 불평등의 구조가 드러났다','정치와 경제가 사람들의 삶에 미치는 영향이 보였다','집단의 규칙과 권력 구조가 인상적이었다'],
'어둠':['죽음과 상실과 공포가 강하게 남았다','감시와 억압이 당연해지는 세계가 무서웠다','사람이 집단 밖으로 밀려나는 소외가 섬뜩했다','붕괴와 폭력과 불안이 지배하는 장면이었다'],
}
NULL={
'response':['오늘 삼십 페이지까지 읽었다','책을 가방에 넣고 집에 왔다','이 책은 총 오백 쪽이다','주말에 두 장을 읽었다'],
'world':['커피 원두의 맛을 비교해보고 싶었다','축구 전술 변화가 궁금했다','기도와 신앙에 대해 생각했다','전시장의 공간 구성이 인상적이었다','뜨개질 방법을 따라해보고 싶었다','번역 표현을 비교했다']
}
CASES=[
('null-r1','오늘 30페이지까지 읽었다.',[],[]),
('null-r2','책을 빌려서 가방에 넣고 집에 왔다.',[],[]),
('null-w1','원두를 갈고 물 온도를 바꾸면 맛이 어떻게 달라지는지 직접 비교해보고 싶었다.',['탐구'],[]),
('null-w2','축구 전술이 왜 이렇게 바뀌었는지 경기 영상을 더 찾아봤다.',['탐구'],[]),
('null-w3','기도가 소원을 이루는 방법이라기보다 사람이 자기 욕망을 바라보는 방식일 수도 있겠다는 생각이 들었다.',['사유'],[]),
('metaphor-1','사람들 틈에 섞여 있는데도 주인공만 유리벽 너머에 서 있는 것처럼 느껴졌다.',['감정'],['어둠']),
('metaphor-2','모두가 같은 방향으로 걷는데 한 사람만 그림자처럼 지워지는 느낌이 무서웠다.',['감정'],['사회','어둠']),
('metaphor-3','몇 줄 안 되는 문장인데 읽고 나서 오래 멈춰 있었다. 말하지 않은 부분이 더 크게 느껴졌다.',['감각','사유'],[]),
('multi-1','모두가 감시 장치를 당연하게 받아들이는 미래 도시가 무서웠다. 안전을 위해 자유를 어디까지 포기할 수 있을까.',['사유'],['상상','사회','어둠']),
('multi-2','우주 식민지에서도 계급이 생기고 아래 구역 사람들만 위험한 일을 맡는 설정이 인상적이었다.',['사유'],['상상','사회']),
('multi-3','숲을 보호하자는 주장과 벌목으로 먹고사는 주민들의 이야기가 함께 나와 어느 한쪽만 쉽게 고르기 어려웠다.',['사유'],['자연','사회']),
('multi-4','난민 가족이 국경을 넘는 동안 계속 의심받는 장면이 괴로웠다.',['감정'],['모험','사회','어둠']),
('multi-5','구름을 생물처럼 묘사한 부분이 좋아 한동안 창밖 하늘을 계속 보게 됐다.',['감각'],['자연']),
('multi-6','현실에서는 불가능한 설정인데 이상하게 인물의 외로움은 너무 현실적이었다.',['감정'],['상상','어둠']),
('clear-1','실험이 실패한 이유를 설명하는 부분이 가장 재미있어 관련 원리를 더 찾아봤다.',['탐구'],[]),
('clear-2','가족이라고 해서 서로를 이해하는 건 아니라는 생각이 들었다. 가까울수록 상처가 깊을 수도 있겠다.',['감정','사유'],[]),
('clear-3','낯선 도시를 걷는 장면을 보면서 여행 계획을 짜고 싶어졌다.',['감정'],['모험']),
('clear-4','세상이 조금씩 무너지고 있는데 사람들은 평소처럼 출근하고 밥을 먹는 모습이 가장 섬뜩했다.',['사유'],['사회','어둠']),
('clear-5','새가 이동하는 경로를 읽다가 실제 지도를 찾아봤다. 매년 같은 곳을 찾아간다는 게 놀랍다.',['탐구'],['자연']),
('clear-6','문장의 뜻보다 소리와 리듬이 먼저 귀에 들어와 몇 문장은 입으로 읽어보고 싶었다.',['감각'],[]),
]

def agg(xs):
    xs=sorted(xs,reverse=True)[:3]
    if not xs:return 0.0
    if len(xs)==1:return xs[0]
    return .7*xs[0]+.3*sum(xs[1:])/len(xs[1:])

class E5:
    def __init__(self):
        self.tok=Tokenizer.from_file(str(MODEL/'tokenizer.json')); self.tok.enable_truncation(max_length=512)
        self.sess=ort.InferenceSession(str(MODEL/'model.onnx'),providers=['CPUExecutionProvider'])
        self.names={x.name for x in self.sess.get_inputs()}
        self.p={k:self.enc(['passage: '+x for x in v]) for k,v in PROT.items()}
        self.n={k:self.enc(['passage: '+x for x in v]) for k,v in NULL.items()}
    def enc(self,texts):
        encs=self.tok.encode_batch(texts); ml=max(len(e.ids) for e in encs); pad=self.tok.token_to_id('<pad>') or 1
        ids=np.array([e.ids+[pad]*(ml-len(e.ids)) for e in encs],dtype=np.int64)
        mask=np.array([[1]*len(e.ids)+[0]*(ml-len(e.ids)) for e in encs],dtype=np.int64)
        feeds={'input_ids':ids,'attention_mask':mask}
        if 'token_type_ids' in self.names: feeds['token_type_ids']=np.zeros_like(ids)
        feeds={k:v for k,v in feeds.items() if k in self.names}
        h=self.sess.run(None,feeds)[0]; m=mask[...,None].astype(np.float32)
        z=(h*m).sum(1)/np.clip(m.sum(1),1e-9,None); z=z/np.clip(np.linalg.norm(z,axis=1,keepdims=True),1e-12,None)
        return z
    def raw(self,text):
        q=self.enc(['query: '+text])[0]
        return {k:agg([float(np.dot(q,v)) for v in bank]) for k,bank in self.p.items()}, {g:agg([float(np.dot(q,v)) for v in bank]) for g,bank in self.n.items()}

def ngrams(s):
    s=re.sub(r'[^0-9a-zA-Z가-힣]+','',s.lower()); return Counter(g for n in (2,3,4) for i in range(max(0,len(s)-n+1)) for g in [s[i:i+n]])
def cos(a,b):
    if not a or not b:return 0.0
    dot=sum(v*b.get(k,0) for k,v in a.items()); na=math.sqrt(sum(v*v for v in a.values())); nb=math.sqrt(sum(v*v for v in b.values())); return dot/(na*nb) if na and nb else 0.0
NPROT={k:[ngrams(x) for x in v] for k,v in PROT.items()}; NNULL={k:[ngrams(x) for x in v] for k,v in NULL.items()}
def nraw(text):
    q=ngrams(text); return ({k:agg([cos(q,v) for v in bank]) for k,bank in NPROT.items()}, {g:agg([cos(q,v) for v in bank]) for g,bank in NNULL.items()})

def classify(raw,null,group,backend):
    traits=RESPONSE if group=='response' else WORLD; vals=sorted([(raw[t],t) for t in traits],reverse=True)
    top=vals[0][0]; n=null[group]; margin=top-n
    if backend=='e5':
        if margin < 0.015 or top < 0.70:return []
        floor=max(n+0.015, top-0.055)
    else:
        if margin < 0.015 or top < 0.08:return []
        floor=max(n+0.015, top*0.62)
    return [t for v,t in vals if v>=floor][:3]

def metrics(preds):
    m={'response_present':0,'response_top1':0,'response_null':0,'response_null_ok':0,'world_present':0,'world_top1':0,'world_null':0,'world_null_ok':0,'metaphor':0,'metaphor_all':0,'multi_labels':0,'multi_hit':0}
    for c,p in zip(CASES,preds):
        cid,text,er,ew=c; pr=p['response']; pw=p['world']; allok=True
        for g,e,x in [('response',er,pr),('world',ew,pw)]:
            if e:
                m[g+'_present']+=1; m[g+'_top1']+=int(bool(x) and x[0] in e)
                if not all(k in x for k in e):allok=False
            else:
                m[g+'_null']+=1; m[g+'_null_ok']+=int(not x); allok &= not x
        if cid.startswith('metaphor'):
            m['metaphor']+=1; m['metaphor_all']+=int(allok)
        if cid.startswith('multi'):
            m['multi_labels']+=len(er)+len(ew); m['multi_hit']+=sum(k in pr for k in er)+sum(k in pw for k in ew)
    return m

def pct(a,b): return 100*a/b if b else 0.0

e5=E5(); results={}
for name,fn in [('ngram',nraw),('e5',e5.raw)]:
    rows=[]
    for cid,text,er,ew in CASES:
        raw,null=fn(text); rows.append({'id':cid,'text':text,'expected_response':er,'expected_world':ew,'response':classify(raw,null,'response',name),'world':classify(raw,null,'world',name),'raw':raw,'null':null})
    results[name]={'rows':rows,'metrics':metrics(rows)}
lines=['# BookEater targeted Windows E5 validation','','Target: NULL abstention, metaphor understanding, and multilabel retention. This is a development slice, not a final accuracy claim.','']
lines+=['|backend|response Top-1|response NULL|world Top-1|world NULL|metaphor all-layer|multilabel recall|','|---|---:|---:|---:|---:|---:|---:|']
for name in ('ngram','e5'):
    m=results[name]['metrics']; lines.append(f"|{name}|{pct(m['response_top1'],m['response_present']):.1f}%|{pct(m['response_null_ok'],m['response_null']):.1f}%|{pct(m['world_top1'],m['world_present']):.1f}%|{pct(m['world_null_ok'],m['world_null']):.1f}%|{pct(m['metaphor_all'],m['metaphor']):.1f}%|{pct(m['multi_hit'],m['multi_labels']):.1f}%|")
lines+=['','## Case-by-case','']
for i,c in enumerate(CASES):
    cid,text,er,ew=c; n=results['ngram']['rows'][i]; e=results['e5']['rows'][i]
    lines += [f'### {cid}',text,'',f"- gold: response={er or ['NULL']} / world={ew or ['NULL']}",f"- ngram: response={n['response'] or ['NULL']} / world={n['world'] or ['NULL']}",f"- E5: response={e['response'] or ['NULL']} / world={e['world'] or ['NULL']}",'']
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text('\n'.join(lines),encoding='utf-8'); JSON_OUT.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(OUT); print(JSON_OUT)
