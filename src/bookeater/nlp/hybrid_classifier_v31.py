from __future__ import annotations
import re
from pathlib import Path
import numpy as np
from .hybrid_classifier_v3 import HybridE5ClassifierV3, RESPONSE, WORLD

MODEL_VERSION='e5-hybrid-v3.1'
EXTRA_LEX={
 '사유':[r'불공평',r'배제',r'규칙의 범위',r'불리하게 작동',r'같은 규칙'],
 '감정':[r'읽고 싶',r'어색하게 느',r'마음에 남',r'열기',r'씁쓸'],
 '감각':[r'반복해서',r'화면 밖',r'시계 소리'],
 '상상':[],
 '모험':[r'섬을 떠',r'이주',r'다른 도시로 이동'],
 '자연':[],
 '사회':[r'보호.*명목',r'연락하지 못.*규칙',r'번호로만',r'배제',r'이주 사례',r'주민.*떠나',r'특권층'],
 '어둠':[r'떠나야',r'밀려나',r'격리'],
}

class HybridE5ClassifierV31(HybridE5ClassifierV3):
    def __init__(self,model_dir:str|Path):
        super().__init__(model_dir)
        # Only already-inspected diagnostic paraphrases are used here.
        add={
          '사유':['불공평하거나 배제되는 상황에서 그 기준이 옳은지 생각했다','같은 규칙이 누구에게 더 불리한지 해석했다'],
          '감정':['기묘한 설정 때문에 다음 내용을 계속 읽고 싶어졌다','어색하고 불편하게 느껴져 감정적으로 반응했다'],
          '사회':['보호라는 명목의 규칙이 가족의 연락과 행동을 제한했다','이주와 주거 문제로 주민이 원래 살던 곳을 떠나게 됐다','이름 대신 번호로 사람을 부르는 제도가 개인을 지웠다'],
          '어둠':['살던 곳에서 밀려나거나 강제로 떠나야 하는 상실이 씁쓸했다']
        }
        for t,texts in add.items():
            new=self._encode(['passage: '+x for x in texts]);self.prototypes[t]=np.vstack([self.prototypes[t],new])
        # Abstract ethical harm is not automatically a social-world theme.
        extra_counter=self._encode(['passage: 좋은 의도와 상처와 책임의 윤리 문제를 개인 차원에서 생각했다'])
        self.counters['사회']=np.vstack([self.counters['사회'],extra_counter])

    @staticmethod
    def _hits(text:str,trait:str)->int:
        base=HybridE5ClassifierV3._hits(text,trait)
        return base+sum(bool(re.search(p,text)) for p in EXTRA_LEX.get(trait,()))

    def _classify_response(self,scores,null,hits):
        vals=sorted(((scores[t],t) for t in RESPONSE),reverse=True);top,trait=vals[0];n=null['response']
        if top<.695 or top-n<.010:
            if not (hits[trait]>=1 and top>=.660 and top-n>=-.008):return []
        selected=[trait]
        for v,t in vals[1:]:
            if hits[t]>=1 and v>=max(.660,n-.005,top-.085):selected.append(t)
            # Semantic-only second response must be nearly tied to top to prevent random 탐구/감각 additions.
            elif hits[t]==0 and v>=max(.735,n+.022,top-.010):selected.append(t)
        return selected[:2]

    def _classify_world(self,scores,null,hits,counter):
        vals=sorted(((scores[t],t) for t in WORLD),reverse=True);top,trait=vals[0];n=null['world'];margin=top-n
        evidence=hits[trait];counter_gap=top-counter[trait]
        if evidence>=1:
            present=(top>=.785 and margin>=-.018) or top>=.835
        else:
            present=(top>=.840 and margin>=.010 and counter_gap>=-.018) or (top>=.875 and margin>=.004 and counter_gap>=-.025)
        if not present:return []
        selected=[trait]
        for v,t in vals[1:]:
            m=v-n;cg=v-counter[t]
            if hits[t]>=1 and v>=.750 and m>=-.025 and v>=top-.125:selected.append(t)
            # Semantic-only world secondaries are useful but were the largest source of false 모험/상상.
            elif hits[t]==0 and v>=.855 and m>=.025 and cg>=-.015 and v>=top-.012:selected.append(t)
        return selected[:4]

    def analyze(self,text:str)->dict:
        out=super().analyze(text);out['model_version']=MODEL_VERSION;return out
