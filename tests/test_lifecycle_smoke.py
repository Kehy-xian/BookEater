from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import bookeater_desktop
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
    assert 'from bookeater.pet_window_v12 import DesktopPetWindowV12, run_pet_v12' in source
    assert 'run_guarded(run_pet_v12)' in source
    assert "if '--lifecycle-preview' in sys.argv:" in source


def test_lifecycle_preview_constructs_latest_window_in_disposable_profile(monkeypatch):
    calls = []

    class Journal:
        def add_book(self, *args, **kwargs):
            calls.append(('book', args, kwargs))

    runtime = SimpleNamespace(journal=Journal())
    monkeypatch.setattr(bookeater_desktop, 'bootstrap_runtime', lambda **kwargs: runtime)

    class PreviewWindow:
        def __init__(self, passed_runtime, *, lifecycle_preview=False):
            calls.append(('window', passed_runtime, lifecycle_preview))

        def run(self):
            calls.append(('run',))

    monkeypatch.setattr(bookeater_desktop, 'DesktopPetWindowV12', PreviewWindow)

    assert bookeater_desktop._lifecycle_preview() == 0
    assert calls[0][0] == 'book'
    assert calls[1] == ('window', runtime, True)
    assert calls[2] == ('run',)
