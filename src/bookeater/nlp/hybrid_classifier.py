from __future__ import annotations
import re
from pathlib import Path
from typing import Iterable
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

RESPONSE = ('사유','탐구','감정','감각')
WORLD = ('상상','모험','자연','사회','어둠')

PROTOTYPES = {
'사유':['옳고 그름과 가치의 의미를 생각하게 되었다','내가 같은 상황이라면 어떤 선택을 했을지 고민했다','당연하게 믿던 기준을 다시 생각하게 했다','자유와 책임이 무엇인지 질문하게 되었다','서로 충돌하는 가치 중 무엇을 택해야 할지 쉽게 답하기 어려웠다','같은 규칙이 사람에 따라 다르게 작동하는 이유가 마음에 걸렸다'],
'탐구':['왜 그런 결과가 나오는지 원리를 더 찾아보고 싶었다','실제 자료와 통계를 확인해보고 싶었다','역사적 배경을 더 조사했다','과정과 원인이 궁금해서 정보를 찾아봤다','주장의 근거를 다른 자료와 비교해 확인했다'],
'감정':['인물의 외로움과 상처가 마음에 남았다','가족 사이의 감정 변화가 슬펐다','내 경험이 떠올라 공감했다','사람들 속에서도 혼자인 느낌이 안타까웠다','인물이 받는 부당한 대우를 보며 화가 났다','기묘하거나 재미있는 장면에 감정적으로 끌렸다'],
'감각':['문장의 리듬과 소리가 아름다웠다','색과 빛의 묘사가 그림처럼 남았다','비유와 이미지가 인상적이었다','뜻보다 문체와 표현 방식이 좋았다','냄새와 온도까지 느껴지는 듯한 묘사가 기억에 남았다','설명과 문장이 매끄럽게 이어져 읽는 느낌이 좋았다'],
'상상':['현실에 없는 세계와 마법적 설정이 흥미로웠다','다른 행성과 미래의 허구 세계를 상상하게 했다','신화적 존재와 비현실적 세계관이 좋았다','불가능한 설정인데 그 세계에서 살아보고 싶었다','시간여행과 가상 세계 같은 허구적 설정이 재미있었다'],
'모험':['낯선 곳으로 떠나는 여행과 탐험이 좋았다','항해하며 새로운 장소에 도착하는 과정이 재미있었다','길 위에서 벌어지는 사건과 도전이 흥미로웠다','여행자가 국경과 도시를 지나 이동하는 과정이 기억에 남았다','목적지를 향해 위험을 감수하며 떠나는 여정이 흥미로웠다'],
'자연':['숲과 바다와 계절의 변화가 오래 남았다','동물과 식물의 생태가 인상적이었다','기후와 환경 문제를 생각하게 했다','자연의 냄새와 바람을 느끼는 장면이 좋았다','철새와 야생동물의 이동과 생태를 다룬 부분이 흥미로웠다'],
'사회':['법과 제도가 누구에게 유리한지 생각했다','노동과 계급과 불평등의 구조가 드러났다','정치와 경제가 사람들의 삶에 미치는 영향이 보였다','집단의 규칙과 권력 구조가 인상적이었다','교육과 복지와 차별 같은 사회 제도가 개인에게 미치는 영향이 보였다','주거와 재난과 자원의 차이가 사람마다 다른 결과를 만드는 점이 보였다'],
'어둠':['죽음과 상실과 공포가 강하게 남았다','감시와 억압이 당연해지는 세계가 무서웠다','사람이 집단 밖으로 밀려나는 소외가 섬뜩했다','붕괴와 폭력과 불안이 지배하는 장면이었다','아무도 직접 공격하지 않지만 한 사람이 서서히 지워지는 듯한 고립이 무서웠다'],
}
NULL = {
'response':['오늘 삼십 페이지까지 읽었다','책을 가방에 넣고 집에 왔다','이 책은 총 오백 쪽이다','주말에 두 장을 읽었다','도서관에서 빌린 뒤 반납일을 달력에 적었다','등장인물 이름을 잊지 않으려고 메모해 두었다'],
'world':['커피 원두의 맛을 비교해보고 싶었다','축구 전술 변화가 궁금했다','기도와 신앙에 대해 생각했다','전시장의 공간 구성이 인상적이었다','뜨개질 방법을 따라해보고 싶었다','번역 표현을 비교했다','요리 과정과 악기 연주법을 설명하는 책이었다']
}

LEX = {
'사유':[r'생각',r'고민',r'판단',r'공정',r'옳',r'의미',r'선택',r'책임',r'장단점',r'자신이 없',r'누구를 위해',r'같은 규칙.*차이',r'다르게 겪',r'차이가 .*보였',r'복잡하게 느'],
'탐구':[r'찾아',r'검색',r'확인',r'조사',r'통계',r'자료',r'원자료',r'원리',r'비교',r'수집',r'경로를 따라',r'근거',r'사실인지'],
'감정':[r'공감',r'마음',r'슬프',r'화가',r'괴로',r'불편',r'아팠',r'편안',r'질투',r'불공평하게 느',r'무서웠',r'섬뜩',r'긴장감',r'재미있',r'흥미로',r'좋았다',r'놀랐'],
'감각':[r'문장',r'리듬',r'소리',r'색',r'빛',r'묘사',r'비유',r'삽화',r'쉼표',r'소리 내',r'냄새',r'대비',r'표현',r'읽기 편',r'매끄럽',r'문체'],
'상상':[r'마법',r'화성',r'시간여행',r'시간을 거꾸로',r'용(?:과|이|을)',r'미래 도시',r'꿈에 들어',r'기억을 병',r'지하도시',r'가상 세계',r'외계',r'신화적'],
'모험':[r'여행',r'항해',r'항로',r'낯선 도시',r'골목',r'국경을 넘',r'산길',r'정상',r'관광지',r'교통편',r'탐험',r'목적지'],
'자연':[r'철새',r'고래',r'습지',r'산불',r'숲',r'식물',r'강(?:을|이|의)',r'댐',r'물고기',r'멸종위기',r'흙냄새',r'폭풍',r'바닷물',r'기후',r'생태',r'야생동물',r'빙하',r'홍수'],
'사회':[r'교육',r'시험 점수',r'공장',r'회사',r'임금',r'법정',r'변호사',r'세금',r'의료',r'난민',r'일자리',r'노동시장',r'고용',r'세입자',r'계층',r'권력',r'공동체의 규칙',r'부유한',r'생계',r'관광객 수를 제한',r'여권',r'검문',r'가난한',r'통행이 막',r'경제 성장률',r'규칙을 .*바꾸',r'줄 세워',r'생산량',r'복지',r'차별',r'노동',r'계급',r'불평등',r'집을 가진',r'명단에서 사라'],
'어둠':[r'죽',r'전쟁',r'산불',r'전염병',r'굶',r'위협',r'사라지',r'지워지',r'투명해',r'무서',r'섬뜩',r'불안',r'고립',r'상처',r'무너지',r'통행이 막',r'재난',r'침수',r'홍수',r'억압',r'감시',r'폭력'],
}
NONFICTION_FUTURE=[r'보고서',r'통계',r'전망',r'예측',r'고용',r'노동시장',r'기술']
VISUAL_DARK=[r'어두운 .*색',r'어두운 파란',r'색조']
NATURE_MIGRATION=[r'철새',r'고래',r'습지',r'생태',r'야생',r'멸종']


def _agg(xs: Iterable[float]) -> float:
    v=sorted(xs,reverse=True)[:3]
    if not v:return 0.0
    if len(v)==1:return v[0]
    return .7*v[0]+.3*sum(v[1:])/len(v[1:])

class HybridE5Classifier:
    def __init__(self, model_dir: str|Path):
        model_dir=Path(model_dir)
        self.tok=Tokenizer.from_file(str(model_dir/'tokenizer.json')); self.tok.enable_truncation(max_length=512)
        self.sess=ort.InferenceSession(str(model_dir/'model.onnx'),providers=['CPUExecutionProvider'])
        self.input_names={x.name for x in self.sess.get_inputs()}
        self.prototypes={k:self._encode(['passage: '+x for x in v]) for k,v in PROTOTYPES.items()}
        self.nulls={k:self._encode(['passage: '+x for x in v]) for k,v in NULL.items()}

    def _encode(self,texts:list[str])->np.ndarray:
        es=self.tok.encode_batch(texts); ml=max(len(e.ids) for e in es); pad=self.tok.token_to_id('<pad>') or 1
        ids=np.array([e.ids+[pad]*(ml-len(e.ids)) for e in es],dtype=np.int64)
        mask=np.array([[1]*len(e.ids)+[0]*(ml-len(e.ids)) for e in es],dtype=np.int64)
        feed={'input_ids':ids,'attention_mask':mask}
        if 'token_type_ids' in self.input_names:feed['token_type_ids']=np.zeros_like(ids)
        feed={k:v for k,v in feed.items() if k in self.input_names}
        h=self.sess.run(None,feed)[0]; m=mask[...,None].astype(np.float32)
        z=(h*m).sum(1)/np.clip(m.sum(1),1e-9,None); z=z/np.clip(np.linalg.norm(z,axis=1,keepdims=True),1e-12,None)
        return z

    def _raw(self,text:str):
        q=self._encode(['query: '+text])[0]
        raw={k:_agg(float(np.dot(q,v)) for v in bank) for k,bank in self.prototypes.items()}
        null={g:_agg(float(np.dot(q,v)) for v in bank) for g,bank in self.nulls.items()}
        return raw,null

    @staticmethod
    def _hits(text:str,trait:str)->int:
        return sum(bool(re.search(p,text)) for p in LEX[trait])

    def _adjust(self,text:str,raw:dict[str,float]):
        out=dict(raw); hits={t:self._hits(text,t) for t in RESPONSE+WORLD}
        for t,h in hits.items():
            if h:out[t]+=min(.060,.020+.015*(h-1))
        if any(re.search(p,text) for p in NONFICTION_FUTURE) and hits['상상']==0:out['상상']-=.055
        if any(re.search(p,text) for p in NATURE_MIGRATION) and hits['모험']==0:
            out['모험']-=.055;out['자연']+=.020
        if any(re.search(p,text) for p in VISUAL_DARK):
            out['어둠']-=.070;out['감각']+=.020
        return out,hits

    def _classify(self,text:str,raw:dict[str,float],null:dict[str,float],group:str):
        traits=RESPONSE if group=='response' else WORLD
        scores,hits=self._adjust(text,raw); vals=sorted(((scores[t],t) for t in traits),reverse=True)
        top,top_trait=vals[0]; n=null[group]; any_evidence=max(hits[t] for t in traits)
        if group=='world' and any_evidence==0:
            if top<.750 or top-n<.045:return [],scores,hits
        elif top<.700 or top-n<.015:
            if not (any_evidence>=1 and top>=.665 and top-n>=-.005):return [],scores,hits
        selected=[top_trait]
        for v,t in vals[1:]:
            if group=='response':
                evidence_ok=hits[t]>=1 and v>=max(.665,n-.005,top-.075)
                semantic_ok=hits[t]==0 and v>=max(.720,n+.015,top-.018)
            else:
                evidence_ok=hits[t]>=1 and v>=max(.650,n-.010,top-.100)
                semantic_ok=hits[t]==0 and top-n>=.045 and v>=max(.735,n+.020,top-.018)
            if evidence_ok or semantic_ok:selected.append(t)
        return selected[:(2 if group=='response' else 4)],scores,hits

    def analyze(self,text:str)->dict:
        text=str(text or '').strip()
        if not text:return {'response':[],'world':[],'scores':{},'null':{},'evidence':{}}
        raw,null=self._raw(text)
        response,scores,hits=self._classify(text,raw,null,'response')
        world,_,_=self._classify(text,raw,null,'world')
        return {'response':response,'world':world,'scores':scores,'raw_scores':raw,'null':null,'evidence':hits}
