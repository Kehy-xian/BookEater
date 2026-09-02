from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.pet_fallback_forms import approved_visual_form, fallback_family, fallback_variant


def test_approved_forms_keep_their_own_fallback_identity():
    assert approved_visual_form('starter') == 'starter'
    assert approved_visual_form('route_a') == 'route_a'
    assert approved_visual_form('route_b1') == 'route_b1'
    assert approved_visual_form('route_c2') == 'route_c2'


def test_unapproved_final_forms_do_not_invent_new_visuals():
    assert approved_visual_form('route_a1_alpha') == 'route_a1'
    assert approved_visual_form('route_a2_beta') == 'route_a2'
    assert approved_visual_form('route_b2_alpha') == 'route_b2'
    assert approved_visual_form('route_c1_beta') == 'route_c1'


def test_family_and_variant_are_stable():
    assert (fallback_family('route_a2'), fallback_variant('route_a2')) == ('a', '2')
    assert (fallback_family('route_b1_beta'), fallback_variant('route_b1_beta')) == ('b', '1')
    assert (fallback_family('route_c2_alpha'), fallback_variant('route_c2_alpha')) == ('c', '2')


def test_unknown_form_falls_back_to_starter():
    assert approved_visual_form('not-a-form') == 'starter'
    assert fallback_family('not-a-form') == 'starter'
