from __future__ import annotations
import re
from pathlib import Path
from typing import Iterable
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

MODEL_VERSION = 'e5-hybrid-v3'
RESPONSE = ('사유','탐구','감정','감각')
WORLD = ('상상','모험','자연','사회','어둠')

# These banks are calibrated only from already-inspected development/diagnostic examples.
# Future blind sets must never be copied into these banks before evaluation.
PROTOTYPES = {
'사유':[
 '옳고 그름과 가치의 의미를 생각하게 되었다','내가 같은 상황이라면 어떤 선택을 했을지 고민했다',
 '당연하게 믿던 기준을 다시 생각하게 했다','자유와 책임이 무엇인지 질문하게 되었다',
 '서로 충돌하는 가치 중 무엇을 택해야 할지 쉽게 답하기 어려웠다','같은 규칙이 사람에 따라 다르게 작동하는 이유가 마음에 걸렸다',
 '제도나 선택이 공정한지 판단하기 어려워 오래 생각했다','직접 말하지 않은 장면에서 관계와 권력의 의미를 해석하게 되었다'],
'탐구':[
 '왜 그런 결과가 나오는지 원리를 더 찾아보고 싶었다','실제 자료와 통계를 확인해보고 싶었다',
 '역사적 배경을 더 조사했다','과정과 원인이 궁금해서 정보를 찾아봤다','주장의 근거를 다른 자료와 비교해 확인했다',
 '설명과 수치가 맞는지 원자료를 확인했다','생물의 구조와 작동 원리를 더 알아보고 싶었다'],
'감정':[
 '인물의 외로움과 상처가 마음에 남았다','가족 사이의 감정 변화가 슬펐다','내 경험이 떠올라 공감했다',
 '사람들 속에서도 혼자인 느낌이 안타까웠다','인물이 받는 부당한 대우를 보며 화가 났다',
 '기묘하거나 재미있는 장면에 감정적으로 끌렸다','질투와 미안함처럼 모순된 마음이 이해됐다'],
'감각':[
 '문장의 리듬과 소리가 아름다웠다','색과 빛의 묘사가 그림처럼 남았다','비유와 이미지가 인상적이었다',
 '뜻보다 문체와 표현 방식이 좋았다','냄새와 온도까지 느껴지는 듯한 묘사가 기억에 남았다',
 '설명과 문장이 매끄럽게 이어져 읽는 느낌이 좋았다','번역과 말투가 달라지면서 인물 관계의 느낌도 달라졌다'],
'상상':[
 '현실에 없는 세계와 마법적 설정이 흥미로웠다','다른 행성과 미래의 허구 세계를 상상하게 했다',
 '신화적 존재와 비현실적 세계관이 좋았다','불가능한 설정인데 그 세계에서 살아보고 싶었다',
 '시간여행과 가상 세계 같은 허구적 설정이 재미있었다','달이나 우주에 현실에는 없는 도시와 시설이 존재하는 설정이 흥미로웠다',
 '기억이나 의식을 다른 몸과 공간으로 옮길 수 있다는 허구적 설정이 인상적이었다'],
'모험':[
 '낯선 곳으로 떠나는 여행과 탐험이 좋았다','항해하며 새로운 장소에 도착하는 과정이 재미있었다',
 '길 위에서 벌어지는 사건과 도전이 흥미로웠다','여행자가 국경과 도시를 지나 이동하는 과정이 기억에 남았다',
 '목적지를 향해 위험을 감수하며 떠나는 여정이 흥미로웠다','기차와 배를 갈아타며 여러 장소를 이동하는 여행 동선을 따라가고 싶었다'],
'자연':[
 '숲과 바다와 계절의 변화가 오래 남았다','동물과 식물의 생태가 인상적이었다','기후와 환경 문제를 생각하게 했다',
 '자연의 냄새와 바람을 느끼는 장면이 좋았다','철새와 야생동물의 이동과 생태를 다룬 부분이 흥미로웠다',
 '꽃이 피는 시기와 곤충의 활동처럼 계절 변화가 생태에 미치는 영향이 흥미로웠다',
 '동물의 몸 구조가 환경에 적응하는 방식을 더 알아보고 싶었다','바다 생태와 해수면 변화가 생물과 사람의 삶을 바꾸는 내용이었다'],
'사회':[
 '법과 제도가 누구에게 유리한지 생각했다','노동과 계급과 불평등의 구조가 드러났다','정치와 경제가 사람들의 삶에 미치는 영향이 보였다',
 '집단의 규칙과 권력 구조가 인상적이었다','교육과 복지와 차별 같은 사회 제도가 개인에게 미치는 영향이 보였다',
 '주거와 재난과 자원의 차이가 사람마다 다른 결과를 만드는 점이 보였다','학교 규칙이 학생의 선택과 자유를 어디까지 제한할 수 있는지 생각했다',
 '아르바이트와 직장에서 노동 조건이 사람마다 다르게 적용되는 문제가 보였다','지역에 따라 의료와 공공서비스를 이용할 기회가 달라지는 이유가 궁금했다',
 '투표와 선거 같은 제도에 접근하기 어려운 사람들의 조건이 보였다','재개발과 임대료 때문에 원래 살던 주민이 밀려나는 과정이 드러났다'],
'어둠':[
 '죽음과 상실과 공포가 강하게 남았다','감시와 억압이 당연해지는 세계가 무서웠다','사람이 집단 밖으로 밀려나는 소외가 섬뜩했다',
 '붕괴와 폭력과 불안이 지배하는 장면이었다','아무도 직접 공격하지 않지만 한 사람이 서서히 지워지는 듯한 고립이 무서웠다',
 '빈 자리와 사라진 이름처럼 직접 말하지 않은 상실의 흔적이 더 무서웠다','보호를 명분으로 사람을 격리하거나 연락을 끊게 하는 장면이 불안했다'],
}

NULL = {
'response':['오늘 삼십 페이지까지 읽었다','책을 가방에 넣고 집에 왔다','이 책은 총 오백 쪽이다','주말에 두 장을 읽었다','도서관에서 빌린 뒤 반납일을 달력에 적었다','등장인물 이름을 잊지 않으려고 메모해 두었다'],
'world':['커피 원두의 맛을 비교해보고 싶었다','축구 전술 변화가 궁금했다','기도와 신앙에 대해 생각했다','전시장의 공간 구성이 인상적이었다','뜨개질 방법을 따라해보고 싶었다','번역 표현을 비교했다','요리 과정과 악기 연주법을 설명하는 책이었다','인물의 감정과 문체만 이야기하고 특정 세계 주제는 언급하지 않았다']
}

# Trait-specific semantic counterexamples reduce literal-word traps without turning the classifier back into pure keyword matching.
COUNTER = {
'상상':['미래 인구와 고용을 예측한 통계 보고서를 읽었다','인공지능 기술 전망과 실제 산업 자료를 확인했다','현실의 과학기술 발전을 설명한 논픽션이다'],
'모험':['철새와 고래의 이동 경로를 지도에서 확인했다','데이터의 흐름과 진로 경로를 분석했다','실제 연구 자료에서 이동 경로를 추적했다'],
'자연':['폭풍 같은 박수라는 비유가 공연장의 열기를 보여줬다','자연스럽게 웃는 방법을 연습하라는 조언이었다','어두운 초록색과 파란색의 시각적 표현이 인상적이었다'],
'사회':['친구와 가족 사이의 개인적인 갈등과 감정만 다뤘다','개인의 습관과 취미를 설명할 뿐 제도나 집단 구조의 문제는 없다','문장 표현과 번역의 차이를 비교한 기록이다'],
'어둠':['상처라는 단어를 윤리적 책임의 비유로 사용했다','어두운 색채와 거친 종이 질감이 시각적으로 좋았다','폭풍 같은 소리와 강한 리듬이라는 표현이 인상적이었다'],
}

LEX = {
'사유':[r'생각',r'고민',r'판단',r'공정',r'옳',r'의미',r'선택',r'책임',r'장단점',r'자신이 없',r'누구를 위해',r'같은 규칙.*차이',r'다르게 겪',r'차이가 .*보였',r'복잡하게 느',r'어디까지'],
'탐구':[r'찾아',r'검색',r'확인',r'조사',r'통계',r'자료',r'원자료',r'원리',r'비교',r'수집',r'경로를 따라',r'근거',r'사실인지',r'왜 .*달라'],
'감정':[r'공감',r'마음',r'슬프',r'화가',r'괴로',r'불편',r'아팠',r'편안',r'질투',r'불공평하게 느',r'무서웠',r'섬뜩',r'긴장감',r'재미있',r'흥미로',r'좋았다',r'놀랐',r'이해됐다',r'씁쓸'],
'감각':[r'문장',r'리듬',r'소리',r'색',r'빛',r'묘사',r'비유',r'삽화',r'쉼표',r'소리 내',r'냄새',r'대비',r'표현',r'읽기 편',r'매끄럽',r'문체',r'번역',r'말투',r'질감'],
'상상':[r'마법',r'화성',r'달의 뒷면',r'시간여행',r'시간을 거꾸로',r'용(?:과|이|을)',r'미래 도시',r'꿈에 들어',r'기억을 .*옮',r'기억을 병',r'지하도시',r'가상 세계',r'외계',r'신화적'],
'모험':[r'여행',r'항해',r'항로',r'낯선 도시',r'골목',r'국경을 넘',r'산길',r'정상',r'관광지',r'교통편',r'탐험',r'목적지',r'기차를 갈아',r'여정'],
'자연':[r'철새',r'고래',r'습지',r'산불',r'숲',r'식물',r'꽃 피',r'곤충',r'발굽',r'산양',r'강(?:을|이|의)',r'댐',r'물고기',r'산호초',r'멸종위기',r'흙냄새',r'폭풍',r'바닷물',r'해수면',r'기후',r'생태',r'야생동물',r'빙하',r'홍수'],
'사회':[r'교육',r'학교가 .*정',r'학생',r'시험 점수',r'공장',r'회사',r'아르바이트',r'휴게시간',r'임금',r'법정',r'변호사',r'세금',r'의료',r'병원 수',r'난민',r'선거',r'투표소',r'일자리',r'노동시장',r'고용',r'재개발',r'임대료',r'세입자',r'계층',r'권력',r'공동체의 규칙',r'부유한',r'생계',r'관광객 수를 제한',r'여권',r'검문',r'가난한',r'통행이 막',r'경제 성장률',r'규칙을 .*바꾸',r'줄 세워',r'생산량',r'복지',r'차별',r'노동',r'계급',r'불평등',r'집을 가진',r'명단에서 사라'],
'어둠':[r'죽',r'전쟁',r'산불',r'전염병',r'감염',r'굶',r'위협',r'사라지',r'지워지',r'투명해',r'무서',r'섬뜩',r'불안',r'고립',r'연락하지 못',r'무너지',r'통행이 막',r'재난',r'침수',r'홍수',r'억압',r'감시',r'폭력',r'빈 신발',r'빈 의자',r'번호로만'],
}

NONFICTION_FUTURE=[r'보고서',r'통계',r'전망',r'예측',r'고용',r'노동시장',r'기술',r'자료']
VISUAL_DARK=[r'어두운 .*색',r'어두운 파란',r'어두운 초록',r'색조',r'표지.*어두']
NATURE_METAPHOR=[r'폭풍 같은 .*박수',r'폭풍 같은 .*소리',r'자연스럽게',r'파도처럼 .*감정',r'동물처럼 빠르게']
NATURE_MIGRATION=[r'철새',r'고래',r'습지',r'생태',r'야생',r'멸종',r'산양',r'발굽']


def _agg(xs: Iterable[float]) -> float:
    v=sorted(xs,reverse=True)[:3]
    if not v:return 0.0
    if len(v)==1:return v[0]
    return .7*v[0]+.3*sum(v[1:])/len(v[1:])

class HybridE5ClassifierV3:
    def __init__(self, model_dir: str|Path):
        model_dir=Path(model_dir)
        self.tok=Tokenizer.from_file(str(model_dir/'tokenizer.json')); self.tok.enable_truncation(max_length=512)
        self.sess=ort.InferenceSession(str(model_dir/'model.onnx'),providers=['CPUExecutionProvider'])
        self.input_names={x.name for x in self.sess.get_inputs()}
        self.prototypes={k:self._encode(['passage: '+x for x in v]) for k,v in PROTOTYPES.items()}
        self.nulls={k:self._encode(['passage: '+x for x in v]) for k,v in NULL.items()}
        self.counters={k:self._encode(['passage: '+x for x in v]) for k,v in COUNTER.items()}

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
        counter={k:_agg(float(np.dot(q,v)) for v in bank) for k,bank in self.counters.items()}
        return raw,null,counter

    @staticmethod
    def _hits(text:str,trait:str)->int:
        return sum(bool(re.search(p,text)) for p in LEX[trait])

    def _adjust(self,text:str,raw:dict[str,float],counter:dict[str,float]):
        out=dict(raw); hits={t:self._hits(text,t) for t in RESPONSE+WORLD}
        for t,h in hits.items():
            if h:out[t]+=min(.060,.020+.015*(h-1))
        if any(re.search(p,text) for p in NONFICTION_FUTURE) and hits['상상']==0:out['상상']-=.060
        if any(re.search(p,text) for p in NATURE_MIGRATION) and hits['모험']==0:
            out['모험']-=.050;out['자연']+=.020
        if any(re.search(p,text) for p in VISUAL_DARK):
            out['어둠']-=.075;out['감각']+=.020
        if any(re.search(p,text) for p in NATURE_METAPHOR):out['자연']-=.075
        # If a sentence is semantically closer to a known counterexample than to a world prototype,
        # apply a small penalty. This is intentionally modest: counters guard, they do not decide.
        for t in WORLD:
            c=counter[t]
            if c>raw[t]:out[t]-=min(.040,(c-raw[t])*.65+.010)
        return out,hits

    def _classify_response(self,scores,null,hits):
        vals=sorted(((scores[t],t) for t in RESPONSE),reverse=True);top,trait=vals[0];n=null['response']
        if top<.695 or top-n<.010:
            if not (hits[trait]>=1 and top>=.660 and top-n>=-.008):return []
        selected=[trait]
        for v,t in vals[1:]:
            if hits[t]>=1 and v>=max(.660,n-.005,top-.085):selected.append(t)
            elif hits[t]==0 and v>=max(.725,n+.018,top-.016):selected.append(t)
        return selected[:2]

    def _classify_world(self,scores,null,hits,counter):
        vals=sorted(((scores[t],t) for t in WORLD),reverse=True);top,trait=vals[0];n=null['world'];margin=top-n
        evidence=hits[trait]
        counter_gap=top-counter[trait]
        # Presence is primarily semantic. Lexical evidence and counterexamples move the boundary,
        # but do not act as mandatory gates.
        if evidence>=1:
            present=(top>=.790 and margin>=-.015) or (top>=.835)
        else:
            present=(top>=.840 and margin>=.010 and counter_gap>=-.018) or (top>=.875 and margin>=.004 and counter_gap>=-.025)
        if not present:return []
        selected=[trait]
        for v,t in vals[1:]:
            m=v-n;cg=v-counter[t]
            if hits[t]>=1 and v>=.760 and m>=-.020 and v>=top-.120:selected.append(t)
            elif hits[t]==0 and v>=.850 and m>=.015 and cg>=-.020 and v>=top-.028:selected.append(t)
        return selected[:4]

    def analyze(self,text:str)->dict:
        text=str(text or '').strip()
        if not text:return {'response':[],'world':[],'scores':{},'null':{},'counter':{},'evidence':{},'model_version':MODEL_VERSION}
        raw,null,counter=self._raw(text);scores,hits=self._adjust(text,raw,counter)
        return {
          'response':self._classify_response(scores,null,hits),
          'world':self._classify_world(scores,null,hits,counter),
          'scores':scores,'raw_scores':raw,'null':null,'counter':counter,'evidence':hits,'model_version':MODEL_VERSION
        }
