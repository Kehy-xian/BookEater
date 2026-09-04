from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bookeater.pet_art import GEULSSIAL_ANIMATIONS, frame_filename
from bookeater.pet_sprite import (
    TkSpriteCache,
    _binary_alpha,
    asset_slug_for_form,
    default_override_root,
    production_animation_available,
    production_frame_paths,
    resolved_frame_paths,
    sprite_source_form,
    visual_asset_slug_for_form,
)


def test_binary_alpha_removes_color_key_fringe():
    from PIL import Image

    image = Image.new('RGBA', (3, 1))
    image.putdata(((80, 70, 60, 0), (80, 70, 60, 95), (80, 70, 60, 96)))
    result = _binary_alpha(image)
    assert [result.getpixel((x, 0))[3] for x in range(3)] == [0, 0, 255]


def _write_complete(root: Path, slug: str, state: str, payload: bytes = b'placeholder') -> tuple[Path, ...]:
    root.mkdir(parents=True, exist_ok=True)
    spec = GEULSSIAL_ANIMATIONS[state]
    paths = tuple(root / frame_filename(slug, state, i) for i in range(spec.frame_count))
    for path in paths:
        path.write_bytes(payload)
    return paths


def test_approved_forms_have_stable_asset_slugs():
    assert asset_slug_for_form('starter') == 'paperling'
    assert asset_slug_for_form('route_a') == 'pagedge'
    assert asset_slug_for_form('route_b') == 'inknest'
    assert asset_slug_for_form('route_c') == 'lantern'


def test_placeholder_final_has_no_own_slug_but_inherits_nearest_approved_visual():
    assert asset_slug_for_form('route_a1_alpha') is None
    assert sprite_source_form('route_a1_alpha') == 'route_a1'
    assert visual_asset_slug_for_form('route_a1_alpha') == 'route_a1'
    assert sprite_source_form('route_c2_beta') == 'route_c2'
    assert visual_asset_slug_for_form('route_c2_beta') == 'route_c2'


def test_inherited_final_uses_parent_production_paths(tmp_path):
    resource_root = tmp_path
    sprites = resource_root / 'resources' / 'sprites'
    expected = _write_complete(sprites, 'route_a1', 'idle')
    assert production_frame_paths(resource_root, 'route_a1_alpha', 'idle') == expected
    assert production_animation_available(resource_root, 'route_a1_alpha', 'idle')


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


def test_complete_override_wins_over_packaged_animation(tmp_path):
    resource_root = tmp_path / 'bundle'
    packaged = resource_root / 'resources' / 'sprites'
    override = tmp_path / 'user-art'
    packaged_paths = _write_complete(packaged, 'paperling', 'idle', b'packaged')
    override_paths = _write_complete(override, 'paperling', 'idle', b'override')

    resolved = resolved_frame_paths(
        resource_root,
        'starter',
        'idle',
        override_root=override,
    )
    assert resolved == override_paths
    assert resolved != packaged_paths


def test_partial_override_is_atomic_and_never_mixes_with_packaged_frames(tmp_path):
    resource_root = tmp_path / 'bundle'
    packaged = resource_root / 'resources' / 'sprites'
    override = tmp_path / 'user-art'
    packaged_paths = _write_complete(packaged, 'paperling', 'walk', b'packaged')
    override.mkdir(parents=True)
    # Copy only one override frame; the entire override state must be ignored.
    (override / frame_filename('paperling', 'walk', 0)).write_bytes(b'override')

    resolved = resolved_frame_paths(
        resource_root,
        'starter',
        'walk',
        override_root=override,
    )
    assert resolved == packaged_paths
    assert all(path.parent == packaged for path in resolved)


def test_corrupt_complete_override_falls_back_to_healthy_packaged_animation(tmp_path):
    resource_root = tmp_path / 'bundle'
    packaged = resource_root / 'resources' / 'sprites'
    override = tmp_path / 'user-art'
    packaged_paths = _write_complete(packaged, 'paperling', 'idle', b'good')
    override_paths = _write_complete(override, 'paperling', 'idle', b'bad')

    class FakeTk:
        @staticmethod
        def PhotoImage(*, file):
            path = Path(file)
            if path.parent == override:
                raise ValueError('corrupt override PNG')
            return path

    cache = TkSpriteCache(FakeTk, resource_root, override_root=override)
    frames = cache.frames('starter', 'idle')
    assert frames == packaged_paths
    assert all(path not in override_paths for path in frames)


def test_default_override_root_is_inside_user_data_not_packaged_resources(tmp_path):
    data = tmp_path / 'data'
    resource = tmp_path / 'bundle'
    override = default_override_root(data)
    assert override == data / 'art_overrides'
    assert resource not in override.parents


def test_tk_cache_auto_discovers_bookeater_data_dir_override(tmp_path, monkeypatch):
    data = tmp_path / 'user-data'
    resource_root = tmp_path / 'bundle'
    override = default_override_root(data)
    expected = _write_complete(override, 'paperling', 'idle', b'fake-png')
    monkeypatch.setenv('BOOKEATER_DATA_DIR', str(data))

    class FakeTk:
        @staticmethod
        def PhotoImage(*, file):
            return Path(file)

    cache = TkSpriteCache(FakeTk, resource_root)
    frames = cache.frames('starter', 'idle')
    assert frames == expected
    assert cache.override_root == override
