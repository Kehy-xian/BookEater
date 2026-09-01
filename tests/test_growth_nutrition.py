from bookeater.game.nutrition import project_growth_nutrition, apply_growth_nutrition


def _analysis(*, response=(), world=(), scores=None, rn=.84, wn=.84, evidence=None):
    return {
        'response':list(response),'world':list(world),
        'scores':scores or {},'null':{'response':rn,'world':wn},
        'evidence':evidence or {},
    }


def test_near_null_response_does_not_feed_growth():
    a=_analysis(response=['탐구'],scores={'탐구':.855},rn=.84)
    n=project_growth_nutrition('기록을 다시 확인했다.',a)
    assert n.response=={}


def test_strong_response_signal_feeds_primary_trait():
    a=_analysis(response=['사유'],scores={'사유':.91},rn=.84)
    n=project_growth_nutrition('결말의 선택이 옳았는지 오래 생각했다.',a)
    assert n.response=={'사유':1.0}


def test_only_primary_response_feeds_body_growth():
    a=_analysis(response=['감정','사유'],scores={'감정':.91,'사유':.90},rn=.84)
    n=project_growth_nutrition('마음이 아팠고 그 선택의 책임도 생각했다.',a)
    assert n.response=={'감정':1.0}


def test_bookkeeping_record_feeds_nothing_even_with_keyword_like_analysis():
    a=_analysis(response=['탐구'],world=['자연'],scores={'탐구':.92,'자연':.91},rn=.84,wn=.84)
    n=project_growth_nutrition('목차에서 127쪽 위치를 다시 확인했다.',a)
    assert n.is_empty


def test_weak_semantic_world_guess_is_ignored():
    a=_analysis(world=['상상'],scores={'상상':.87},wn=.84,evidence={'상상':0})
    n=project_growth_nutrition('결말이 행복하다고 말할 수 있는지 생각했다.',a)
    assert n.world=={}


def test_strong_semantic_world_signal_can_pass_without_literal_anchor():
    a=_analysis(world=['상상'],scores={'상상':.90},wn=.84,evidence={'상상':0})
    n=project_growth_nutrition('현실 법칙으로는 설명되지 않는 공간이 펼쳐졌다.',a)
    assert n.world=={'상상':1.0}


def test_metaphorical_world_keyword_does_not_mutate_creature():
    a=_analysis(world=['모험'],scores={'모험':.887},wn=.84,evidence={'모험':1})
    n=project_growth_nutrition('문제를 푸는 과정을 미로를 탐험하듯 설명한 비유가 재미있었다.',a)
    assert n.world=={}


def test_title_or_product_name_does_not_create_world_modifier():
    a=_analysis(world=['상상'],scores={'상상':.93},wn=.84,evidence={'상상':1})
    n=project_growth_nutrition('마법이라는 이름의 디저트 조리법을 비교해봤다.',a)
    assert n.world=={}


def test_strong_literal_world_signal_can_feed_growth():
    a=_analysis(world=['자연'],scores={'자연':.89},wn=.84,evidence={'자연':1})
    n=project_growth_nutrition('숲의 생태와 계절 변화를 다룬 장면이 기억에 남았다.',a)
    assert n.world=={'자연':1.0}


def test_world_is_capped_to_two_and_secondary_is_downweighted():
    a=_analysis(world=['사회','어둠','자연'],scores={'사회':.91,'어둠':.90,'자연':.89},wn=.84,evidence={'사회':1,'어둠':1,'자연':1})
    n=project_growth_nutrition('재난 지원 제도 때문에 주민들이 밀려나는 장면이 불안했다.',a)
    assert n.world=={'사회':1.0,'어둠':.65}


def test_apply_is_pure_and_accumulative():
    stats={'사유':3.0}
    n=project_growth_nutrition('질문을 오래 생각했다.',_analysis(response=['사유'],scores={'사유':.91},rn=.84))
    out=apply_growth_nutrition(stats,n)
    assert stats=={'사유':3.0}
    assert out['사유']==4.0
