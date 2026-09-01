from bookeater.game.evolution import resolve_evolution


def test_one_noisy_response_does_not_flip_established_body():
    # An established reflective body should not flip because one record is classified differently.
    before={'사유':30,'탐구':24,'감정':6,'감각':5}
    after={**before,'탐구':26}
    d1=resolve_evolution(before,35,current_base='사유')
    d2=resolve_evolution(after,36,current_base=d1.base_trait)
    assert d1.base_trait=='사유'
    assert d2.base_trait=='사유'
    assert d2.changed_base is False


def test_sustained_shift_can_eventually_change_body():
    # Opacity must not make the creature permanently insensitive to a real long-term change.
    stats={'사유':30,'탐구':38,'감정':6,'감각':5}
    d=resolve_evolution(stats,50,current_base='사유')
    assert d.base_trait=='탐구'
    assert d.changed_base is True


def test_one_noisy_world_hit_does_not_create_second_modifier():
    before={'사회':10,'어둠':2,'상상':1,'모험':0,'자연':1}
    after={**before,'어둠':3}
    d1=resolve_evolution(before,30,current_base='사유')
    d2=resolve_evolution(after,31,current_base='사유')
    assert d1.modifier_traits==('사회',)
    assert d2.modifier_traits==('사회',)


def test_coherent_mixed_world_history_can_show_two_modifiers():
    stats={'사회':10,'어둠':8,'상상':1,'모험':0,'자연':1}
    d=resolve_evolution(stats,31,current_base='사유')
    assert set(d.modifier_traits)=={'사회','어둠'}


def test_stage_threshold_does_not_force_internal_explanation_into_species():
    stats={'사유':20,'탐구':5,'감정':4,'감각':3,'사회':7}
    d=resolve_evolution(stats,40,current_base='사유')
    # Species itself is a phenotype name, not an encoded score/recipe.
    assert d.species=='천개의눈 서고지기'
    assert '%' not in d.species and '사유' not in d.species and '사회' not in d.species
