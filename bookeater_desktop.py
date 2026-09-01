from __future__ import annotations

import json
import sys

from bookeater.desktop import run_desktop
from bookeater.pet_window import run_pet
from bookeater.runtime import bootstrap_runtime


def _smoke() -> int:
    """Headless packaged-runtime check used by Windows CI.

    It opens only a temporary/local DB chosen by the workflow, verifies bundled model resources can
    really initialize, and exercises one semantic analysis. It does not create a desktop window.
    """
    runtime = bootstrap_runtime()
    analysis = runtime.analyzer.analyze('주인공의 선택이 옳았는지 오래 생각했다.')
    view = runtime.feed_service.current_view()
    payload = {
        'db_ok': runtime.database_path.exists(),
        'model_loaded': runtime.analyzer.loaded,
        'analysis_is_mapping': isinstance(analysis, dict),
        'journal_ready': runtime.journal is not None,
        'species': view.species,
    }
    # PyInstaller uses the windowed bootloader for the real desktop app. On a Windows CI runner,
    # inherited stdout can therefore fall back to a legacy code page. Keep the smoke payload ASCII
    # so Korean species names cannot turn an otherwise healthy packaged runtime into a false failure.
    print(json.dumps(payload, ensure_ascii=True))
    return 0 if all((
        payload['db_ok'], payload['model_loaded'], payload['analysis_is_mapping'], payload['journal_ready']
    )) else 3


if __name__ == '__main__':
    if '--smoke' in sys.argv:
        raise SystemExit(_smoke())
    if '--full-window' in sys.argv:
        raise SystemExit(run_desktop())
    raise SystemExit(run_pet())
