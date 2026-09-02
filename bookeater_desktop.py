from __future__ import annotations

import json
import sys

from bookeater.desktop import run_desktop
from bookeater.pet_window_v4 import run_pet_v4
from bookeater.runtime import bootstrap_runtime


def _smoke() -> int:
    """Headless packaged-runtime check used by Windows CI.

    It opens only a temporary/local DB chosen by the workflow, verifies bundled model resources can
    really initialize, and exercises one semantic analysis. It does not create a desktop window.
    """
    runtime = bootstrap_runtime()
    analysis = runtime.analyzer.analyze('주인공의 선택이 옳았는지 오래 생각했다.')
    view = runtime.feed_service.current_view()
    state = runtime.store.load_state()
    payload = {
        'db_ok': runtime.database_path.exists(),
        'model_loaded': runtime.analyzer.loaded,
        'analysis_is_mapping': isinstance(analysis, dict),
        'journal_ready': runtime.journal is not None,
        'encyclopedia_ready': runtime.encyclopedia is not None,
        'form_id': state.form_id,
        'species': view.species,
    }
    print(json.dumps(payload, ensure_ascii=True))
    return 0 if all((
        payload['db_ok'], payload['model_loaded'], payload['analysis_is_mapping'],
        payload['journal_ready'], payload['encyclopedia_ready'],
    )) else 3


if __name__ == '__main__':
    if '--smoke' in sys.argv:
        raise SystemExit(_smoke())
    if '--full-window' in sys.argv:
        raise SystemExit(run_desktop())
    raise SystemExit(run_pet_v4())
