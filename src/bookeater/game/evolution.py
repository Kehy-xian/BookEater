from __future__ import annotations
from dataclasses import dataclass,asdict

REACTION=('사유','탐구','감정','감각')
WORLD=('상상','모험','자연','사회','어둠')
BASE_SPECIES={
 '사유':('생각콩','질문짐승','천개의눈 서고지기'),
 '탐구':('돋보기콩','수집까마귀','만물서고지기'),
 '감정':('마음몽글','기억여우','이야기를품은달짐승'),
 '감각':('운율콩','잉크나비','시어를엮는공작'),
}
NEUTRAL=('글씨알','문장콩','기억몽','이름없는 서고지기')
WORLD_MODIFIERS={
 '상상':('꿈빛','별가루','상상'),
 '모험':('길무늬','나침반','모험'),
 '자연':('잎결','이끼뿔','자연'),
 '사회':('창문무늬','도시눈','사회'),
 '어둠':('그늘결','먹구름','어둠'),
}

@dataclass(frozen=True)
class EvolutionDecision:
    stage:int
    base_trait:str|None
    modifier_traits:tuple[str,...]
    species:str
    visual_modifiers:tuple[str,...]
    changed_base:bool=False
    reason:str=''
    def to_dict(self):return asdict(self)

def _stage(entry_count:int)->int:
    if entry_count<5:return 0
    if entry_count<15:return 1
    if entry_count<40:return 2
    return 3

def _rank(stats:dict[str,int|float],traits:tuple[str,...]):
    return sorted(((max(0.0,float(stats.get(t,0))),t) for t in traits),reverse=True)

def _choose_base(stats:dict[str,int|float],current_base:str|None)->tuple[str|None,bool,str]:
    ranked=_rank(stats,REACTION);top_score,top=ranked[0]
    if top_score<3:return current_base if current_base in REACTION else None,False,'reaction signal still sparse'
    if current_base not in REACTION:return top,True,'first stable reaction base'
    cur=max(0.0,float(stats.get(current_base,0)))
    if top==current_base:return current_base,False,'current base remains strongest'
    # Hysteresis prevents a monster from flipping body type whenever two cumulative traits are close.
    # A challenger needs both an absolute and proportional lead.
    if top_score>=cur*1.22 and top_score-cur>=4:return top,True,'challenger clearly surpassed current base'
    return current_base,False,'near-tie kept current base for identity stability'

def _choose_modifiers(stats:dict[str,int|float])->tuple[str,...]:
    ranked=_rank(stats,WORLD);top_score,top=ranked[0]
    if top_score<3:return ()
    out=[top]
    second_score,second=ranked[1]
    # A genuine mixed world/topic profile can keep a second modifier. Do not force one.
    if second_score>=4 and second_score>=top_score*.78:out.append(second)
    return tuple(out)

def resolve_evolution(stats:dict[str,int|float],entry_count:int,*,current_base:str|None=None)->EvolutionDecision:
    stage=_stage(max(0,int(entry_count)))
    base,changed,why=_choose_base(stats,current_base)
    mods=_choose_modifiers(stats)
    if stage==0:
        return EvolutionDecision(0,base,mods,'글씨알',tuple(WORLD_MODIFIERS[m][0] for m in mods),changed,why)
    if base is None:
        species=NEUTRAL[stage]
    else:
        species=BASE_SPECIES[base][stage-1]
    visuals=[]
    for m in mods:
        visuals.append(WORLD_MODIFIERS[m][min(stage-1,1)])
    return EvolutionDecision(stage,base,mods,species,tuple(visuals),changed,why)
