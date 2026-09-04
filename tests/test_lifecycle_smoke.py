from __future__ import annotations

from pathlib import Path

from bookeater.services.lifecycle_smoke import lifecycle_smoke


def test_lifecycle_smoke_isolated_cycle_passes(tmp_path):
    report = lifecycle_smoke(resources=tmp_path)

    assert report['ok'] is True
    assert report == {
        'isolated_profile': True,
        'route_complete': True,
        'final_growth_frozen': True,
        'memoir_created': True,
        'reading_archive_preserved': True,
        'memoir_preserved': True,
        'new_cycle_started': True,
        'ok': True,
    }


def test_windows_entrypoint_uses_latest_pet_window():
    source = (Path(__file__).resolve().parents[1] / 'bookeater_desktop.py').read_text(encoding='utf-8')
    assert 'from bookeater.pet_window_v12 import run_pet_v12' in source
    assert 'run_guarded(run_pet_v12)' in source
