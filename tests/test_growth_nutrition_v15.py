from bookeater.game.nutrition import project_growth_nutrition


def _a(*, response=(), world=(), scores=None, rn=.84, wn=.84):
    return {'response': list(response), 'world': list(world), 'scores': scores or {}, 'null': {'response': rn, 'world': wn}}


def test_library_series_lookup_is_pure_bookkeeping():
    n = project_growth_nutrition(
        '시리즈 순서를 헷갈려 도서관 검색에서 권수를 확인했다.',
        _a(response=['탐구'], scores={'탐구': .90}, rn=.84),
    )
    assert n.is_empty


def test_game_character_job_name_does_not_create_dark_modifier():
    n = project_growth_nutrition(
        '“감시자”는 게임 캐릭터 직업 이름이고 설명은 점수 계산 방식에 관한 것이었다.',
        _a(response=['탐구'], world=['어둠'], scores={'탐구': .84, '어둠': .85}, rn=.82, wn=.826),
    )
    assert n.world == {}


def test_time_loop_phrase_can_create_imagination_modifier():
    n = project_growth_nutrition(
        '도시 전체가 매주 월요일 아침으로 되돌아간다는 규칙이 기묘했다.',
        _a(world=['사회'], scores={'상상': .844, '사회': .855}, wn=.823),
    )
    assert '상상' in n.world


def test_virtual_country_can_keep_imagination_with_social_structure():
    n = project_growth_nutrition(
        '가상 국가에서 시민 등급에 따라 투표 자격이 정해지는 제도가 무서웠다.',
        _a(world=['사회', '어둠'], scores={'상상': .844, '사회': .884, '어둠': .878}, wn=.824),
    )
    assert set(n.world) == {'상상', '사회'}


def test_explicit_science_nature_anchor_can_survive_tiny_positive_margin():
    n = project_growth_nutrition(
        '산호가 수온 변화에 스트레스를 받는 과정을 다른 자료에서도 확인해 보고 싶다.',
        _a(response=['탐구'], scores={'탐구': .893, '자연': .843}, rn=.812, wn=.837),
    )
    assert n.response == {'탐구': 1.0}
    assert n.world == {'자연': 1.0}


def test_emotion_inflection_jjanhatda_is_not_missed():
    n = project_growth_nutrition(
        '아버지가 빈 의자만 바라보는 장면이 이상하게 짠했다.',
        _a(response=['감정'], scores={'감정': .867}, rn=.834),
    )
    assert n.response == {'감정': 1.0}


def test_pronunciation_language_can_feed_sensory_body_without_world_modifier():
    n = project_growth_nutrition(
        '자연 발음이라는 수업 용어를 따라 읽으며 입 모양을 연습했다.',
        _a(response=['감각'], scores={'감각': .861}, rn=.841),
    )
    assert n.response == {'감각': 1.0}
    assert n.world == {}
