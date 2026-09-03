from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.pet_art import GEULSSIAL_ANIMATIONS, PetPalette
from bookeater.pet_window_v8 import DesktopPetWindowV8


class FakeCanvas:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        if name.startswith('create_') or name == 'delete':
            def call(*args, **kwargs):
                self.calls.append((name, args, kwargs))
                return len(self.calls)
            return call
        raise AttributeError(name)


class FakeSpriteCache:
    def __init__(self, states):
        self.states = set(states)

    def frames(self, _form_id, state, *, scale=1.0):
        del scale
        return (object(), object()) if state in self.states else None


def make_pet(form_id: str, state: str):
    pet = object.__new__(DesktopPetWindowV8)
    pet.canvas = FakeCanvas()
    pet.palette = PetPalette()
    pet._frame = 7
    pet._pet_state = state
    pet._visual_form_id = form_id
    # Dialogue choice needs runtime; renderer smoke only verifies body drawing here.
    pet._draw_dialogue_overlay = lambda: None
    return pet


def test_each_approved_route_family_draws_all_animation_states_without_tk():
    forms = ('route_a', 'route_a1', 'route_a2', 'route_b', 'route_b1', 'route_b2', 'route_c', 'route_c1', 'route_c2')
    for form_id in forms:
        for state in GEULSSIAL_ANIMATIONS:
            pet = make_pet(form_id, state)
            pet._draw_route_fallback(state)
            assert pet.canvas.calls, (form_id, state)
            assert any(name.startswith('create_') for name, _args, _kwargs in pet.canvas.calls)


def test_unapproved_final_form_draws_approved_parent_shape_without_error():
    for form_id in ('route_a1_alpha', 'route_b2_beta', 'route_c1_alpha'):
        pet = make_pet(form_id, 'idle')
        pet._draw_route_fallback('idle')
        assert pet.canvas.calls


def test_complete_custom_action_frames_replace_procedural_action_overlay():
    pet = make_pet('starter', 'wash')
    pet._sprite_cache = FakeSpriteCache({'wash', 'idle'})
    pet._pet_scale = 1.0
    pet._refresh_visual_identity = lambda: None
    pet._scale_canvas_items = lambda: None
    overlays = []
    pet._draw_care_overlay = overlays.append
    pet._draw()
    assert any(name == 'create_image' for name, _args, _kwargs in pet.canvas.calls)
    assert overlays == []


def test_missing_custom_action_frames_keep_safe_idle_and_overlay_fallback():
    pet = make_pet('starter', 'wash')
    pet._sprite_cache = FakeSpriteCache({'idle'})
    pet._pet_scale = 1.0
    pet._refresh_visual_identity = lambda: None
    pet._scale_canvas_items = lambda: None
    overlays = []
    pet._draw_care_overlay = overlays.append
    pet._draw()
    assert any(name == 'create_image' for name, _args, _kwargs in pet.canvas.calls)
    assert overlays == ['wash']
