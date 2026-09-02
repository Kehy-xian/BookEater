from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.game.form_catalog import approved_concept_ids, catalog_entry, placeholder_ids
from bookeater.game.growth_routes import ALL_GROWTH_FORMS


def test_approved_concepts_stop_after_two_types_per_route():
    approved = set(approved_concept_ids())
    assert approved == {
        'starter',
        'route_a', 'route_b', 'route_c',
        'route_a1', 'route_a2',
        'route_b1', 'route_b2',
        'route_c1', 'route_c2',
    }


def test_all_final_forms_are_reserved_placeholders():
    placeholders = set(placeholder_ids())
    assert len(ALL_GROWTH_FORMS) == 22
    assert len(placeholders) == 12
    assert all(form_id.endswith(('_alpha', '_beta')) for form_id in placeholders)
    for form_id in placeholders:
        entry = catalog_entry(form_id)
        assert entry.public_name == '???'
        assert entry.asset_slug is None
        assert not entry.concept_approved


def test_concept_approval_does_not_pretend_sprite_frames_exist():
    for form_id in approved_concept_ids():
        entry = catalog_entry(form_id)
        assert entry.asset_slug
        assert not entry.sprite_ready
