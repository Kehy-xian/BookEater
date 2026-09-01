from __future__ import annotations

import json
import sys

from bookeater.desktop import run_desktop
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
        'species': view.species,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if all((payload['db_ok'], payload['model_loaded'], payload['analysis_is_mapping'])) else 3


if __name__ == '__main__':
    raise SystemExit(_smoke() if '--smoke' in sys.argv else run_desktop())
