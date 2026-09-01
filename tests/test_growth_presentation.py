from bookeater.game.evolution import EvolutionDecision
from bookeater.game.presentation import public_growth_view, generic_feed_line

INTERNAL_KEYS={'base_trait','modifier_traits','reason','changed_base'}
INTERNAL_LABELS={'사유','탐구','감정','감각','상상','모험','자연','사회','어둠'}


def test_public_view_hides_internal_classifier_state():
    decision=EvolutionDecision(
        stage=3,
        base_trait='사유',
        modifier_traits=('사회','어둠'),
        species='천개의눈 서고지기',
        visual_modifiers=('도시눈','먹구름'),
        changed_base=True,
        reason='challenger clearly surpassed current base',
    )
    public=public_growth_view(decision,previous_stage=2).to_dict()
    assert INTERNAL_KEYS.isdisjoint(public.keys())
    assert not any(v in INTERNAL_LABELS for v in public.values() if isinstance(v,str))
    assert '키워드' not in str(public)
    assert 'confidence' not in str(public).lower()
    assert decision.reason not in str(public)


def test_stage_one_hint_stays_vague():
    decision=EvolutionDecision(1,'탐구',(), '돋보기콩',(),True,'first stable reaction base')
    hint=public_growth_view(decision).tendency_hint
    assert '탐구' not in hint
    assert '점수' not in hint
    assert '%' not in hint


def test_final_hint_can_reveal_broad_tendency_without_labels():
    decision=EvolutionDecision(3,'감정',('자연',),'이야기를품은달짐승',('이끼뿔',),False,'current base remains strongest')
    view=public_growth_view(decision)
    assert '마음' in view.tendency_hint
    assert '생명' in view.tendency_hint or '환경' in view.tendency_hint
    assert '감정' not in view.tendency_hint
    assert '자연' not in view.tendency_hint


def test_feed_line_never_explains_classification():
    line=generic_feed_line(7)
    assert all(label not in line for label in INTERNAL_LABELS)
    assert '분류' not in line and '점수' not in line and '%' not in line
