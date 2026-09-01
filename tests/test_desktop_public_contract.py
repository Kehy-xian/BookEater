from bookeater.desktop import CreatureCard, creature_card
from bookeater.game.presentation import PublicGrowthView


def test_creature_card_contains_only_public_fields():
    view = PublicGrowthView(
        stage=2,
        species='질문짐승',
        visual_modifiers=('leaf_tail',),
        tendency_hint='질문을 오래 붙잡고 생각의 결을 따라가는 흔적이 보인다.',
        change_message='조금씩 자라고 있다.',
    )
    card = creature_card(view)
    assert isinstance(card, CreatureCard)
    assert set(card.__dict__) == {'species', 'stage_text', 'hint'}
    assert card.species == '질문짐승'
    assert card.stage_text == '성장 2단계'
    assert '질문을 오래' in card.hint
    # Visual implementation identifiers are consumed later by sprite code, never printed here.
    assert 'leaf_tail' not in repr(card)


def test_stage_zero_is_diegetic_not_numeric_debug_output():
    view = PublicGrowthView(
        stage=0,
        species='글씨알',
        visual_modifiers=(),
        tendency_hint='',
        change_message='',
    )
    card = creature_card(view)
    assert card.stage_text == '아직 알 속에서 자라는 중'
    assert card.hint == '아직 어떤 모습으로 자랄지 알 수 없다.'
