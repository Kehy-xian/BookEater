from __future__ import annotations
import json, re
from pathlib import Path
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'resources/models/multilingual-e5-small-onnx'
OUT = ROOT / 'tests/e5_hybrid_holdout_report.md'
JSON_OUT = ROOT / 'tests/e5_hybrid_holdout_results.json'

RESPONSE = ['사유','탐구','감정','감각']
WORLD = ['상상','모험','자연','사회','어둠']

# Prototype bank is intentionally fixed before the held-out run.
PROT = {
'사유':['옳고 그름과 가치의 의미를 생각하게 되었다','내가 같은 상황이라면 어떤 선택을 했을지 고민했다','당연하게 믿던 기준을 다시 생각하게 했다','자유와 책임이 무엇인지 질문하게 되었다','서로 충돌하는 가치 중 무엇을 택해야 할지 쉽게 답하기 어려웠다'],
'탐구':['왜 그런 결과가 나오는지 원리를 더 찾아보고 싶었다','실제 자료와 통계를 확인해보고 싶었다','역사적 배경을 더 조사했다','과정과 원인이 궁금해서 정보를 찾아봤다','주장의 근거를 다른 자료와 비교해 확인했다'],
'감정':['인물의 외로움과 상처가 마음에 남았다','가족 사이의 감정 변화가 슬펐다','내 경험이 떠올라 공감했다','사람들 속에서도 혼자인 느낌이 안타까웠다','인물이 받는 부당한 대우를 보며 화가 났다'],
'감각':['문장의 리듬과 소리가 아름다웠다','색과 빛의 묘사가 그림처럼 남았다','비유와 이미지가 인상적이었다','뜻보다 문체와 표현 방식이 좋았다','냄새와 온도까지 느껴지는 듯한 묘사가 기억에 남았다'],
'상상':['현실에 없는 세계와 마법적 설정이 흥미로웠다','다른 행성과 미래 세계를 상상하게 했다','신화적 존재와 비현실적 세계관이 좋았다','불가능한 설정인데 그 세계에서 살아보고 싶었다','시간여행과 가상 세계 같은 허구적 설정이 재미있었다'],
'모험':['낯선 곳으로 떠나는 여행과 탐험이 좋았다','항해하며 새로운 장소에 도착하는 과정이 재미있었다','길 위에서 벌어지는 사건과 도전이 흥미로웠다','여행자가 국경과 도시를 지나 이동하는 과정이 기억에 남았다','목적지를 향해 위험을 감수하며 떠나는 여정이 흥미로웠다'],
'자연':['숲과 바다와 계절의 변화가 오래 남았다','동물과 식물의 생태가 인상적이었다','기후와 환경 문제를 생각하게 했다','자연의 냄새와 바람을 느끼는 장면이 좋았다','철새와 야생동물의 이동과 생태를 다룬 부분이 흥미로웠다'],
'사회':['법과 제도가 누구에게 유리한지 생각했다','노동과 계급과 불평등의 구조가 드러났다','정치와 경제가 사람들의 삶에 미치는 영향이 보였다','집단의 규칙과 권력 구조가 인상적이었다','교육과 복지와 차별 같은 사회 제도가 개인에게 미치는 영향이 보였다'],
'어둠':['죽음과 상실과 공포가 강하게 남았다','감시와 억압이 당연해지는 세계가 무서웠다','사람이 집단 밖으로 밀려나는 소외가 섬뜩했다','붕괴와 폭력과 불안이 지배하는 장면이었다','아무도 직접 공격하지 않지만 한 사람이 서서히 지워지는 듯한 고립이 무서웠다'],
}
NULL = {
'response':['오늘 삼십 페이지까지 읽었다','책을 가방에 넣고 집에 왔다','이 책은 총 오백 쪽이다','주말에 두 장을 읽었다','도서관에서 빌린 뒤 반납일을 달력에 적었다'],
'world':['커피 원두의 맛을 비교해보고 싶었다','축구 전술 변화가 궁금했다','기도와 신앙에 대해 생각했다','전시장의 공간 구성이 인상적이었다','뜨개질 방법을 따라해보고 싶었다','번역 표현을 비교했다','요리 과정과 악기 연주법을 설명하는 책이었다']
}

# Completely new records: do not tune the lexical evidence or thresholds after looking at their result.
CASES = [
('h01','오늘은 42쪽까지 읽고 책갈피를 꽂아 두었다.',[],[],'null'),
('h02','출판사가 바뀐 판본이라 페이지 수가 이전 책과 달랐다.',[],[],'null'),
('h03','대출 연장을 하고 다음 주까지 읽기로 했다.',[],[],'null'),
('h04','등장인물 이름이 많아서 메모장에 적어 두었다.',[],[],'null'),
('h05','레시피의 물 비율을 바꿔 직접 만들어 보고 차이를 비교하고 싶었다.',['탐구'],[],'out-grid'),
('h06','기타 코드 진행이 왜 이렇게 들리는지 다른 연주도 찾아 들어봤다.',['탐구'],[],'out-grid'),
('h07','기도를 반복하는 장면을 보며 믿음이 사람을 버티게 하는 방식에 대해 생각했다.',['사유'],[],'out-grid'),
('h08','번역본마다 같은 문장을 다르게 옮긴 부분을 나란히 비교해 보고 싶다.',['탐구','감각'],[],'out-grid'),
('h09','뜨개질 무늬가 반복되면서 만들어지는 규칙이 신기해서 직접 따라 해봤다.',['탐구'],[],'out-grid'),
('h10','건물 안의 빈 공간과 빛이 사람의 움직임을 바꾸는 방식이 인상적이었다.',['감각'],[],'out-grid'),
('h11','사람들 사이에 앉아 있지만 주인공 주변만 소리가 사라진 방처럼 느껴졌다.',['감정'],['어둠'],'metaphor'),
('h12','아무도 등을 돌리지 않았는데 대화가 이어질수록 한 사람이 투명해지는 것 같아 불편했다.',['감정'],['어둠'],'metaphor'),
('h13','마을 전체가 웃고 있는데 웃음소리가 경보음처럼 들리는 장면이 섬뜩했다.',['감각','감정'],['사회','어둠'],'metaphor'),
('h14','가족의 식탁이 점점 좁아지는 것처럼 묘사돼 관계가 무너지는 느낌이 들었다.',['감각','감정'],['어둠'],'metaphor'),
('h15','문장이 자꾸 숨을 참는 것처럼 짧게 끊겨서 인물의 불안이 더 가까이 느껴졌다.',['감각','감정'],['어둠'],'metaphor'),
('h16','도시는 번쩍이는데 사람들은 모두 같은 회색 얼굴을 하고 있는 것처럼 느껴졌다.',['감각','사유'],['사회','어둠'],'metaphor'),
('h17','아이들이 같은 시험 점수로 줄 세워지는 장면에서 교육이 누구를 위해 존재하는지 생각했다.',['사유'],['사회'],'social'),
('h18','공장 사고 뒤에도 생산량 이야기만 하는 회사의 태도에 화가 났다.',['감정'],['사회','어둠'],'social'),
('h19','임금 격차 수치가 실제 생활비와 얼마나 연결되는지 다른 통계도 확인해보고 싶었다.',['탐구'],['사회'],'social'),
('h20','법정에서는 같은 규칙을 말하지만 변호사를 살 수 있는 사람과 없는 사람의 차이가 크게 보였다.',['사유'],['사회'],'social'),
('h21','세금을 더 걷는 대신 모두에게 의료를 제공하는 선택의 장단점을 쉽게 판단하기 어려웠다.',['사유'],['사회'],'social'),
('h22','난민을 숫자로만 설명한 기사와 한 가족의 이야기를 함께 보니 통계가 다르게 느껴졌다.',['감정','사유'],['사회'],'social'),
('h23','AI가 일자리를 바꿀 것이라는 전망을 읽고 직업별 고용 통계를 더 찾아봤다.',['탐구'],['사회'],'confound'),
('h24','미래 노동시장을 예측한 보고서라서 소설 같은 상상보다 근거가 얼마나 탄탄한지가 궁금했다.',['탐구'],['사회'],'confound'),
('h25','철새가 어느 습지를 거쳐 이동하는지 지도를 펴 놓고 경로를 따라가 봤다.',['탐구'],['자연'],'confound'),
('h26','고래가 먹이를 찾아 수천 킬로미터 이동한다는 설명을 보고 실제 이동 자료를 검색했다.',['탐구'],['자연'],'confound'),
('h27','짙고 어두운 파란색을 반복해서 쓰는 삽화가 차분해서 좋았다.',['감각'],[],'confound'),
('h28','폭발적인 리듬과 거친 문장이 인물의 흥분을 잘 보여줬다.',['감각','감정'],[],'confound'),
('h29','설명이 자연스럽게 이어져 복잡한 개념인데도 읽기 편했다.',['감각'],[],'confound'),
('h30','사회라는 단어는 한 번도 나오지 않지만 집을 가진 사람과 세입자가 같은 재난을 다르게 겪는 점이 인상적이었다.',['사유'],['사회'],'confound'),
('h31','마법사가 기억을 병에 담아 거래하는 시장 설정이 기묘하고 재미있었다.',['감정'],['상상'],'imagination'),
('h32','죽은 사람의 꿈에 들어갈 수 있다는 설정 때문에 기억과 정체성이 무엇인지 생각하게 됐다.',['사유'],['상상','어둠'],'imagination'),
('h33','화성의 지하도시에서 산소를 가진 계층이 권력을 독점하는 설정이 섬뜩했다.',['감정','사유'],['상상','사회','어둠'],'multi'),
('h34','시간을 거꾸로 걷는 여행자가 매번 다른 시대의 전쟁을 목격하는 구조가 흥미로웠다.',['감정'],['상상','모험','어둠'],'multi'),
('h35','용과 싸우러 떠나는 이야기보다 길에서 만난 낯선 공동체의 규칙이 더 기억에 남았다.',['사유'],['상상','모험','사회'],'multi'),
('h36','바닷물이 차오른 미래 도시에서 부유한 사람들만 높은 구역으로 이주하는 설정이 현실처럼 느껴졌다.',['사유','감정'],['상상','자연','사회','어둠'],'multi'),
('h37','산불 뒤 숲이 회복되는 과정을 읽고 어떤 식물이 먼저 돌아오는지 더 찾아봤다.',['탐구'],['자연','어둠'],'nature'),
('h38','강을 막은 댐이 물고기뿐 아니라 주변 마을의 생계까지 바꿨다는 부분이 복잡하게 느껴졌다.',['사유'],['자연','사회'],'multi'),
('h39','멸종위기 동물을 보호하려면 관광객 수를 제한해야 한다는 주장에 어느 정도가 적절한지 고민했다.',['사유'],['자연','사회'],'multi'),
('h40','비가 오기 전 흙냄새를 묘사한 문장을 읽으니 장면이 바로 떠올랐다.',['감각'],['자연'],'nature'),
('h41','낯선 도시의 골목을 헤매며 목적지 없이 걷는 장면이 이상하게 편안했다.',['감정'],['모험'],'adventure'),
('h42','배가 폭풍을 피해 항로를 바꾸는 과정에서 선원들의 판단이 긴장감 있게 느껴졌다.',['감정'],['모험','자연','어둠'],'multi'),
('h43','국경을 넘는 기차 여행이지만 여권에 따라 검문 시간이 달라지는 장면이 더 눈에 들어왔다.',['사유'],['모험','사회'],'multi'),
('h44','산길을 오르는 장면보다 정상에 도착하지 못하고 돌아서는 선택이 더 오래 남았다.',['사유','감정'],['모험'],'adventure'),
('h45','주인공이 친구의 성공을 축하하면서도 질투하는 마음이 너무 솔직해서 공감됐다.',['감정'],[],'response-only'),
('h46','결말에서 누구도 벌을 받지 않는다는 점이 공정한 결말인지 계속 생각하게 됐다.',['사유'],[],'response-only'),
('h47','같은 사건을 세 화자가 다르게 설명해서 어느 쪽이 사실인지 앞부분을 다시 확인했다.',['탐구'],[],'response-only'),
('h48','쉼표가 거의 없는 긴 문장 때문에 숨이 차는 느낌이 들어 소리 내 읽어봤다.',['감각'],[],'response-only'),
('h49','숫자만 적힌 표를 보다가 원자료가 어떤 방식으로 수집됐는지 찾아봤다.',['탐구'],[],'response-only'),
('h50','주인공의 선택이 답답했지만 나도 같은 압박을 받았다면 달랐을지 자신이 없었다.',['사유','감정'],[],'response-only'),
('h51','권력을 가진 인물이 직접 위협하지 않고 규칙을 조금씩 바꾸는 방식이 더 무서웠다.',['사유','감정'],['사회','어둠'],'multi'),
('h52','사람들이 굶고 있는데 광고 화면만 화려하게 빛나는 장면의 대비가 강하게 남았다.',['감각','감정'],['사회','어둠'],'multi'),
('h53','전염병이 퍼진 도시에서 가난한 구역만 통행이 막히는 설정이 불공평하게 느껴졌다.',['감정','사유'],['사회','어둠'],'multi'),
('h54','전쟁 장면 자체보다 전쟁이 끝난 뒤에도 아이들이 소리에 놀라는 모습이 더 아팠다.',['감정'],['어둠'],'dark'),
('h55','아무 일도 일어나지 않는데 매일 한 사람씩 이름이 명단에서 사라지는 장면이 무서웠다.',['감정'],['사회','어둠'],'dark'),
('h56','죽음을 직접 묘사하지 않고 빈 의자만 계속 보여주는 방식이 더 슬펐다.',['감각','감정'],['어둠'],'metaphor'),
('h57','유명 관광지를 소개하는 정보책이라 이동 동선과 교통편을 실제 여행 계획에 써보고 싶었다.',['탐구'],['모험'],'adventure'),
('h58','고대 항해 기록의 날짜와 별자리 관측이 실제 경로와 맞는지 찾아보고 싶었다.',['탐구'],['모험'],'adventure'),
('h59','경제 성장률이 높아졌는데도 등장인물의 삶이 나아지지 않는 이유가 궁금했다.',['사유','탐구'],['사회'],'social'),
('h60','한 문장을 여러 번 고쳐 쓴 흔적을 보니 작가가 단어 하나의 소리까지 얼마나 고민했는지 느껴졌다.',['감각','사유'],[],'response-only'),
]

LEX = {
'사유':[r'생각',r'고민',r'판단',r'공정',r'옳',r'의미',r'선택',r'책임',r'왜 .*존재',r'장단점',r'어려웠',r'자신이 없'],
'탐구':[r'찾아',r'검색',r'확인',r'조사',r'통계',r'자료',r'원자료',r'원리',r'비교',r'수집',r'경로를 따라'],
'감정':[r'공감',r'마음',r'슬프',r'화가',r'괴로',r'불편',r'아팠',r'편안',r'질투',r'불공평하게 느',r'무서웠',r'섬뜩',r'긴장감'],
'감각':[r'문장',r'리듬',r'소리',r'색',r'빛',r'묘사',r'비유',r'삽화',r'쉼표',r'소리 내',r'냄새',r'대비',r'표현'],
'상상':[r'마법',r'화성',r'시간을 거꾸로',r'용과',r'미래 도시',r'꿈에 들어',r'기억을 병',r'지하도시'],
'모험':[r'여행',r'항해',r'항로',r'낯선 도시',r'골목',r'국경을 넘',r'산길',r'정상',r'관광지',r'교통편'],
'자연':[r'철새',r'고래',r'습지',r'산불',r'숲',r'식물',r'강을',r'댐',r'물고기',r'멸종위기',r'비가 오기 전',r'흙냄새',r'폭풍',r'바닷물'],
'사회':[r'교육',r'시험 점수',r'공장',r'회사',r'임금',r'법정',r'변호사',r'세금',r'의료',r'난민',r'AI가 일자리',r'노동시장',r'고용',r'세입자',r'계층',r'권력',r'공동체의 규칙',r'부유한',r'마을의 생계',r'관광객 수를 제한',r'여권',r'검문',r'가난한',r'통행이 막',r'경제 성장률',r'규칙을 .*바꾸'],
'어둠':[r'죽',r'전쟁',r'폭풍',r'산불',r'전염병',r'굶',r'위협',r'사라지',r'지워지',r'투명해',r'무서',r'섬뜩',r'불안',r'고립',r'상처',r'무너지',r'통행이 막'],
}

NONFICTION_FUTURE = [r'보고서',r'통계',r'전망',r'예측',r'고용',r'노동시장',r'기술']
VISUAL_DARK = [r'어두운 .*색',r'어두운 파란',r'색조']
NATURE_MIGRATION = [r'철새',r'고래',r'습지',r'생태',r'야생',r'멸종']


def agg(xs):
    xs = sorted(xs, reverse=True)[:3]
    if not xs: return 0.0
    if len(xs) == 1: return xs[0]
    return .7 * xs[0] + .3 * sum(xs[1:]) / len(xs[1:])

class E5:
    def __init__(self):
        self.tok = Tokenizer.from_file(str(MODEL/'tokenizer.json'))
        self.tok.enable_truncation(max_length=512)
        self.sess = ort.InferenceSession(str(MODEL/'model.onnx'), providers=['CPUExecutionProvider'])
        self.names = {x.name for x in self.sess.get_inputs()}
        self.p = {k:self.enc(['passage: '+x for x in v]) for k,v in PROT.items()}
        self.n = {k:self.enc(['passage: '+x for x in v]) for k,v in NULL.items()}
    def enc(self, texts):
        es = self.tok.encode_batch(texts); ml=max(len(e.ids) for e in es); pad=self.tok.token_to_id('<pad>') or 1
        ids=np.array([e.ids+[pad]*(ml-len(e.ids)) for e in es],dtype=np.int64)
        mask=np.array([[1]*len(e.ids)+[0]*(ml-len(e.ids)) for e in es],dtype=np.int64)
        feed={'input_ids':ids,'attention_mask':mask}
        if 'token_type_ids' in self.names: feed['token_type_ids']=np.zeros_like(ids)
        feed={k:v for k,v in feed.items() if k in self.names}
        h=self.sess.run(None,feed)[0]; m=mask[...,None].astype(np.float32)
        z=(h*m).sum(1)/np.clip(m.sum(1),1e-9,None); z=z/np.clip(np.linalg.norm(z,axis=1,keepdims=True),1e-12,None)
        return z
    def raw(self,text):
        q=self.enc(['query: '+text])[0]
        return {k:agg([float(np.dot(q,v)) for v in bank]) for k,bank in self.p.items()}, {g:agg([float(np.dot(q,v)) for v in bank]) for g,bank in self.n.items()}


def hits(text, trait):
    return sum(bool(re.search(p,text)) for p in LEX[trait])

def evidence_adjust(text, raw):
    out=dict(raw); hs={t:hits(text,t) for t in RESPONSE+WORLD}
    for t,h in hs.items():
        if h: out[t] += min(0.055, 0.020 + 0.015*(h-1))
    # Do not interpret nonfiction discussion of the future as fictional imagination merely because it says 'future'.
    if any(re.search(p,text) for p in NONFICTION_FUTURE) and hs['상상']==0:
        out['상상'] -= 0.045
    # A map/route used for animal migration is natural inquiry unless real travel evidence exists.
    if any(re.search(p,text) for p in NATURE_MIGRATION) and hs['모험']==0:
        out['모험'] -= 0.045
        out['자연'] += 0.020
    # 'dark colour' is sensory, not a dark-world signal.
    if any(re.search(p,text) for p in VISUAL_DARK):
        out['어둠'] -= 0.060
        out['감각'] += 0.020
    return out, hs

def classify(raw, null, text, group, hybrid=False):
    traits = RESPONSE if group=='response' else WORLD
    scores, hs = evidence_adjust(text,raw) if hybrid else (dict(raw), {t:0 for t in RESPONSE+WORLD})
    vals=sorted([(scores[t],t) for t in traits],reverse=True); top=vals[0][0]; n=null[group]
    # conservative abstention: lexical evidence may rescue a borderline semantic score, never a very weak one
    strong=max(hs[t] for t in traits) if hybrid else 0
    threshold=0.70
    if top < threshold or top-n < 0.015:
        if not (hybrid and strong>=1 and top>=0.665 and top-n>=-0.005): return []
    gap=0.040 if group=='response' else 0.045
    floor=max(n+0.010, top-gap)
    selected=[t for v,t in vals if v>=floor]
    if hybrid:
        # Keep evidence-backed secondary labels that sit just outside the semantic band.
        for v,t in vals:
            if t not in selected and hs[t]>=1 and v>=max(0.665,n-0.005,top-0.080): selected.append(t)
    limit=2 if group=='response' else 4
    return selected[:limit]

def eval_rows(rows):
    stats={'r_present':0,'r_top1':0,'r_null':0,'r_null_ok':0,'w_present':0,'w_top1':0,'w_null':0,'w_null_ok':0,'gold':0,'hit':0,'pred':0,'exact':0}
    bycat={}
    for row in rows:
        er=row['expected_response']; ew=row['expected_world']; pr=row['response']; pw=row['world']; cat=row['category']
        if er: stats['r_present']+=1; stats['r_top1']+=int(bool(pr) and pr[0] in er)
        else: stats['r_null']+=1; stats['r_null_ok']+=int(not pr)
        if ew: stats['w_present']+=1; stats['w_top1']+=int(bool(pw) and pw[0] in ew)
        else: stats['w_null']+=1; stats['w_null_ok']+=int(not pw)
        gold=set(('r',x) for x in er)|set(('w',x) for x in ew); pred=set(('r',x) for x in pr)|set(('w',x) for x in pw)
        stats['gold']+=len(gold); stats['hit']+=len(gold&pred); stats['pred']+=len(pred); stats['exact']+=int(gold==pred)
        d=bycat.setdefault(cat,{'n':0,'exact':0,'gold':0,'hit':0,'pred':0}); d['n']+=1; d['exact']+=int(gold==pred); d['gold']+=len(gold); d['hit']+=len(gold&pred); d['pred']+=len(pred)
    return stats,bycat

def pct(a,b): return 100*a/b if b else 0

e5=E5(); result={}
for mode in ('e5','hybrid'):
    rows=[]
    for cid,text,er,ew,cat in CASES:
        raw,null=e5.raw(text)
        rows.append({'id':cid,'text':text,'category':cat,'expected_response':er,'expected_world':ew,
                     'response':classify(raw,null,text,'response',mode=='hybrid'),
                     'world':classify(raw,null,text,'world',mode=='hybrid'),
                     'raw':raw,'null':null})
    st,bc=eval_rows(rows); result[mode]={'rows':rows,'stats':st,'by_category':bc}

lines=['# BookEater E5 hybrid held-out validation','',
       'This set was written and labeled before its first run. Do not tune on it after inspecting results; future tuning must use a separate calibration set.','',
       '|mode|response Top-1|response NULL|world Top-1|world NULL|label recall|label precision|exact records|','|---|---:|---:|---:|---:|---:|---:|---:|']
for mode in ('e5','hybrid'):
    s=result[mode]['stats']
    lines.append(f"|{mode}|{pct(s['r_top1'],s['r_present']):.1f}%|{pct(s['r_null_ok'],s['r_null']):.1f}%|{pct(s['w_top1'],s['w_present']):.1f}%|{pct(s['w_null_ok'],s['w_null']):.1f}%|{pct(s['hit'],s['gold']):.1f}%|{pct(s['hit'],s['pred']):.1f}%|{pct(s['exact'],len(CASES)):.1f}%|")
lines += ['','## Category sample checks','']
for cat in sorted(set(c[-1] for c in CASES)):
    lines.append(f'### {cat}')
    subset=[(a,b) for a,b in zip(result['e5']['rows'],result['hybrid']['rows']) if a['category']==cat]
    for a,b in subset[:3]:
        lines += [f"- **{a['id']}** {a['text']}",f"  - gold: R={a['expected_response'] or ['NULL']} / W={a['expected_world'] or ['NULL']}",f"  - E5: R={a['response'] or ['NULL']} / W={a['world'] or ['NULL']}",f"  - hybrid: R={b['response'] or ['NULL']} / W={b['world'] or ['NULL']}"]
lines += ['','## Unexpected-error watchlist','']
for a,b in zip(result['e5']['rows'],result['hybrid']['rows']):
    gold=set(('r',x) for x in a['expected_response'])|set(('w',x) for x in a['expected_world']); hp=set(('r',x) for x in b['response'])|set(('w',x) for x in b['world'])
    if gold != hp:
        missing=sorted(f'{g}:{x}' for g,x in gold-hp); extra=sorted(f'{g}:{x}' for g,x in hp-gold)
        lines.append(f"- {a['id']} [{a['category']}]: missing={missing or '-'} extra={extra or '-'} :: {a['text']}")
OUT.parent.mkdir(exist_ok=True); OUT.write_text('\n'.join(lines),encoding='utf-8'); JSON_OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('\n'.join(lines))
