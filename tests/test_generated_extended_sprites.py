from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))

from bookeater.pet_art import GEULSSIAL_ANIMATIONS
from bookeater.sprite_validation import validate_sprite_pack
from generate_extended_sprites import APPROVED_SLUGS, DERIVED_STATES, ensure_all_derived_states, ensure_derived_state
from generate_paperling_sprites import generate_paperling_core_frames
from generate_route_sprites import generate_all_route_core_frames
from generate_subroute_sprites import generate_all_subroute_core_frames


def _generate_all_core(root: Path) -> None:
    generate_paperling_core_frames(root)
    generate_all_route_core_frames(root)
    generate_all_subroute_core_frames(root)


def test_all_approved_forms_get_complete_derived_states(tmp_path):
    _generate_all_core(tmp_path)
    result = ensure_all_derived_states(tmp_path)
    assert len(result) == len(APPROVED_SLUGS) * len(DERIVED_STATES)
    assert all(value == 'derived' for value in result.values())

    all_states = ('idle', 'eat', 'walk') + DERIVED_STATES
    for slug in APPROVED_SLUGS:
        assert not validate_sprite_pack(tmp_path, slug, required_states=all_states), slug


def test_derived_state_frame_counts_follow_runtime_contract(tmp_path):
    _generate_all_core(tmp_path)
    ensure_all_derived_states(tmp_path)
    for slug in APPROVED_SLUGS:
        for state in DERIVED_STATES:
            expected = GEULSSIAL_ANIMATIONS[state].frame_count
            actual = len(tuple(tmp_path.glob(f'{slug}_{state}_*.png')))
            assert actual == expected, f'{slug}/{state}: {actual} != {expected}'


def test_derived_states_are_not_static_copies(tmp_path):
    _generate_all_core(tmp_path)
    ensure_all_derived_states(tmp_path)
    for slug in APPROVED_SLUGS:
        read = [(tmp_path / f'{slug}_read_{i:02d}.png').read_bytes() for i in range(3)]
        sleep = [(tmp_path / f'{slug}_sleep_{i:02d}.png').read_bytes() for i in range(3)]
        talk = [(tmp_path / f'{slug}_talk_{i:02d}.png').read_bytes() for i in range(2)]
        memory = [(tmp_path / f'{slug}_spit_memory_{i:02d}.png').read_bytes() for i in range(4)]
        assert len(set(read)) >= 2, slug
        assert len(set(sleep)) >= 2, slug
        assert len(set(talk)) == 2, slug
        assert len(set(memory)) == 4, slug


def test_partial_hand_authored_derived_state_is_rejected_not_mixed(tmp_path):
    generate_paperling_core_frames(tmp_path)
    partial = tmp_path / 'paperling_read_00.png'
    partial.write_bytes((tmp_path / 'paperling_idle_00.png').read_bytes())
    try:
        ensure_derived_state(tmp_path, 'paperling', 'read')
    except RuntimeError as exc:
        assert 'partial paperling/read' in str(exc)
    else:
        raise AssertionError('partial hand-authored state must not be silently mixed')
