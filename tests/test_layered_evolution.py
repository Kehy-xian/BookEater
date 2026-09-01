from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bookeater.game import resolve_evolution


def test_world_only_never_becomes_body_type():
    d=resolve_evolution({'상상':20,'사회':10},20)
    assert d.base_trait is None
    assert d.modifier_traits[0]=='상상'
    assert d.species=='기억몽'


def test_reaction_only_has_no_fake_world_modifier():
    d=resolve_evolution({'사유':12,'감정':4},20)
    assert d.base_trait=='사유'
    assert d.modifier_traits==()


def test_world_trait_cannot_be_selected_as_base():
    d=resolve_evolution({'사회':100,'사유':8},50)
    assert d.base_trait=='사유'
    assert d.modifier_traits[0]=='사회'


def test_reaction_trait_cannot_be_modifier():
    d=resolve_evolution({'감정':100,'자연':9},50)
    assert d.base_trait=='감정'
    assert d.modifier_traits==('자연',)


def test_near_tie_does_not_flip_existing_body():
    d=resolve_evolution({'사유':20,'감정':22},30,current_base='사유')
    assert d.base_trait=='사유'
    assert not d.changed_base


def test_clear_challenger_can_change_body():
    d=resolve_evolution({'사유':20,'감정':29},30,current_base='사유')
    assert d.base_trait=='감정'
    assert d.changed_base


def test_multilabel_world_can_have_two_modifiers_but_not_forced():
    d=resolve_evolution({'사유':20,'사회':10,'어둠':8,'자연':2},45)
    assert d.modifier_traits==('사회','어둠')
    d2=resolve_evolution({'사유':20,'사회':10,'어둠':5},45)
    assert d2.modifier_traits==('사회',)
