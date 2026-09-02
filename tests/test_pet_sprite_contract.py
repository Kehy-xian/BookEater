from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.pet_art import GEULSSIAL_ANIMATIONS, frame_filename
from bookeater.pet_sprite import (
    asset_slug_for_form,
    production_animation_available,
    production_frame_paths,
)


def test_approved_forms_have_stable_asset_slugs():
    assert asset_slug_for_form('starter') == 'paperling'
    assert asset_slug_for_form('route_a') == 'pagedge'
    assert asset_slug_for_form('route_b') == 'inknest'
    assert asset_slug_for_form('route_c') == 'lantern'


def test_placeholder_final_has_no_production_slug():
    assert asset_slug_for_form('route_a1_alpha') is None


def test_partial_animation_never_counts_as_ready(tmp_path):
    root = tmp_path
    sprites = root / 'resources' / 'sprites'
    sprites.mkdir(parents=True)
    spec = GEULSSIAL_ANIMATIONS['idle']
    for i in range(spec.frame_count - 1):
        (sprites / frame_filename('paperling', 'idle', i)).write_bytes(b'not-a-real-png')
    assert not production_animation_available(root, 'starter', 'idle')


def test_complete_filename_set_is_discovered(tmp_path):
    root = tmp_path
    sprites = root / 'resources' / 'sprites'
    sprites.mkdir(parents=True)
    paths = production_frame_paths(root, 'route_c', 'walk')
    assert len(paths) == GEULSSIAL_ANIMATIONS['walk'].frame_count
    for path in paths:
        path.write_bytes(b'placeholder')
    # Availability checks completeness only; TkSpriteCache separately rejects corrupt PNG bytes.
    assert production_animation_available(root, 'route_c', 'walk')
