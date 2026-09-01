from bookeater.game.nutrition import project_growth_nutrition


def _a(*, response=(), world=(), scores=None, rn=.84, wn=.84):
    return {'response':list(response),'world':list(world),'scores':scores or {},'null':{'response':rn,'world':wn}}


def test_quoted_boardgame_card_name_does_not_create_war_darkness():
    n=project_growth_nutrition(
        '“전쟁의 신”은 보드게임 카드 이름이고 이 문단은 점수 규칙 설명이었다.',
        _a(world=['어둠'],scores={'어둠':.837},wn=.819),
    )
    assert n.world=={}


def test_quoted_activity_name_does_not_create_surveillance_darkness():
    n=project_growth_nutrition(
        '‘감시’라는 과목 활동명 아래 체크리스트 작성 방법만 설명돼 있었다.',
        _a(response=['탐구'],world=['어둠'],scores={'탐구':.86,'어둠':.847},rn=.816,wn=.832),
    )
    assert n.world=={}


def test_literal_day_restart_is_imagination_not_metaphor():
    n=project_growth_nutrition(
        '매일 자정이 되면 마을의 하루가 처음부터 다시 시작되고 한 사람만 기억을 유지한다.',
        _a(world=['사회'],scores={'상상':.845,'사회':.848},wn=.817),
    )
    assert '상상' in n.world


def test_social_lack_of_benefit_is_not_mistaken_for_topic_negation():
    n=project_growth_nutrition(
        '같은 일을 해도 고용 형태에 따라 병가를 쓸 수 없는 구조가 공정한지 생각했다.',
        _a(response=['사유'],world=['사회'],scores={'사유':.929,'사회':.893},rn=.831,wn=.846),
    )
    assert n.response=={'사유':1.0}
    assert n.world=={'사회':1.0}


def test_labor_section_with_missing_leave_still_counts_as_social_content():
    n=project_growth_nutrition(
        '목차에서 노동 파트를 찾아 읽고 계약직에게만 휴가가 없는 기준이 공정한지 고민했다.',
        _a(response=['사유'],world=['사회'],scores={'사유':.913,'사회':.885},rn=.848,wn=.851),
    )
    assert n.world=={'사회':1.0}


def test_grief_time_metaphor_does_not_add_imagination():
    n=project_growth_nutrition(
        '전쟁이 끝났는데도 실종된 가족을 기다리는 인물의 시간이 멈춘 것 같아 먹먹했다.',
        _a(response=['감정'],world=['어둠'],scores={'감정':.892,'상상':.868,'어둠':.892},rn=.861,wn=.850),
    )
    assert '상상' not in n.world
    assert '어둠' in n.world


def test_predicted_voyage_is_not_displaced_by_decorative_sea_nature():
    n=project_growth_nutrition(
        '다른 행성의 바다를 조사하려고 잠수정을 타고 미지의 해역으로 떠나는 장면이 설렜다.',
        _a(world=['모험','상상'],scores={'상상':.872,'모험':.881,'자연':.858},wn=.835),
    )
    assert set(n.world)=={'상상','모험'}


def test_memory_market_can_recover_imagination_alongside_society():
    n=project_growth_nutrition(
        '기억을 사고팔 수 있는 나라에서 부자만 과거를 지울 수 있다는 제도가 불공평하게 느껴졌다.',
        _a(world=['상상','어둠','사회'],scores={'상상':.878,'사회':.874,'어둠':.877},wn=.848),
    )
    assert set(n.world)=={'상상','사회'}


def test_explicit_surveillance_camera_can_recover_dark_even_if_embedding_margin_is_negative():
    n=project_growth_nutrition(
        '삽화의 어두운 색보다 감시 카메라 때문에 주민들이 서로를 의심하는 설정이 더 불편했다.',
        _a(world=['상상','어둠'],scores={'상상':.867,'사회':.865,'어둠':.820},wn=.844),
    )
    assert '어둠' in n.world
    assert '사회' in n.world


def test_secret_passage_can_preserve_adventure_with_darkness():
    n=project_growth_nutrition(
        '주인공이 사라진 친구를 찾다가 폐허가 된 지하 도시의 비밀 통로를 발견하는 장면이 흥미로웠다.',
        _a(response=['감정'],world=['모험','상상'],scores={'감정':.891,'모험':.885,'상상':.877,'어둠':.860},rn=.855,wn=.837),
    )
    assert '모험' in n.world
    assert '어둠' in n.world


def test_common_emotion_inflections_can_pass_small_margin():
    for text, score, rn in [
        ('둘이 아무 말 없이 식탁을 치우는 마지막 장면이 유난히 쓸쓸했다.',.869,.840),
        ('오랫동안 기다렸던 편지가 결국 도착하지 않는 장면이 너무 허전했다.',.875,.858),
    ]:
        n=project_growth_nutrition(text,_a(response=['감정'],scores={'감정':score},rn=rn))
        assert n.response=={'감정':1.0}
