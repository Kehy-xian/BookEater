from pathlib import Path

import pytest

from bookeater.pet_art import (
    GEULSSIAL_ANIMATIONS,
    PetPalette,
    complete_animation_available,
    expected_frame_paths,
    frame_filename,
)


def test_working_palette_is_stable():
    palette = PetPalette()
    assert palette.paper == '#F4EDDA'
    assert palette.ink == '#25211E'
    assert palette.bookmark == '#B95F55'


def test_geulssial_first_milestone_has_idle_and_eat():
    assert GEULSSIAL_ANIMATIONS['idle'].frame_count == 4
    assert GEULSSIAL_ANIMATIONS['eat'].frame_count == 6
    assert GEULSSIAL_ANIMATIONS['eat'].loop is False


def test_asset_filenames_are_predictable():
    assert frame_filename('geulssial', 'idle', 0) == 'geulssial_idle_00.png'
    assert frame_filename('geulssial', 'eat', 5) == 'geulssial_eat_05.png'
    with pytest.raises(ValueError):
        frame_filename('글씨알', 'idle', 0)


def test_incomplete_animation_must_fall_back_atomically(tmp_path: Path):
    paths = expected_frame_paths(tmp_path, 'geulssial', 'idle')
    assert len(paths) == 4
    for path in paths[:-1]:
        path.write_bytes(b'placeholder')
    assert complete_animation_available(tmp_path, 'geulssial', 'idle') is False
    paths[-1].write_bytes(b'placeholder')
    assert complete_animation_available(tmp_path, 'geulssial', 'idle') is True
