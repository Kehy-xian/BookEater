from bookeater.game.nutrition import project_growth_nutrition


def _a(*, response=(), world=(), scores=None, rn=.84, wn=.84):
    return {'response':list(response),'world':list(world),'scores':scores or {},'null':{'response':rn,'world':wn}}


def test_reservation_admin_note_cannot_feed_body_even_if_classifier_is_confident():
    n=project_growth_nutrition(
        '예약한 책이 도착했다는 알림이 와서 수령 가능 날짜를 확인했다.',
        _a(response=['탐구'],scores={'탐구':.91},rn=.84),
    )
    assert n.is_empty


def test_sync_admin_note_cannot_feed_emotion():
    n=project_growth_nutrition(
        '전자책 동기화가 안 돼 마지막 읽은 위치를 직접 맞췄다.',
        _a(response=['감정'],scores={'감정':.91},rn=.84),
    )
    assert n.is_empty


def test_unanchored_body_guess_needs_clear_margin():
    n=project_growth_nutrition(
        '설명이 조금 복잡해서 예시를 다시 읽었다.',
        _a(response=['사유'],scores={'사유':.87},rn=.84),
    )
    assert n.response=={}


def test_real_emotion_anchor_can_still_pass_small_margin():
    n=project_growth_nutrition(
        '아이가 혼자 식탁을 치우는 장면이 짠하고 마음에 남았다.',
        _a(response=['감정'],scores={'감정':.852},rn=.84),
    )
    assert n.response=={'감정':1.0}


def test_low_margin_direct_nature_topic_can_pass_world_guard():
    n=project_growth_nutrition(
        '해수 온도가 오르면 산호가 하얗게 변하는 원리가 궁금했다.',
        _a(response=['탐구'],world=[],scores={'탐구':.90,'자연':.852},rn=.84,wn=.84),
    )
    assert n.world=={'자연':1.0}


def test_two_structural_modifiers_take_priority_over_tonal_darkness():
    n=project_growth_nutrition(
        '가상 도시에서 시민 점수에 따라 투표 제도가 달라진다는 설정이 섬뜩했다.',
        _a(world=['어둠','사회'],scores={'상상':.855,'사회':.89,'어둠':.90},wn=.84),
    )
    assert set(n.world)=={'상상','사회'}


def test_visual_surface_with_real_social_content_is_not_overblocked():
    n=project_growth_nutrition(
        '차가운 색의 그림도 인상적이었지만 감시 제도 때문에 사람들이 서로 피하는 내용이 더 남았다.',
        _a(response=['감각'],world=['어둠'],scores={'감각':.91,'사회':.858,'어둠':.87},rn=.84,wn=.84),
    )
    assert '사회' in n.world
